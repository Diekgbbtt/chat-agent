# 13 - Runtime modes and session seam

**What to build:** `AGENT_MODE=legacy|llm` selects the runtime path on one `Agent.answer` seam.
The session records only safe in-scope visible text and keeps history disabled.
`llm` is the target path.
The legacy path stays the default and is untouched.

**Blocked by:** 12.

**Status:** done

- [ ] The default mode is legacy.
- [ ] Legacy mode constructs the old handler stack and makes no model call.
- [ ] LLM mode uses the guard, policy, and QA agent.
- [ ] An unknown mode fails at startup with a clear error.
- [ ] Raw SPARQL keeps its bypass in every mode.
- [ ] The session stores only safe in-scope verbatims.
- [ ] The session stores no unsafe or out-of-scope text.
- [ ] History stays disabled.
- [ ] The trace names the mode, classification, plan, policy, tools, evidence, parts, and fallback.
- [ ] Tests cover mode selection, session sanitisation, and trace steps.
