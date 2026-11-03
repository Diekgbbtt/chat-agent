"""Normalise, discriminate, classify, validate, plan, and label one message."""

from dataclasses import dataclass

from agent.guard.classifier import GuardClassifier
from agent.guard.discriminator import GuardDiscriminator
from agent.guard.labels import canonical_labels
from agent.guard.policy import Decision, PolicyEngine
from agent.guard.verdict import (Discrimination, Verdict, invalid_discrimination,
                                 invalid_verdict, validate_classification,
                                 validate_discrimination)
from agent.llm.client import LLMError
from agent.normalize import normalise


@dataclass(frozen=True)
class GuardResult:
    verdict: Verdict
    discrimination: Discrimination
    decision: Decision
    labels: tuple


def _relationship_detail(relationship):
    if relationship is None:
        return None
    return {"target_verbatim_index": relationship.target_verbatim_index,
            "entity": relationship.entity,
            "status": relationship.status}


def _span_detail(discrimination) -> list:
    return [{"index": span.index,
             "text": span.text,
             "ambiguous": span.ambiguous,
             "relationship": _relationship_detail(span.relationship)}
            for span in discrimination.spans]


def _verbatim_detail(verdict) -> list:
    return [{"index": verbatim.index,
             "text": verbatim.text,
             "ambiguous": verbatim.ambiguous,
             "relationship": _relationship_detail(verbatim.relationship),
             "safety": verbatim.label.safety,
             "unsafe_types": list(verbatim.label.unsafe_types),
             "scope": verbatim.label.scope,
             "rationale": {"safety": verbatim.rationale.safety, "scope": verbatim.rationale.scope}}
            for verbatim in verdict.verbatims]


def _plan_detail(decision) -> list:
    return [{"index": plan.index,
             "handling": plan.handling,
             "redacted": plan.redacted,
             "safety": plan.label.safety,
             "unsafe_types": list(plan.label.unsafe_types),
             "scope": plan.label.scope,
             "ambiguous": plan.ambiguous,
             "relationship": _relationship_detail(plan.relationship)}
            for plan in decision.verbatim_plan]


def _policy_detail(decision) -> dict:
    return {"action": decision.action,
            "tools_enabled": decision.tools_enabled,
            "safety_types": list(decision.safety_types),
            "fallback_mode": decision.fallback_mode,
            "invalid": decision.invalid}


class GuardGate:
    def __init__(self, client, schema):
        self.schema = schema
        self.discriminator = GuardDiscriminator(client, schema)
        self.classifier = GuardClassifier(client, schema)
        self.policy = PolicyEngine(schema)

    def _discriminate(self, text: str, trace=None) -> Discrimination:
        raw = self.discriminator.discriminate(text)
        result = validate_discrimination(raw, text, self.schema)
        if not result.valid:
            if trace is not None:
                trace.add("guard_retry", {"stage": "discrimination", "error": result.error})
            raw = self.discriminator.discriminate(text, correction=result.error or "invalid output")
            result = validate_discrimination(raw, text, self.schema)
        return result

    def _classify(self, text: str, discrimination: Discrimination, trace=None) -> Verdict:
        raw = self.classifier.classify(text, discrimination)
        verdict = validate_classification(raw, discrimination, self.schema)
        if not verdict.valid:
            if trace is not None:
                trace.add("guard_retry", {"stage": "classification", "error": verdict.error})
            raw = self.classifier.classify(text, discrimination,
                                            correction=verdict.error or "invalid output")
            verdict = validate_classification(raw, discrimination, self.schema)
        return verdict

    def evaluate(self, text: str, trace=None) -> GuardResult:
        normalized = normalise(text)
        if trace is not None:
            trace.add("normalized", normalized)
        try:
            discrimination = self._discriminate(normalized, trace)
        except LLMError as exc:
            discrimination = invalid_discrimination(str(exc))
        if discrimination.valid:
            try:
                verdict = self._classify(normalized, discrimination, trace)
            except LLMError as exc:
                verdict = invalid_verdict(str(exc), self.schema)
        else:
            verdict = invalid_verdict(discrimination.error or "invalid discrimination", self.schema)

        decision = self.policy.decide(verdict)
        labels = canonical_labels(decision)
        if trace is not None:
            trace.add("discrimination", {"summary": discrimination.overview.summary if discrimination.overview else "",
                                         "error": discrimination.error,
                                         "spans": _span_detail(discrimination)})
            trace.add("classification", {"error": verdict.error,
                                         "verbatims": _verbatim_detail(verdict)})
            trace.add("plan", _plan_detail(decision))
            trace.add("policy", _policy_detail(decision))
            trace.add("labels", set(labels))
        return GuardResult(verdict, discrimination, decision, labels)
