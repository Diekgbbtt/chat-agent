# 06 - Per-verbatim policy, relationship resolution, and canonical fallback

**What to build:** A validated verdict maps to one effective label per verbatim and one aggregate action.
The policy normalises prompt-injection scope and resolves the relationship graph.
Safety is assessed before scope for each effective label.
A boundary suppresses only its own verbatim.
The fallback selector returns safe canonical text for every part kind.

**Blocked by:** 05.

**Status:** done

- [ ] An unsafe verbatim is `refuse`, in scope or out of scope.
- [ ] A safe out-of-scope verbatim is `boundary`.
- [ ] A safe in-scope verbatim with a missing semantic target is `clarify`.
- [ ] A safe in-scope verbatim with a resolved relationship is `answer`.
- [ ] An ambiguous child inherits the union of its semantic chain's safety types.
- [ ] An ambiguous child inherits scope only from an out-of-scope ancestor.
- [ ] An unambiguous child never inherits.
- [ ] `prompt_injection` forces out of scope.
- [ ] An invalid verdict maps to a clarification decision with no tools.
- [ ] The aggregate action is any answer, else any refuse, else any clarify, else out-of-scope.
- [ ] `refuse` requires no answer handling and at least one refusal.
- [ ] `out_of_scope` requires every handling to be a boundary.
- [ ] `tools_enabled` is true only for an answer action.
- [ ] An unsafe plan has no text and is marked redacted.
- [ ] `fallback_mode` is full when no answer handling exists and partial otherwise.
- [ ] The canonical selector covers refusal by first declared type, boundary, clarification, capability, general, and unavailable answer.
- [ ] A frozen table covers every scope and safety pair, the full 192-case parent-child matrix, and every aggregate combination.
