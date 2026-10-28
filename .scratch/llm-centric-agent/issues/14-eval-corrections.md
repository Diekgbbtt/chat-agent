# 14 — Eval corrections and policy suite

**What to build:** The guardrail eval reflects the per-verbatim design.
The three scope cases are relabelled, the two mixed cases keep their safe answer and gain a refusal-part assertion, and a policy suite covers every handling and aggregate combination.
The legacy projection is the only eval bridge.

**Blocked by:** 07, 13.

**Status:** ready-for-agent

- [ ] `safe-hello`, `safe-thanks`, and `safe-capabilities` are labelled `out_of_scope`.
- [ ] `mixed-heat-robbery` and `mixed-jaws-insult` keep their expected safe answer.
- [ ] A unit assertion checks that each mixed case carries a refusal part.
- [ ] A policy suite covers every scope and safety pair.
- [ ] A policy suite covers every aggregate action combination.
- [ ] Invalid classification maps to clarification.
- [ ] The 44-case projection is 44 of 44 on the corrected set once a model is available.
- [ ] The no-LLM run is still recorded as 0 of 44 and is not misreported as a pass.
