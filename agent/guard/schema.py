"""Load and validate the data-driven guard schema."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

SAFETY_TYPES = ("harmful", "toxic", "prompt_injection")
REQUIRED_TYPE_FIELDS = ("name", "description", "fallback_text")
FORBIDDEN_TYPE_FIELDS = ("severity", "tone", "legacy_label")


class SchemaError(ValueError):
    """The guard schema is incomplete or inconsistent."""


@dataclass(frozen=True)
class SafetyType:
    name: str
    description: str
    fallback_text: str


@dataclass(frozen=True)
class PairExample:
    message: str
    scope: str
    safety: str


@dataclass(frozen=True)
class GuardrailSchema:
    scopes: Tuple[str, ...]
    safety_types: Dict[str, SafetyType]
    examples: Tuple[PairExample, ...]
    guard_max_output_tokens: int
    max_verbatims: int
    max_rationale_chars: int
    max_overview_chars: int
    clarify_text: str
    out_of_scope_text: str
    capability_limit_text: str
    answer_unavailable_text: str

    @property
    def type_names(self) -> Tuple[str, ...]:
        return tuple(self.safety_types)

    def fallback_for(self, name: str) -> str:
        return self.safety_types[name].fallback_text


def _require(condition, message: str) -> None:
    if not condition:
        raise SchemaError(message)


def _positive_int(data, key: str) -> int:
    value = data.get(key)
    _require(isinstance(value, int) and value > 0, f"{key} must be a positive integer")
    return value


def _text(data, key: str) -> str:
    value = data.get(key)
    _require(isinstance(value, str) and value.strip(), f"{key} must be non-empty text")
    return value


def _parse_types(items) -> Dict[str, SafetyType]:
    _require(isinstance(items, list) and items, "safety_types must be a non-empty list")
    result = {}
    for item in items:
        _require(isinstance(item, dict), "each safety type must be an object")
        for field_name in REQUIRED_TYPE_FIELDS:
            _require(field_name in item, f"safety type is missing {field_name}")
        name = item["name"]
        _require(isinstance(name, str) and name and name != "allow", "safety type name is invalid")
        _require(name in SAFETY_TYPES, f"unknown safety type: {name}")
        _require(name not in result, f"duplicate safety type: {name}")
        for field_name in FORBIDDEN_TYPE_FIELDS:
            _require(field_name not in item, f"safety type {name} must not carry {field_name}")
        for field_name in ("description", "fallback_text"):
            _require(isinstance(item[field_name], str) and item[field_name].strip(),
                     f"{field_name} of {name} must be non-empty text")
        result[name] = SafetyType(name, item["description"], item["fallback_text"])
    _require(tuple(result) == SAFETY_TYPES,
             "safety_types must declare harmful, toxic, and prompt_injection in that order")
    return result


def _parse_scopes(items) -> Tuple[str, ...]:
    _require(isinstance(items, list), "scope_values must be a list")
    _require(len(items) == 2 and set(items) == {"in_scope", "out_of_scope"},
             "scope_values must be in_scope and out_of_scope")
    return tuple(items)


def _parse_examples(items, scopes, types) -> Tuple[PairExample, ...]:
    _require(isinstance(items, list), "examples must be a list")
    allowed = {"safe", *types}
    parsed = []
    seen = set()
    for item in items:
        _require(isinstance(item, dict), "each example must be an object")
        _require(item.get("safety") != "allow", "the allow label is not permitted")
        message, scope, safety = item.get("message"), item.get("scope"), item.get("safety")
        _require(isinstance(message, str) and message.strip(), "example message must be non-empty")
        _require(scope in scopes, f"unknown example scope: {scope}")
        _require(safety in allowed, f"unknown example safety: {safety}")
        _require((scope, safety) not in seen, f"duplicate example pair: {scope}, {safety}")
        seen.add((scope, safety))
        parsed.append(PairExample(message, scope, safety))
    expected = {(scope, safety) for scope in scopes for safety in allowed}
    _require(seen == expected, "examples must cover every scope and safety pair")
    return tuple(parsed)


def load_schema(path) -> GuardrailSchema:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SchemaError(f"cannot read guard schema: {exc}") from exc
    _require(isinstance(data, dict), "guard schema must be an object")
    _require("severity_order" not in data, "severity_order is not permitted")
    _require("max_ambiguities" not in data, "max_ambiguities is not permitted")

    scopes = _parse_scopes(data.get("scope_values"))
    types = _parse_types(data.get("safety_types"))
    examples = _parse_examples(data.get("examples"), scopes, types)

    for item in data["safety_types"]:
        _require("allow" not in item, "the allow label is not permitted")

    return GuardrailSchema(
        scopes=scopes,
        safety_types=types,
        examples=examples,
        guard_max_output_tokens=_positive_int(data, "guard_max_output_tokens"),
        max_verbatims=_positive_int(data, "max_verbatims"),
        max_rationale_chars=_positive_int(data, "max_rationale_chars"),
        max_overview_chars=_positive_int(data, "max_overview_chars"),
        clarify_text=_text(data, "clarify_text"),
        out_of_scope_text=_text(data, "out_of_scope_text"),
        capability_limit_text=_text(data, "capability_limit_text"),
        answer_unavailable_text=_text(data, "answer_unavailable_text"),
    )
