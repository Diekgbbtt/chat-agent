# 10 - QA contract and prompt

**What to build:** The QA model receives one system prompt with role, grounding, classification format, relationships, reply contract, tools, policy, schema card, and stop rules.
The user prompt carries the overview, the action, and the verbatim plan.
Unsafe text and its rationale are absent.
`submit_response` accepts one part per verbatim with the typed fields.

**Blocked by:** 02, 06.

**Status:** done

- [ ] The system prompt carries all nine sections.
- [ ] The QA loop blocks a repeated tool call and forces `submit_response` on the final step.
- [ ] The schema card carries prefixes, core classes, core properties, value shapes, and eight to twelve query examples.
- [ ] The reply contract names all six part kinds.
- [ ] The user prompt carries the overview, action, plan, and relationship fields.
- [ ] A redacted verbatim contributes no text and no rationale to the prompt.
- [ ] `submit_response` accepts `verbatim_index`, `kind`, `text`, `evidence_row_ids`, and `addressed_safety_types`.
- [ ] The tool list is exactly the two graph tools plus `submit_response` when tools are enabled, and only `submit_response` otherwise.
- [ ] Prompt length stays within the configured budget.
- [ ] Tests cover the prompt sections, relationship fields, redaction, and distinct fallback observations.
