"""Session helpers for the guard."""


def visible_user_text(decision) -> str:
    """The only user text that may enter the session turn list."""
    if decision.invalid:
        return ""
    return " ".join(plan.text for plan in decision.verbatim_plan
                    if plan.handling == "answer" and plan.label.safety == "safe"
                    and plan.label.scope == "in_scope" and not plan.redacted and plan.text)
