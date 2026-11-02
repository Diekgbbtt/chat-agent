# 15 - Serving launcher and cutover report

**What to build:** A local launcher starts one vLLM process for the shared model, waits for health, and prints the exact command.
The submission build copies the serving requirements and the launcher.
The report records what was implemented, what was measured, and what remains blocked.

**Blocked by:** 13, 14.

**Status:** done - model gate remains blocked

- [ ] The launcher starts one process with configurable model name and port.
- [ ] The launcher exposes a health-only check.
- [ ] The launcher exits non-zero when a configured endpoint is unhealthy.
- [ ] The submission build copies the serving requirements next to the runtime requirements.
- [ ] The submission build asserts that the launcher exists.
- [ ] The report lists the implemented modules, tests, and commands.
- [ ] The report separates measured results from unmeasured model gates.
- [ ] The report records the open safety review and the missing held-out set.
