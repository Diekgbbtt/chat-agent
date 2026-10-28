# 06 — Per-verbatim policy and canonical fallback

**What to build:** A validated verdict maps to one handling per verbatim and one aggregate action.
Safety is assessed before scope for each verbatim.
A boundary suppresses only its own verbatim.
The fallback selector returns safe canonical text for every part kind.

**Blocked by:** 05.

**Status:** ready-for-agent

- [ ] An unsafe verbatim is `refuse`, in scope or out of scope.
- [ ] A safe out-of-scope verbatim is `boundary`.
- [ ] A safe in-scope verbatim with a blocking ambiguity is `clarify`.
- [ ] A safe in-scope verbatim without a blocking ambiguity is `answer`.
- [ ] An invalid verdict maps to a clarification decision with no tools.
- [ ] The aggregate action is any answer, else any refuse, else any clarify, else out-of-scope.
- [ ] `refuse` requires no answer handling and at least one refusal.
- [ ] `out_of_scope` requires every handling to be a boundary.
- [ ] `tools_enabled` is true only for an answer action.
- [ ] An unsafe plan has no text and is marked redacted.
- [ ] `fallback_mode` is full when no answer handling exists and partial otherwise.
- [ ] The canonical selector covers refusal by highest severity, boundary, clarification, capability, general, and unavailable answer.
- [ ] A frozen table covers every scope and safety pair and every aggregate combination.
