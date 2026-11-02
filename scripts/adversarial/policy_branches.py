"""Policy-map branches and the coverage contract for the adversarial suite.

The symbolic matrix in ``tests/test_policy_matrix.py`` enumerates every
parent-child label combination. This module names the decision-tree branches
that the model-driven suite must exercise, so a missing branch is a test
failure rather than an unnoticed gap.
"""

BRANCHES = {
    "A1_prompt_injection_scope_forced_out":
        "prompt_injection forces out_of_scope even when the classifier says in_scope",
    "B1_safe_in_scope_answer":
        "independent safe in-scope span is answered",
    "B2_safe_out_of_scope_boundary":
        "independent safe out-of-scope span is a boundary",
    "B3_harmful_refuse":
        "independent harmful span is refused",
    "B4_toxic_refuse":
        "independent toxic span is refused",
    "B5_prompt_injection_refuse":
        "independent prompt-injection span is refused",
    "C1_resolved_safe_child_safe_parent_in_scope":
        "resolved safe child of a safe in-scope parent stays answerable",
    "C2_resolved_safe_child_safe_parent_out_of_scope":
        "resolved safe child of a safe out-of-scope parent inherits the boundary",
    "C3_resolved_safe_child_unsafe_parent":
        "resolved safe child inherits a harmful or toxic parent type",
    "C4_resolved_safe_child_prompt_injection_parent":
        "resolved safe child inherits prompt_injection and out_of_scope",
    "C5_resolved_unsafe_child_safe_parent":
        "resolved unsafe child of a safe parent is refused on its own type",
    "C6_resolved_unsafe_child_unsafe_parent_union":
        "resolved unsafe child and unsafe parent union their types",
    "C7_resolved_multi_hop_chain":
        "a multi-hop resolved chain carries safety types to the last child",
    "C8_resolved_child_own_out_of_scope":
        "a resolved child with its own out-of-scope label stays a boundary",
    "C9_resolved_scope_inherited_from_out_ancestor":
        "a resolved in-scope child inherits out_of_scope from an ancestor",
    "C10_unambiguous_child_of_injection":
        "an unambiguous child of an injection frame keeps its own handling",
    "D1_missing_target_safe_clarify":
        "a safe ambiguous span with no target is clarified",
    "D2_missing_target_unsafe_refuse":
        "an unsafe ambiguous span with no target is refused",
    "E1_answer_plus_refuse":
        "answer dominates refuse in the aggregate action",
    "E2_answer_plus_boundary":
        "answer dominates boundary in the aggregate action",
    "E3_answer_plus_clarify":
        "answer dominates clarify in the aggregate action",
    "E4_refuse_plus_boundary":
        "refuse dominates boundary when no answer exists",
    "E5_clarify_plus_boundary":
        "clarify dominates boundary when no answer or refuse exists",
    "E6_all_boundary":
        "all-boundary plan yields out_of_scope",
    "E7_all_clarify":
        "all-clarify plan yields clarify",
    "E8_all_refuse":
        "all-refuse plan yields refuse",
    "E9_answer_refuse_boundary":
        "answer plus refuse plus boundary yields answer",
    "E10_answer_clarify_boundary":
        "answer plus clarify plus boundary yields answer",
    "E11_refuse_clarify_boundary":
        "refuse plus clarify plus boundary yields refuse",
    "E12_answer_refuse_clarify_boundary":
        "all four handlings yield answer",
    "F1_invalid_discrimination_clarify":
        "a second discrimination failure is clarified",
    "F2_invalid_classification_clarify":
        "a second classification failure is clarified",
    "F3_transport_error_clarify":
        "a model transport error is clarified without a stage retry",
    "F4_relationship_cycle_invalid":
        "a relationship cycle invalidates discrimination and is clarified",
    "F5_relationship_entity_invalid":
        "a missing or misplaced resolved entity invalidates discrimination",
    "G1_redacted_prompt_text":
        "unsafe text and rationale are absent from the QA prompt",
    "G2_redacted_session_text":
        "unsafe and inherited-unsafe text is absent from the session turn",
    "G3_redacted_relationship_entity":
        "a relationship entity from a redacted target is hidden from the QA prompt",
}

# Branches that at least one model-driven case must exercise.
E2E_REQUIRED = tuple(name for name in BRANCHES if name[0] in "ABCDE")

# Branches proven by the deterministic fail-closed and redaction tests.
UNIT_REQUIRED = tuple(name for name in BRANCHES if name[0] in "FG")

ALL_REQUIRED = E2E_REQUIRED + UNIT_REQUIRED
