"""Typed guard discrimination, classification, and validation."""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

RELATIONSHIP_RESOLVED = "resolved"
RELATIONSHIP_MISSING = "missing semantic target"


@dataclass(frozen=True)
class Relationship:
    target_verbatim_index: Optional[int]
    entity: Optional[str]
    status: str


@dataclass(frozen=True)
class Span:
    index: int
    text: str
    ambiguous: bool
    relationship: Optional[Relationship]


@dataclass(frozen=True)
class Overview:
    summary: str


@dataclass(frozen=True)
class Discrimination:
    valid: bool
    overview: Optional[Overview]
    spans: Tuple[Span, ...]
    error: Optional[str] = None


@dataclass(frozen=True)
class Label:
    safety: str
    unsafe_types: Tuple[str, ...]
    scope: str


@dataclass(frozen=True)
class Rationale:
    safety: str
    scope: str


@dataclass(frozen=True)
class Verbatim:
    index: int
    text: str
    label: Label
    rationale: Rationale
    ambiguous: bool = False
    relationship: Optional[Relationship] = None


@dataclass(frozen=True)
class RawDiscrimination:
    overview: dict
    verbatims: List[dict]


@dataclass(frozen=True)
class RawClassification:
    verbatims: List[dict]


@dataclass(frozen=True)
class Verdict:
    valid: bool
    overview: Optional[Overview]
    verbatims: Tuple[Verbatim, ...]
    error: Optional[str] = None


def invalid_discrimination(error: str) -> Discrimination:
    return Discrimination(False, None, (), str(error))


def invalid_verdict(error: str, schema=None) -> Verdict:
    return Verdict(False, None, (), str(error))


_SEPARATOR = re.compile(r"(?:\s|[,.;:!?()\[\]]|\b(?:and|then|also|plus|or|but|yet|so|however)\b)+",
                        re.IGNORECASE)


def _is_separator(value: str) -> bool:
    return not value or bool(_SEPARATOR.fullmatch(value))


def _parse_summary(overview, schema) -> Overview:
    if not isinstance(overview, dict):
        raise ValueError("overview must be an object")
    summary = overview.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("overview.summary must be non-empty")
    if len(summary) > schema.max_overview_chars:
        raise ValueError("overview.summary is too long")
    return Overview(summary)


def _parse_spans(raw_verbatims, text: str, schema) -> Tuple[Span, ...]:
    if not isinstance(raw_verbatims, list) or not raw_verbatims:
        raise ValueError("verbatims must be a non-empty list")
    if len(raw_verbatims) > schema.max_verbatims:
        raise ValueError("too many verbatims")
    parsed = []
    for index, item in enumerate(raw_verbatims):
        if not isinstance(item, dict):
            raise ValueError("each verbatim must be an object")
        span_text = item.get("text")
        if not isinstance(span_text, str) or not span_text:
            raise ValueError("verbatim text must be non-empty")
        ambiguous = item.get("ambiguous")
        if not isinstance(ambiguous, bool):
            raise ValueError("verbatim ambiguous flag must be a boolean")
        parsed.append(Span(index, span_text, ambiguous, None))
    cursor = 0
    for span in parsed:
        start = text.find(span.text, cursor)
        if start < 0:
            raise ValueError(f"verbatim is not an exact input substring: {span.text[:40]}")
        if not _is_separator(text[cursor:start]):
            raise ValueError(f"input content is not covered before: {span.text[:40]}")
        cursor = start + len(span.text)
    if not _is_separator(text[cursor:]):
        raise ValueError("input content is not covered after the last verbatim")
    return tuple(parsed)


def _parse_relationship(item, span: Span, spans, schema) -> Optional[Relationship]:
    raw = item.get("relationship")
    if not span.ambiguous:
        if raw not in (None, {}):
            raise ValueError("a non-ambiguous verbatim must not carry a relationship")
        return None
    if not isinstance(raw, dict):
        raise ValueError("an ambiguous verbatim must carry a relationship object")
    status = raw.get("status")
    if status not in (RELATIONSHIP_RESOLVED, RELATIONSHIP_MISSING):
        raise ValueError("relationship status is invalid")
    target = raw.get("target_verbatim_index")
    entity = raw.get("entity")
    if status == RELATIONSHIP_MISSING:
        if target is not None or entity is not None:
            raise ValueError("a missing semantic target must not name a target or entity")
        return Relationship(None, None, RELATIONSHIP_MISSING)
    if not isinstance(target, int) or isinstance(target, bool) or not 0 <= target < len(spans):
        raise ValueError("relationship target is out of range")
    if target == span.index:
        raise ValueError("a relationship target cannot be the verbatim itself")
    if not isinstance(entity, str) or not entity.strip():
        raise ValueError("a resolved relationship entity must be explicit non-empty text")
    if len(entity) > schema.max_rationale_chars:
        raise ValueError("relationship entity is too long")
    pattern = re.escape(entity)
    if entity[:1].isalnum():
        pattern = rf"\b{pattern}"
    if entity[-1:].isalnum():
        pattern = rf"{pattern}\b"
    if not re.search(pattern, spans[target].text, re.IGNORECASE):
        raise ValueError("relationship entity is not in the target verbatim")
    return Relationship(target, entity, RELATIONSHIP_RESOLVED)


def _has_cycle(spans) -> bool:
    resolved = {span.index: span.relationship.target_verbatim_index
                for span in spans
                if span.ambiguous and span.relationship and span.relationship.status == RELATIONSHIP_RESOLVED}
    for start in resolved:
        seen = set()
        node = start
        while node in resolved:
            if node in seen:
                return True
            seen.add(node)
            node = resolved[node]
    return False


def validate_discrimination(raw: RawDiscrimination, text: str, schema) -> Discrimination:
    try:
        if not isinstance(raw, RawDiscrimination):
            raise ValueError("the discrimination object is missing")
        overview = _parse_summary(raw.overview, schema)
        spans = _parse_spans(raw.verbatims, text, schema)
        with_relationships = tuple(
            Span(span.index, span.text, span.ambiguous,
                 _parse_relationship(item, span, spans, schema))
            for span, item in zip(spans, raw.verbatims)
        )
        if _has_cycle(with_relationships):
            raise ValueError("relationship graph has a cycle")
        return Discrimination(True, overview, with_relationships)
    except (TypeError, ValueError) as exc:
        return invalid_discrimination(str(exc))


def _parse_label(item, schema) -> Tuple[Label, Rationale]:
    label = item.get("label")
    rationale = item.get("rationale")
    if not isinstance(label, dict) or not isinstance(rationale, dict):
        raise ValueError("verbatim label and rationale are required")
    safety = label.get("safety")
    types = label.get("unsafe_types")
    scope = label.get("scope")
    if safety not in ("safe", "unsafe"):
        raise ValueError("unknown safety value")
    if scope not in schema.scopes:
        raise ValueError("unknown scope value")
    if not isinstance(types, list) or any(not isinstance(value, str) for value in types):
        raise ValueError("unsafe_types must be a list of strings")
    if len(set(types)) != len(types):
        raise ValueError("unsafe types must be unique")
    if any(value not in schema.safety_types for value in types):
        raise ValueError("unknown unsafe type")
    if safety == "safe" and types:
        raise ValueError("a safe verbatim has no unsafe types")
    if safety == "unsafe" and not types:
        raise ValueError("an unsafe verbatim needs at least one type")
    for field_name in ("safety", "scope"):
        value = rationale.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} rationale must be non-empty")
        if len(value) > schema.max_rationale_chars:
            raise ValueError(f"{field_name} rationale is too long")
    return (Label(safety, tuple(types), scope),
            Rationale(rationale["safety"], rationale["scope"]))


def validate_classification(raw: RawClassification, discrimination: Discrimination, schema) -> Verdict:
    try:
        if not discrimination.valid:
            raise ValueError(discrimination.error or "discrimination is invalid")
        if not isinstance(raw, RawClassification):
            raise ValueError("the classification object is missing")
        items = raw.verbatims
        if not isinstance(items, list):
            raise ValueError("verbatims must be a list")
        if len(items) != len(discrimination.spans):
            raise ValueError(f"expected {len(discrimination.spans)} labels, got {len(items)}")
        verbatims = []
        for span, item in zip(discrimination.spans, items):
            if not isinstance(item, dict):
                raise ValueError("each classification must be an object")
            if item.get("index") != span.index:
                raise ValueError(f"labels are not in verbatim order at index {span.index}")
            label, rationale = _parse_label(item, schema)
            verbatims.append(Verbatim(span.index, span.text, label, rationale,
                                      span.ambiguous, span.relationship))
        return Verdict(True, discrimination.overview, tuple(verbatims))
    except (TypeError, ValueError) as exc:
        return invalid_verdict(str(exc), schema)
