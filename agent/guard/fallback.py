"""Canonical text for every part kind; used when the model fails."""


def _kind(part) -> str:
    return getattr(part, "kind", None) or getattr(part, "handling", "")


def _types(part, decision):
    values = getattr(part, "addressed_safety_types", ()) or ()
    if not values:
        label = getattr(part, "label", None)
        values = getattr(label, "unsafe_types", ()) or ()
    if not values and decision is not None:
        values = getattr(decision, "safety_types", ()) or ()
    return tuple(values)


def _primary(types, schema) -> str:
    return next((name for name in schema.type_names if name in types), types[0])


def text_for(part, decision, schema) -> str:
    kind = _kind(part)
    if kind == "refuse":
        types = _types(part, decision)
        if types:
            return schema.fallback_for(_primary(types, schema))
        return schema.answer_unavailable_text
    if kind == "boundary":
        return schema.out_of_scope_text
    if kind == "clarification":
        return schema.clarify_text
    if kind == "capability_limit":
        return schema.capability_limit_text
    return schema.answer_unavailable_text
