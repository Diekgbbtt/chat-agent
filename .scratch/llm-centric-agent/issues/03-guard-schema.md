# 03 - Configurable guard schema

**What to build:** The guard prompt and fallback text are generated from one validated data file.
The file carries two scopes, three parent safety types (`harmful`, `toxic`, `prompt_injection`), descriptions, fallback text, limits, and one example for every scope and safety pair.

**Blocked by:** None - can start immediately.

**Status:** done

- [ ] The loader rejects duplicate or missing scope values.
- [ ] The loader rejects duplicate, missing, or unknown safety types.
- [ ] The loader rejects safety types in any order other than `harmful`, `toxic`, `prompt_injection`.
- [ ] The loader rejects a safety type without a description or fallback text.
- [ ] The loader rejects a schema with severity, tone, or legacy label fields.
- [ ] The loader rejects an incomplete 8-pair example set.
- [ ] The loader rejects a duplicate example pair.
- [ ] The loader rejects an allow label.
- [ ] The shipped file has 8 pair examples.
- [ ] Tests cover every rejection and the shipped file.
