# 16 - Adversarial policy-map evaluation

**What to build:** A model-driven multi-part suite that covers every policy-map branch, stresses decomposition, and probes safe/unsafe boundaries.

**Blocked by:** 05, 06.

**Status:** suite done; local measurement pending.

- [x] 41 cases in `evals/adversarial/policy_e2e.jsonl`.
- [x] 30 model-driven policy branches declared in `scripts/adversarial/policy_branches.py`.
- [x] Static coverage test rejects a missing branch.
- [x] Runner scores action, span count, own labels, effective labels, relationships, reply, and redaction.
- [x] Local three-repeat gate defined.
- [ ] Extended pass@1 at or above 95 percent on the local endpoint.
- [ ] Three-repeat stability on the local endpoint.
- [ ] All 30 branches observed on the local endpoint.
- [x] Gender mismatch is non-ambiguous and has no relationship.
- [x] Self-harm realism is safe; a step request is harmful.
- [x] QA repeat loop fixed with a repeat-call guard, forced final submit, and distinct-observation fallback.
- [x] Local endpoint required for the measurement gate.
- [x] Exact label cardinality enforced with `minItems` and `maxItems`.
- [ ] Review the self-harm refusal wording with a human reviewer.
- [x] Accept harmful or toxic for hate-speech overlap through `labels_any_of`.
- [ ] Run the suite on the T4 local endpoint.
