# 05 - Guard discrimination, classification, and typed verdict

**What to build:** The guard uses two chained forced calls.
`submit_discrimination` returns the overview, exact spans, ambiguity flags, and relationships.
`submit_classification` returns one label and rationale per span.
The runtime validates both stages.
A structural failure retries the failing stage once.
A second failure becomes an invalid verdict that the policy maps to clarification.

**Blocked by:** 02, 03, 04.

**Status:** done

- [ ] The discriminator prompt carries the smallest-complete-verbatim rule and the two canonical relationship examples.
- [ ] The discriminator forces `submit_discrimination` and caps output tokens.
- [ ] The classifier prompt carries all 8 pair examples and the prompt-injection scope rule.
- [ ] The classifier forces `submit_classification` and caps output tokens.
- [ ] The parsed discrimination has an overview and ordered spans.
- [ ] Each span carries `ambiguous` and an optional relationship.
- [ ] A resolved relationship carries an explicit entity inside its target.
- [ ] A resolved relationship carries a target index and an entity inside the target.
- [ ] A missing target uses `missing semantic target`.
- [ ] The discriminator validator checks exact spans, non-overlap, input order, and alphanumeric coverage.
- [ ] Separator whitespace, words, and punctuation are allowed between spans.
- [ ] The discriminator validator rejects target range, self-target, and cycle errors.
- [ ] The classifier validator checks one label per span, index order, known scopes, known safety types, and the safe/unsafe invariant.
- [ ] The tool schema enforces the exact label count with `minItems` and `maxItems`.
- [ ] Each stage retries once and then returns an invalid verdict.
- [ ] Tests cover valid mixed requests, fabricated spans, gaps, unknown types, multiple types, relationships, and stage retries.
