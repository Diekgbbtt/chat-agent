# t5-partial-titles - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/t5-partial-titles.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/t5-partial-titles.log`
- Log: `docs/design/adversarial/eval/iter0/t5-partial-titles.log`
- Result: 20/51 passed (39.2%). Latency: median 0.00 s, max 0.22 s.
- Fix bar: pass rate >= 0.8, so at least 41/51 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| safe failure (no_entity reply) | 16 | t5-partial-titles-001 | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'? |
| relation refused (no_facts reply) | 6 | t5-partial-titles-006 | Sorry, my knowledge graph has no information about the director of matrix. |
| wrong answer: expected value absent | 6 | t5-partial-titles-035 | The factual answer is: Peter Yates |
| trap value returned ('Lal and Siddique') | 2 | t5-partial-titles-007 | The factual answer is: Lal and Siddique |
| answered instead of clarifying | 1 | t5-partial-titles-045 | The factual answer is: Catherine Hardwicke |

Total failures: 31 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| t5-partial-titles-001 | who directed handmaiden? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-002 | Who wrote the screenplay for handmaiden? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-003 | Who directed 'handmaiden'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-004 | who directed matrix? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-005 | Who wrote the screenplay for matrix? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-016 | who directed terminator? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-017 | Who wrote the screenplay for terminator? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-022 | who directed prestige? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-023 | Who wrote the screenplay for prestige? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-024 | Who directed 'prestige'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-025 | who directed departed? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-026 | Who wrote the screenplay for departed? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-027 | Who directed 'departed'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-028 | who directed pianist? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-029 | Who wrote the screenplay for pianist? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-033 | who directed shawshank redemption? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t5-partial-titles-006 | Who directed 'matrix'? | Sorry, my knowledge graph has no information about the director of matrix. | relation refused (no_facts reply) |
| t5-partial-titles-008 | Who wrote the screenplay for godfather? | Sorry, my knowledge graph has no information about the screenwriter of Godfather. | relation refused (no_facts reply) |
| t5-partial-titles-018 | Who directed 'terminator'? | Sorry, my knowledge graph has no information about the director of Terminator. | relation refused (no_facts reply) |
| t5-partial-titles-030 | Who directed 'pianist'? | Sorry, my knowledge graph has no information about the director of pianist. | relation refused (no_facts reply) |
| t5-partial-titles-031 | who directed dark knight? | Sorry, my knowledge graph has no information about the director of Dark Knight. | relation refused (no_facts reply) |
| t5-partial-titles-032 | Who wrote the screenplay for dark knight? | Sorry, my knowledge graph has no information about the screenwriter of Dark Knight. | relation refused (no_facts reply) |
| t5-partial-titles-035 | who directed usual suspects? | The factual answer is: Peter Yates | wrong answer: expected value absent |
| t5-partial-titles-036 | Who wrote the screenplay for usual suspects? | The factual answer is: Eric Roth | wrong answer: expected value absent |
| t5-partial-titles-037 | who directed silence of the lambs? | The factual answer is: Martin Scorsese | wrong answer: expected value absent |
| t5-partial-titles-038 | Who wrote the screenplay for silence of the lambs? | The factual answer is: Jay Cocks and Martin Scorsese | wrong answer: expected value absent |
| t5-partial-titles-043 | who directed truman show? | The factual answer is: Cesc Gay | wrong answer: expected value absent |
| t5-partial-titles-044 | Who wrote the screenplay for truman show? | The factual answer is: Cesc Gay and Tomàs Aragay o Sastru | wrong answer: expected value absent |
| t5-partial-titles-007 | who directed godfather? | The factual answer is: Lal and Siddique | trap value returned ('Lal and Siddique') |
| t5-partial-titles-009 | Who directed 'godfather'? | The factual answer is: Lal and Siddique | trap value returned ('Lal and Siddique') |
| t5-partial-titles-045 | Who directed twilight zone? | The factual answer is: Catherine Hardwicke | answered instead of clarifying |
