# LLM-Centric Agent — Tickets

Spec: `spec.md`.

| Ticket | Title | Blocked by |
|---|---|---|
| 01 | Reproducible baseline harness | none |
| 02 | Local model client and settings | none |
| 03 | Configurable guard schema | none |
| 04 | Input normalizer | none |
| 05 | Guard classifier and typed verdict | 02, 03, 04 |
| 06 | Per-verbatim policy and canonical fallback | 05 |
| 07 | Guard gate and guard-only vertical slice | 05, 06 |
| 08 | Read-only SPARQL tool | none |
| 09 | Entity resolver tool | 08 |
| 10 | QA contract and prompt | 02, 06 |
| 11 | QA factual answer loop | 02, 08, 09, 10 |
| 12 | Mixed reply and part validator | 11 |
| 13 | Runtime modes and session seam | 07, 12 |
| 14 | Eval corrections and policy suite | 07, 13 |
| 15 | Serving launcher and cutover report | 13, 14 |

Work the frontier: 01, 02, 03, 04, and 08 can start first.
