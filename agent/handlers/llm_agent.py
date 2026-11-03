"""LLM mode: guard gate, QA response agent, and session seam."""

import logging

from agent.core import append_turn
from agent.guard.session import visible_user_text
from agent.observability import emit

log = logging.getLogger("agent.llm_agent")


class LLMAgentHandler:
    name = "llm"

    def __init__(self, gate, qa_agent, schema, show_labels: bool = False):
        self.gate = gate
        self.qa_agent = qa_agent
        self.schema = schema
        self.show_labels = show_labels

    def can_handle(self, text: str, session) -> bool:
        return True

    def handle(self, text: str, session, trace) -> str:
        trace.add("mode", "llm")
        result = self.gate.evaluate(text, trace)
        fallback = ""
        if not result.verdict.valid:
            reply = self.schema.clarify_text
            fallback = "invalid classification"
            trace.add("fallback", fallback)
        else:
            agent_result = self.qa_agent.respond(result.verdict, result.decision, trace)
            reply = agent_result.text
            fallback = agent_result.fallback_reason
        append_turn(session, visible_user_text(result.decision), reply)
        emit(log, "answer", labels=list(result.labels), action=result.decision.action,
             tools_enabled=result.decision.tools_enabled, fallback=fallback, reply=reply)
        if self.show_labels:
            reply = f"[{', '.join(result.labels)}] {reply}"
        return reply
