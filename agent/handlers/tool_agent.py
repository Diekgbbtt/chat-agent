"""Tools mode: guard gate, QA response agent, session seam."""

import logging

from agent.core import append_turn
from agent.guard.session import visible_user_text

log = logging.getLogger("agent.tool_agent")


class ToolAgentHandler:
    name = "tool_agent"

    def __init__(self, gate, qa_agent, schema, show_labels: bool = False):
        self.gate = gate
        self.qa_agent = qa_agent
        self.schema = schema
        self.show_labels = show_labels

    def can_handle(self, text: str, session) -> bool:
        return True

    def handle(self, text: str, session, trace) -> str:
        trace.add("mode", "tools")
        result = self.gate.evaluate(text, trace)
        if not result.verdict.valid:
            reply = self.schema.clarify_text
            trace.add("fallback", "invalid classification")
        else:
            agent_result = self.qa_agent.respond(result.verdict, result.decision, trace)
            reply = agent_result.text
        append_turn(session, visible_user_text(result.decision), reply)
        log.info("Room [%s] labels=%s action=%s", session.id, result.labels, result.decision.action)
        if self.show_labels:
            reply = f"[{', '.join(result.labels)}] {reply}"
        return reply
