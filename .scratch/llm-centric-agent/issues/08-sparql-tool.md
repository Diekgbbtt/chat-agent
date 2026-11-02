# 08 - Read-only SPARQL tool

**What to build:** The QA model can run a read-only SPARQL query and receive labelled rows with stable row IDs.
The query guard rejects writes and network clauses in agent and raw modes.
The result formatter resolves entity and property labels, formats values, assigns row IDs, and caps the observation.

**Blocked by:** None - can start immediately.

**Status:** done

- [ ] Agent mode accepts SELECT and ASK.
- [ ] Raw mode also accepts CONSTRUCT and DESCRIBE.
- [ ] Both modes reject updates, `SERVICE`, `FROM`, and the other banned clauses.
- [ ] Banned words inside string literals and comments do not trigger a rejection.
- [ ] The query length is capped.
- [ ] The formatter resolves entity labels and property labels.
- [ ] The formatter formats literals, dates, numbers, and unbound values.
- [ ] Every row receives a stable row ID.
- [ ] Truncation and query errors become typed observations.
- [ ] The raw SPARQL eval stays at 9 of 9.
