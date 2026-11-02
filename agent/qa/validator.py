"""Validate submitted parts before they are joined into a reply."""

import re
from dataclasses import dataclass, field

from agent.qa.types import Part

DEFAULT_LIMITS = {
    "factual_answer": 400,
    "general_answer": 400,
    "capability_limit": 300,
    "refusal": 300,
    "clarification": 300,
    "boundary": 160,
}
ANSWER_KINDS = {"factual_answer", "general_answer", "capability_limit"}
HANDLING_KINDS = {
    "answer": ANSWER_KINDS,
    "refuse": {"refusal"},
    "clarify": {"clarification"},
    "boundary": {"boundary"},
}
FORBIDDEN = re.compile(r"(https?://|```|\bQ\d+\b|\bP\d+\b)")
NUMBER = re.compile(r"\b\d[\d,.]*\b")
PROPER = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Validation:
    ok: bool
    error: str = ""
    parts: tuple = field(default_factory=tuple)


def _words(text: str) -> list:
    return WORD.findall(text.casefold())


def _has_ngram(query: str, source: str, size: int = 4) -> bool:
    query_words = _words(query)
    source_words = _words(source)
    if len(source_words) < size:
        return False
    grams = {tuple(source_words[index:index + size]) for index in range(len(source_words) - size + 1)}
    return any(tuple(query_words[index:index + size]) in grams
               for index in range(len(query_words) - size + 1))


def _cited_rows(state, row_ids):
    rows = []
    for item in state.observations:
        if item.name != "run_sparql":
            continue
        for row in item.observation.rows:
            if row["row_id"] in row_ids:
                rows.append(row)
    return rows


def _row_text(rows) -> str:
    return " ".join(str(value) for row in rows for value in row.values()).casefold()


class AnswerValidator:
    def __init__(self, schema, limits=None):
        self.schema = schema
        self.limits = dict(DEFAULT_LIMITS)
        if limits:
            self.limits.update(limits)

    def validate(self, payload, state) -> Validation:
        try:
            return self._validate(payload, state)
        except (TypeError, ValueError, KeyError) as exc:
            return Validation(False, str(exc))

    def _validate(self, payload, state) -> Validation:
        if not isinstance(payload, dict):
            raise ValueError("the response must be an object")
        items = payload.get("parts")
        if not isinstance(items, list):
            raise ValueError("parts must be a list")
        plans = state.decision.verbatim_plan
        if len(items) != len(plans):
            raise ValueError(f"expected {len(plans)} parts, got {len(items)}")

        parts = []
        for item, plan in zip(items, plans):
            if not isinstance(item, dict):
                raise ValueError("each part must be an object")
            if item.get("verbatim_index") != plan.index:
                raise ValueError(f"parts are not in verbatim order at index {plan.index}")
            kind = item.get("kind")
            if kind not in HANDLING_KINDS[plan.handling]:
                raise ValueError(f"kind {kind} does not match handling {plan.handling}")
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("part text must be non-empty")
            if len(text) > self.limits[kind]:
                raise ValueError(f"{kind} text is too long")
            if FORBIDDEN.search(text):
                raise ValueError("part text contains a URL, code fence, QID, or property ID")

            evidence = item.get("evidence_row_ids", [])
            safety = item.get("addressed_safety_types", [])
            if not isinstance(evidence, list) or not all(isinstance(value, str) for value in evidence):
                raise ValueError("evidence_row_ids must be a list of strings")
            if not isinstance(safety, list) or not all(isinstance(value, str) for value in safety):
                raise ValueError("addressed_safety_types must be a list of strings")

            if kind == "factual_answer":
                self._check_factual(text, evidence, state, plan)
            else:
                if evidence:
                    raise ValueError("a non-factual part cannot cite evidence")
                if safety and kind != "refusal":
                    raise ValueError("only a refusal part addresses safety types")

            if kind == "refusal":
                if set(safety) != set(plan.label.unsafe_types):
                    raise ValueError("refusal safety types do not match the verbatim")
            elif safety:
                raise ValueError("only a refusal part addresses safety types")

            if kind == "clarification":
                if text.count("?") != 1 or not text.rstrip().endswith("?"):
                    raise ValueError("a clarification must ask exactly one question")
                if _has_ngram(text, plan.text or "", size=7):
                    raise ValueError("a clarification must not quote more than six consecutive words")
            if kind == "boundary" and _has_ngram(text, plan.text or "", size=4):
                raise ValueError("a boundary part must state only the scope limit")

            parts.append(Part(plan.index, kind, text, tuple(evidence), tuple(safety)))

        redacted = {plan.index for plan in state.decision.verbatim_plan if plan.redacted}
        for query in state.tool_queries:
            for verbatim in state.verdict.verbatims:
                if verbatim.index in redacted and _has_ngram(query, verbatim.text):
                    raise ValueError("a tool query reuses redacted text")
        return Validation(True, "", tuple(parts))

    def _check_factual(self, text, evidence, state, plan):
        if not evidence:
            raise ValueError("a factual answer must cite at least one row")
        rows = _cited_rows(state, set(evidence))
        if len(rows) != len(set(evidence)):
            raise ValueError("a cited row does not exist in the observations")
        row_text = _row_text(rows)
        for token in NUMBER.findall(text):
            if token.replace(",", "") not in row_text:
                raise ValueError(f"number {token} is not in a cited row")
        source = f"{plan.text or ''} {row_text}"
        for label in PROPER.findall(text):
            if label.casefold() not in source.casefold():
                raise ValueError(f"label {label} is not in a cited row or the question")
