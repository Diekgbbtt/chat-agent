# 11 — QA factual answer loop

**What to build:** For one answerable verbatim, the QA model calls `resolve_entity`, then `run_sparql`, then `submit_response` with a factual answer and cited row IDs.
The loop enforces the step budget, deadline, one tool call per turn, and repair on malformed output.
The validator checks coverage, kind, evidence, values, and content.

**Blocked by:** 02, 08, 09, 10.

**Status:** ready-for-agent

- [ ] The loop exposes only `submit_response` when tools are disabled.
- [ ] The loop exposes both graph tools when the decision enables tools.
- [ ] A factual part must cite at least one row from a prior observation.
- [ ] Cited row IDs must exist in the observation log.
- [ ] Every number and date in a factual part appears in a cited row.
- [ ] Every entity label in a factual part appears in a cited row or the question.
- [ ] A part kind must match its handling.
- [ ] One repair is allowed, then the deterministic renderer is used.
- [ ] The step budget and deadline stop the loop.
- [ ] A repeated tool call is rejected.
- [ ] Tests cover a full factual slice and each failure.
