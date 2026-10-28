# 15 — Serving launcher and cutover report

**What to build:** A local launcher starts both vLLM processes, waits for health, and prints the exact commands.
The submission build copies the serving requirements and the launcher.
The report records what was implemented, what was measured, and what remains blocked.

**Blocked by:** 13, 14.

**Status:** ready-for-agent

- [ ] The launcher starts two processes with configurable model names and ports.
- [ ] The launcher exposes a health-only check.
- [ ] The launcher exits non-zero when either endpoint is unhealthy.
- [ ] The submission build copies the serving requirements next to the runtime requirements.
- [ ] The submission build asserts that the launcher exists.
- [ ] The report lists the implemented modules, tests, and commands.
- [ ] The report separates measured results from unmeasured model gates.
- [ ] The report records the open safety review and the missing held-out set.
