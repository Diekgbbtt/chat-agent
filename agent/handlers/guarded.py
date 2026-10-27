"""Stage 3: guardrails first; the movie part is answered from the graph only, the LLM writes everything else."""

import logging

from agent.guardrails import SAFE, Guardrails
from agent.rephrase import rephrase

log = logging.getLogger("agent.guarded")


class GuardedHandler:
    name = "guarded"

    def __init__(self, factual, llm, show_labels: bool = False):
        self.factual = factual
        self.llm = llm
        self.guard = Guardrails(llm)
        self.show_labels = show_labels

    def can_handle(self, text: str, session) -> bool:
        return True

    def handle(self, text: str, session, trace) -> str:
        verdict = self.guard.check(text)
        trace.add("labels", verdict.labels)
        log.info("Room [%s] labels=%s", session.id, verdict.labels)

        parts = []
        question = verdict.movie_question or (text if verdict.labels == [SAFE] and not verdict.reply else "")
        if question:
            answer = self.factual.handle(question, session, trace)
            values = next((detail for step, detail in reversed(trace.steps) if step == "answer"), None)
            parts.append(rephrase(self.llm, question, values, answer) if values else answer)
        if verdict.reply and verdict.labels != [SAFE] or not parts:
            parts.append(verdict.reply)
        reply = " ".join(part for part in parts if part)
        if self.show_labels:
            reply = f"[{', '.join(verdict.labels)}] {reply}"
        return reply
