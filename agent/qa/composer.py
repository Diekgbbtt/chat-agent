"""Build deterministic parts when the QA model fails."""

import re

from agent.qa.types import AgentResult, Part

NEGATION = re.compile(r"(?:\bnot\b|\bnever\b|n't\b)", re.IGNORECASE)


class Composer:
    def __init__(self, renderer, schema):
        self.renderer = renderer
        self.schema = schema

    def _sparql(self, state):
        return [item.observation for item in state.observations if item.name == "run_sparql"]

    def _answer_observations(self, decision, state):
        answers = [plan for plan in decision.verbatim_plan if plan.handling == "answer"]
        observations = self._sparql(state)
        if not answers:
            return {}
        if not observations:
            return {plan.index: None for plan in answers}
        if len(observations) >= len(answers):
            chosen = observations[-len(answers):]
        else:
            chosen = [observations[-1]] * len(answers)
        return {plan.index: observation for plan, observation in zip(answers, chosen)}

    def compose(self, decision, state, reason: str) -> AgentResult:
        parts = []
        observations = self._answer_observations(decision, state)
        for plan in decision.verbatim_plan:
            if plan.handling == "refuse":
                text = self.schema.fallback_for(self._primary(plan, decision))
                parts.append(Part(plan.index, "refusal", text, addressed_safety_types=plan.label.unsafe_types))
            elif plan.handling == "boundary":
                parts.append(Part(plan.index, "boundary", self.schema.out_of_scope_text))
            elif plan.handling == "clarify":
                parts.append(Part(plan.index, "clarification", self.schema.clarify_text))
            else:
                observation = observations.get(plan.index)
                if NEGATION.search(plan.text or ""):
                    observation = None
                text, evidence = self.renderer.render(observation)
                if evidence:
                    parts.append(Part(plan.index, "factual_answer", text, evidence_row_ids=evidence))
                else:
                    parts.append(Part(plan.index, "general_answer", text))
        text = " ".join(part.text for part in parts)
        evidence = tuple(row_id for part in parts for row_id in part.evidence_row_ids)
        return AgentResult(tuple(parts), text, evidence, fallback_reason=reason)

    def _primary(self, plan, decision):
        types = plan.label.unsafe_types or decision.safety_types
        return next((name for name in self.schema.type_names if name in types), types[0])
