# 03 — Configurable guard schema

**What to build:** The guard prompt and fallback text are generated from one validated data file.
The file carries two scopes, six safety types, severity, tone, legacy labels, fallback text, limits, and one example for every scope and safety pair.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The loader rejects duplicate or missing scope values.
- [ ] The loader rejects duplicate, missing, or unknown safety types.
- [ ] The loader rejects an incomplete severity order.
- [ ] The loader rejects a safety type without severity, tone, legacy label, or fallback text.
- [ ] The loader rejects a legacy label outside the five known values.
- [ ] The loader rejects an incomplete 14-pair example set.
- [ ] The loader rejects an allow label.
- [ ] The shipped file has 14 pair examples.
- [ ] Tests cover every rejection and the shipped file.
