"""Canonical guard labels for traces and evals.

Safety takes precedence over scope for one verbatim.
An unsafe verbatim emits its safety names and no scope label.
The plan carries the effective label after relationship inheritance.
"""

CANONICAL_LABELS = ("safe_in_scope", "out_of_scope", "harmful", "toxic", "prompt_injection")


def verbatim_labels(label) -> tuple:
    if label.unsafe_types:
        return tuple(name for name in CANONICAL_LABELS if name in label.unsafe_types)
    return ("safe_in_scope" if label.scope == "in_scope" else "out_of_scope",)


def canonical_labels(decision) -> tuple:
    if decision.invalid:
        return ()
    labels = set()
    for plan in decision.verbatim_plan:
        labels.update(verbatim_labels(plan.label))
    return tuple(name for name in CANONICAL_LABELS if name in labels)
