"""Guard-only bridge: typed guard and policy, legacy factual answer, canonical other parts."""

import logging

from agent.core import append_turn
from agent.guard import fallback
from agent.guard.session import visible_user_text

log = logging.getLogger("agent.guard_only")


class GuardOnlyHandler:
    name = "guard_only"

    def __init__(self, factual, gate, schema, show_labels: bool = False):
        self.factual = factual
        self.gate = gate
        self.schema = schema
        self.show_labels = show_labels

    def can_handle(self, text: str, session) -> bool:
        return True

    def _part(self, plan, decision, session, trace) -> str:
        if plan.handling == "answer":
            return self.factual.handle(plan.text, session, trace)
        if plan.handling == "boundary":
            return self.schema.out_of_scope_text
        if plan.handling == "clarify":
            return self.schema.clarify_text
        return fallback.text_for(plan, decision, self.schema)

    def handle(self, text: str, session, trace) -> str:
        trace.add("mode", "guard_only")
        result = self.gate.evaluate(text, trace)
        log.info("Room [%s] labels=%s action=%s", session.id, result.labels, result.decision.action)
        if not result.verdict.valid:
            reply = self.schema.clarify_text
        else:
            reply = " ".join(part for part in
                             (self._part(plan, result.decision, session, trace)
                              for plan in result.decision.verbatim_plan) if part)
        append_turn(session, visible_user_text(result.decision), reply)
        if self.show_labels:
            reply = f"[{', '.join(result.labels)}] {reply}"
        return reply
