# 05 — Guard classifier and typed verdict

**What to build:** The guard model returns one forced `submit_classification` call.
The runtime validates its overview, verbatims, labels, rationales, exact spans, order, coverage, and ambiguities.
A schema failure retries once with the validation error.
A second failure becomes an invalid verdict that the policy maps to clarification.

**Blocked by:** 02, 03, 04.

**Status:** ready-for-agent

- [ ] The classifier prompt renders all 14 pair examples from the schema.
- [ ] The classifier forces `submit_classification` and caps output tokens.
- [ ] The parsed object has an overview and ordered verbatims.
- [ ] Each verbatim has `label` and `rationale`.
- [ ] The validator checks exact spans, non-overlap, input order, and alphanumeric coverage.
- [ ] Separator whitespace and punctuation are allowed between verbatims.
- [ ] The validator checks known scopes, known safety types, and the safe/unsafe invariant.
- [ ] The validator checks rationale, summary, and ambiguity lengths.
- [ ] A blocking ambiguity must carry a valid verbatim index.
- [ ] The validator retries once and then returns an invalid verdict.
- [ ] Tests cover a valid mixed request, a fabricated span, a gap, an unknown type, multiple types, and a second failure.
