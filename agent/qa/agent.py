"""Bounded QA tool loop: one part per verbatim, validation before the join."""

import json
import logging
import time

from agent.llm.client import LLMError
from agent.qa import actions
from agent.qa.composer import Composer
from agent.qa.renderer import RowRenderer
from agent.qa.state import AgentState
from agent.qa.types import AgentResult
from agent.qa.validator import AnswerValidator

log = logging.getLogger("agent.qa")


class ResponseAgent:
    def __init__(self, client, registry, prompt_builder, schema, max_steps: int = 6,
                 deadline_s: float = 20.0, max_step_tokens: int = 300,
                 validator=None, composer=None):
        self.client = client
        self.registry = registry
        self.prompt_builder = prompt_builder
        self.schema = schema
        self.max_steps = max(1, max_steps)
        self.deadline_s = deadline_s
        self.max_step_tokens = max_step_tokens
        self.validator = validator or AnswerValidator(schema)
        self.composer = composer or Composer(RowRenderer(schema), schema)

    def _signature(self, call):
        arguments = dict(call.arguments or {})
        query = arguments.get("query")
        if call.name == "run_sparql" and isinstance(query, str):
            arguments["query"] = " ".join(query.split())
        return call.name, json.dumps(arguments, sort_keys=True, ensure_ascii=False)

    def _append_call(self, messages, call, content):
        messages.append({"role": "assistant", "content": None, "tool_calls": [{
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
        }]})
        messages.append({"role": "tool", "tool_call_id": call.id, "content": content})

    def _result(self, parts, state, trace) -> AgentResult:
        text = " ".join(part.text for part in parts)
        evidence = tuple(row_id for part in parts for row_id in part.evidence_row_ids)
        if trace is not None:
            trace.add("evidence", list(evidence))
            for part in parts:
                trace.add("response_part", {"index": part.verbatim_index, "kind": part.kind,
                                            "chars": len(part.text),
                                            "evidence": list(part.evidence_row_ids),
                                            "safety_types": list(part.addressed_safety_types)})
            trace.add("response", {"parts": len(parts), "text": text})
        return AgentResult(tuple(parts), text, evidence)

    def respond(self, verdict, decision, trace=None) -> AgentResult:
        state = AgentState(verdict, decision)
        messages = self.prompt_builder.build(decision, verdict)
        tools = actions.available_tools(decision)
        deadline = time.monotonic() + self.deadline_s

        for step in range(self.max_steps):
            if time.monotonic() > deadline:
                return self._fallback(state, "deadline", trace)
            state.step_count += 1
            final_step = step == self.max_steps - 1
            tool_choice = "auto"
            if final_step and decision.tools_enabled:
                tool_choice = {"type": "function", "function": {"name": "submit_response"}}
            try:
                response = self.client.chat(messages=messages, tools=tools, tool_choice=tool_choice,
                                            max_tokens=self.max_step_tokens, temperature=0.0)
            except LLMError as exc:
                state.errors.append(str(exc))
                return self._fallback(state, "model error", trace)

            if trace is not None:
                trace.add("llm_step", {
                    "step": step + 1,
                    "content": response.content,
                    "reasoning": response.reasoning,
                    "finish_reason": response.finish_reason,
                    "usage": response.usage,
                    "tool_calls": [{"name": call.name, "arguments": call.arguments}
                                   for call in response.tool_calls],
                })
            if not response.tool_calls:
                messages.append({"role": "assistant", "content": response.content or ""})
                messages.append({"role": "user", "content": "You must call submit_response to finish."})
                continue

            call = response.tool_calls[0]
            if call.name == "submit_response":
                validation = self.validator.validate(call.arguments, state)
                if validation.ok:
                    return self._result(validation.parts, state, trace)
                state.errors.append(validation.error)
                if trace is not None:
                    trace.add("repair", validation.error)
                self._append_call(messages, call, f"Invalid response: {validation.error}")
                continue

            if not decision.tools_enabled or self.registry is None or call.name not in self.registry.names():
                error = f"tool is not available: {call.name}"
                state.errors.append(error)
                if trace is not None:
                    trace.add("repair", error)
                self._append_call(messages, call, error)
                continue

            signature = self._signature(call)
            if signature in state.tool_signatures:
                error = ("This tool call was already executed. Use the observation already "
                         "returned and call submit_response.")
                state.errors.append(error)
                if trace is not None:
                    trace.add("repair", error)
                self._append_call(messages, call, error)
                continue
            state.tool_signatures.add(signature)
            if trace is not None:
                trace.add("agent_step", {"tool": call.name, "arguments": call.arguments})
            executed = self.registry.execute(call.name, call.arguments)
            state.observations.append(executed)
            if trace is not None:
                if call.name == "run_sparql":
                    trace.add("sparql", call.arguments.get("query", ""))
                trace.add("tool_result", {"tool": call.name,
                                          "arguments": call.arguments,
                                          "row_count": len(executed.observation.rows),
                                          "row_ids": list(executed.observation.row_ids),
                                          "rows": list(executed.observation.rows),
                                          "truncated": executed.observation.truncated,
                                          "error": executed.observation.error})
            self._append_call(messages, call, executed.observation.as_json())

        return self._fallback(state, "step budget", trace)

    def _fallback(self, state, reason, trace=None) -> AgentResult:
        log.warning("QA fallback: %s", reason)
        result = self.composer.compose(state.decision, state, reason)
        if trace is not None:
            trace.add("fallback", reason)
            trace.add("response", {"parts": len(result.parts), "text": result.text})
        return result
