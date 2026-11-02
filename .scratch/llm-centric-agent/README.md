# LLM-Centric Agent - Tickets

Spec: `spec.md`.

| Ticket | Title | Blocked by | Status |
|---|---|---|---|
| 01 | Reproducible baseline harness | none | done |
| 02 | Local model client and settings | none | done |
| 03 | Configurable guard schema | none | done |
| 04 | Input normalizer | none | done |
| 05 | Guard classifier and typed verdict | 02, 03, 04 | done |
| 06 | Per-verbatim policy and canonical fallback | 05 | done |
| 07 | Guard gate and guard-only vertical slice | 05, 06 | done |
| 08 | Read-only SPARQL tool | none | done |
| 09 | Entity resolver tool | 08 | done |
| 10 | QA contract and prompt | 02, 06 | done |
| 11 | QA factual answer loop | 02, 08, 09, 10 | done |
| 12 | Mixed reply and part validator | 11 | done |
| 13 | Runtime modes and session seam | 07, 12 | done |
| 14 | Eval corrections and policy suite | 07, 13 | done, model gate blocked |
| 15 | Serving launcher and cutover report | 13, 14 | done, model gate blocked |

The deterministic work is complete.
The 47-case guard label check, the T4 serving spike, and the held-out factual set remain blocked on a model host.
