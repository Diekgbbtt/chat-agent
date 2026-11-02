"""Pure per-verbatim plan, relationship resolution, and aggregate action."""

from dataclasses import dataclass
from typing import Optional, Tuple

from agent.guard.verdict import (RELATIONSHIP_MISSING, RELATIONSHIP_RESOLVED,
                                 Label, Rationale, Relationship, Verbatim)


@dataclass(frozen=True)
class VerbatimPlan:
    index: int
    label: Label
    rationale: Rationale
    handling: str
    text: Optional[str]
    redacted: bool
    ambiguous: bool
    relationship: Optional[Relationship]


@dataclass(frozen=True)
class Decision:
    action: str
    tools_enabled: bool
    verbatim_plan: Tuple[VerbatimPlan, ...]
    overview: object
    safety_types: Tuple[str, ...]
    fallback_mode: str
    invalid: bool = False


def _append(text: str, note: str, limit: int) -> str:
    if not note:
        return text[:limit]
    room = max(0, limit - len(note))
    return (text[:room].rstrip() + note)[:limit]


class PolicyEngine:
    def __init__(self, schema):
        self.schema = schema

    def _ordered_types(self, types) -> Tuple[str, ...]:
        return tuple(name for name in self.schema.type_names if name in types)

    def _normalise_label(self, label: Label) -> Label:
        if "prompt_injection" in label.unsafe_types and label.scope != "out_of_scope":
            return Label(label.safety, label.unsafe_types, "out_of_scope")
        return label

    def _label(self, types, scope: str) -> Label:
        ordered = self._ordered_types(types)
        if ordered:
            return Label("unsafe", ordered, scope)
        return Label("safe", (), scope)

    def _resolve(self, verbatim: Verbatim, by_index):
        own = self._normalise_label(verbatim.label)
        if not verbatim.ambiguous:
            return own, "", False
        relationship = verbatim.relationship
        if relationship is None or relationship.status == RELATIONSHIP_MISSING:
            return own, " Relationship: missing semantic target.", True

        chain, seen = [], set()
        current = verbatim
        while True:
            if current.index in seen:
                return own, " Relationship: semantic target cycle.", True
            seen.add(current.index)
            chain.append(current)
            relation = current.relationship
            if not current.ambiguous or relation is None or relation.status == RELATIONSHIP_MISSING:
                break
            target = by_index.get(relation.target_verbatim_index)
            if target is None:
                return own, " Relationship: semantic target is missing.", True
            current = target

        if current.ambiguous:
            types, scope = set(), own.scope
            for item in chain:
                label = self._normalise_label(item.label)
                types.update(label.unsafe_types)
                if label.scope == "out_of_scope":
                    scope = "out_of_scope"
            return self._label(types, scope), " Relationship: missing semantic target.", True

        types, scope = set(), own.scope
        for item in chain:
            label = self._normalise_label(item.label)
            types.update(label.unsafe_types)
            if label.scope == "out_of_scope":
                scope = "out_of_scope"
        label = self._label(types, scope)
        notes = []
        inherited = label.unsafe_types != own.unsafe_types
        if inherited:
            notes.append(" Relationship: safety types inherited from the semantic target.")
        if own.scope == "in_scope" and scope == "out_of_scope":
            notes.append(" Relationship: scope inherited from the semantic target.")
        if not notes:
            notes.append(" Relationship: the semantic target supplies the missing meaning.")
        return label, "".join(notes), False

    def _handling(self, label: Label, unresolved: bool) -> str:
        if label.unsafe_types:
            return "refuse"
        if unresolved:
            return "clarify"
        if label.scope == "out_of_scope":
            return "boundary"
        return "answer"

    def _rationale(self, verbatim: Verbatim, note: str, dependent_indices) -> Rationale:
        notes = [note] if note else []
        for index in dependent_indices:
            notes.append(f" Relationship: verbatim {index} depends on this verbatim.")
        if not notes:
            return verbatim.rationale
        return Rationale(verbatim.rationale.safety,
                         _append(verbatim.rationale.scope, "".join(notes), self.schema.max_rationale_chars))

    def decide(self, verdict) -> Decision:
        if not verdict.valid:
            return Decision("clarify", False, (), None, (), "full", invalid=True)

        by_index = {verbatim.index: verbatim for verbatim in verdict.verbatims}
        dependents = {}
        for verbatim in verdict.verbatims:
            relationship = verbatim.relationship
            if (verbatim.ambiguous and relationship is not None
                    and relationship.status == RELATIONSHIP_RESOLVED):
                dependents.setdefault(relationship.target_verbatim_index, []).append(verbatim.index)

        plans = []
        for verbatim in verdict.verbatims:
            label, note, unresolved = self._resolve(verbatim, by_index)
            handling = self._handling(label, unresolved)
            redacted = handling == "refuse"
            plans.append(VerbatimPlan(
                verbatim.index, label,
                self._rationale(verbatim, note, dependents.get(verbatim.index, ())),
                handling,
                None if redacted else verbatim.text,
                redacted,
                verbatim.ambiguous,
                verbatim.relationship,
            ))

        handlings = {plan.handling for plan in plans}
        if "answer" in handlings:
            action = "answer"
        elif "refuse" in handlings:
            action = "refuse"
        elif "clarify" in handlings:
            action = "clarify"
        else:
            action = "out_of_scope"

        types = {name for plan in plans for name in plan.label.unsafe_types}
        safety_types = self._ordered_types(types)
        return Decision(action, action == "answer", tuple(plans), verdict.overview,
                        safety_types, "partial" if action == "answer" else "full")
