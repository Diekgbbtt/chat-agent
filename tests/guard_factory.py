"""Build validated two-stage guard results for tests."""

from dataclasses import dataclass

from agent.guard.policy import PolicyEngine
from agent.guard.schema import load_schema
from agent.guard.verdict import (RawClassification, RawDiscrimination,
                                 validate_classification, validate_discrimination)

SCHEMA = load_schema("agent/data/guardrails.json")


@dataclass(frozen=True)
class SpanSpec:
    text: str
    safety: str = "safe"
    types: tuple = ()
    scope: str = "in_scope"
    ambiguous: bool = False
    relationship: dict = None


def discrimination(text, specs, summary="A request."):
    raw = RawDiscrimination(
        overview={"summary": summary},
        verbatims=[{"text": spec.text,
                    "ambiguous": spec.ambiguous,
                    **({"relationship": spec.relationship} if spec.relationship is not None else {})}
                   for spec in specs],
    )
    return validate_discrimination(raw, text, SCHEMA)


def classification(specs):
    return RawClassification(verbatims=[
        {"index": index,
         "label": {"safety": spec.safety, "unsafe_types": list(spec.types), "scope": spec.scope},
         "rationale": {"safety": "Safety note.", "scope": "Scope note."}}
        for index, spec in enumerate(specs)
    ])


def verdict(text, specs, summary="A request."):
    discriminated = discrimination(text, specs, summary)
    return validate_classification(classification(specs), discriminated, SCHEMA)


def decision(text, specs, summary="A request."):
    return PolicyEngine(SCHEMA).decide(verdict(text, specs, summary))


def verdict_and_decision(text, specs, summary="A request."):
    result = verdict(text, specs, summary)
    return result, PolicyEngine(SCHEMA).decide(result)
