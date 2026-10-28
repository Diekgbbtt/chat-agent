# 01 — Reproducible baseline harness

**What to build:** A developer can save one JSON result per eval case and print a scoreboard with pass counts, failures, per-label recall, and latency.
The existing stdout and exit-code contract stays unchanged.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `agent.eval` accepts `--json PATH` and writes one result object per case.
- [ ] The result object carries id, pass, expected labels, got labels, reply, latency, and error.
- [ ] The human-readable output and exit code are unchanged when `--json` is absent.
- [ ] A scoreboard script reads the JSONL results and prints counts, failures, per-label recall, and latency.
- [ ] Unit and eval tests cover the new output contract.
- [ ] The legacy suite stays green.
