"""Stage 3: guard -> planner -> graph. Only the guard's copied movie questions reach the planner, and only
checked requests reach the graph; the LLM writes the refusals and may rephrase answers, never facts."""

import logging

from agent import nlg
from agent.guardrails import SAFE, Guardrails
from agent.planner import PlanError, Planner
from agent.query import QueryEngine
from agent.rephrase import rephrase

log = logging.getLogger("agent.guarded")


class GuardedHandler:
    name = "guarded"

    def __init__(self, kg, lexicon, llm, show_labels: bool = False, rephrase_answers: bool = True):
        self.llm = llm
        self.guard = Guardrails(llm)
        self.engine = QueryEngine(kg, lexicon)
        self.planner = Planner(llm, self.engine)
        self.show_labels = show_labels
        self.rephrase_answers = rephrase_answers

    def can_handle(self, text: str, session) -> bool:
        return True

    def handle(self, text: str, session, trace) -> str:
        verdict = self.guard.check(text)
        if verdict is None:
            trace.add("labels", [])
            return nlg.not_understood()
        trace.add("labels", verdict.labels)
        trace.add("movie_questions", verdict.movie_questions)
        log.info("Room [%s] labels=%s questions=%s", session.id, verdict.labels, verdict.movie_questions)

        parts = [self._answer(question, session, trace) for question in verdict.movie_questions]
        if verdict.reply and (verdict.labels != [SAFE] or not parts):
            parts.append(verdict.reply)
        elif not parts:
            parts.append(nlg.capabilities())  # small talk the guard left without a reply
        reply = " ".join(part for part in parts if part) or nlg.not_understood()
        if self.show_labels:
            reply = f"[{', '.join(verdict.labels)}] {reply}"
        return reply

    def _answer(self, question: str, session, trace) -> str:
        """Plan, run, and plan once more with feedback if the plan was invalid or found nothing."""
        feedback, answers, error = "", [], None
        for _ in range(2):
            try:
                requests = self.planner.plan(question, feedback)
            except PlanError as e:
                error = e
                log.info("Room [%s] invalid plan for %r: %s", session.id, question, e)
                feedback = f"Your last answer was not valid: {e}. Answer with the JSON format only."
                continue
            trace.add("requests", requests)
            log.info("Room [%s] requests=%s", session.id, requests)
            answers = [self.engine.run(request, trace) for request in requests]
            if any(answer.found for answer in answers):
                break
            feedback = ("Those requests found nothing in the graph. Try other properties, the other direction, "
                        f"or a different kind. Last requests: {requests}")
        if not answers:
            # the planner only reached for properties the graph doesn't have ("date of birth")
            return nlg.no_property() if "unknown property" in str(error) else nlg.not_understood()
        texts = []
        for request, answer in zip(requests, answers):
            trace.add("answer", answer.values)
            if answer.found and self.rephrase_answers:
                # with several requests, each sentence may only use its own part of the question:
                # "Who directed Inception and Jaws?" must not become "Nolan directed Inception and Jaws"
                part = question if len(answers) == 1 else self.engine.describe(request)
                texts.append(rephrase(self.llm, part, answer.values, answer.text))
            else:
                texts.append(answer.text)
        return " ".join(texts)
