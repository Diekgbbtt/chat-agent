# 10 — QA contract and prompt

**What to build:** The QA model receives one system prompt with role, grounding, classification format, reply contract, tools, policy, schema card, and stop rules.
The user prompt carries the overview, the action, the verbatim plan, and the ambiguities.
Unsafe text and its rationale are absent.
`submit_response` accepts one part per verbatim with the typed fields.

**Blocked by:** 02, 06.

**Status:** ready-for-agent

- [ ] The system prompt carries all eight sections.
- [ ] The schema card carries prefixes, core classes, core properties, value shapes, and eight to twelve query examples.
- [ ] The reply contract names all six part kinds.
- [ ] The user prompt carries the overview, action, plan, and ambiguities.
- [ ] A redacted verbatim contributes no text and no rationale to the prompt.
- [ ] `submit_response` accepts `verbatim_index`, `kind`, `text`, `evidence_row_ids`, `addressed_safety_types`, and `assumption`.
- [ ] The tool list is exactly the two graph tools plus `submit_response` when tools are enabled, and only `submit_response` otherwise.
- [ ] Prompt length stays within the configured budget.
- [ ] Tests cover the prompt sections and redaction.
