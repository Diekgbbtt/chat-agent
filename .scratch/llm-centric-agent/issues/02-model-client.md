# 02 — Local model client and settings

**What to build:** The runtime can talk to two local OpenAI-compatible chat endpoints through one thin client.
The client normalises content, tool calls, finish reason, and usage.
A health probe reports both endpoints at startup.
Legacy settings and behaviour keep working.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Settings expose guard and QA base URLs, model names, API keys, mode, budgets, and the guard schema path.
- [ ] The client wraps the OpenAI SDK and returns a typed response object.
- [ ] Tool-call arguments are parsed into a typed call, and malformed arguments are reported as a typed error.
- [ ] The client has a timeout and one retry.
- [ ] A health probe checks both endpoints and returns per-endpoint status.
- [ ] The legacy default mode still constructs the old agent without any network call.
- [ ] Tests use a fake transport and do not need a model server.
