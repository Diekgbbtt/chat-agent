# t3-quote-shapes - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/t3-quote-shapes.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/t3-quote-shapes.log`
- Log: `docs/design/adversarial/eval/iter0/t3-quote-shapes.log`
- Result: 37/57 passed (64.9%). Latency: median 0.00 s, max 0.19 s.
- Fix bar: pass rate >= 0.8, so at least 46/57 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| safe failure (no_entity reply) | 12 | t3-quote-shapes-001 | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'? |
| relation refused (no_facts reply) | 5 | t3-quote-shapes-021 | Sorry, my knowledge graph has no information about the director of matrix. |
| trap value returned ('Lal and Siddique') | 2 | t3-quote-shapes-009 | The factual answer is: Lal and Siddique |
| wrong answer: expected value absent | 1 | t3-quote-shapes-039 | The factual answer is: Tim Burton |

Total failures: 20 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| t3-quote-shapes-001 | Who directed ''Inception''? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-011 | Who wrote the screenplay for 'Interstellar.'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-015 | Who wrote the screenplay for ''Interstellar''? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-016 | Who wrote the screenplay for ''The Handmaiden''? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-026 | Who directed 'Jaws.'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-029 | Who directed 'Jaws? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-030 | Who directed ''Titanic''? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-040 | Who directed 'Parasite.'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-044 | Who directed ''Parasite''? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-045 | Who composed the music for ''Whiplash''? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-053 | Who directed 'The Departed.'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-054 | Who directed 'The Departed?'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t3-quote-shapes-021 | Who directed 'The Matrix? | Sorry, my knowledge graph has no information about the director of matrix. | relation refused (no_facts reply) |
| t3-quote-shapes-024 | Who directed 'The Matrix.'? | Sorry, my knowledge graph has no information about the director of matrix. | relation refused (no_facts reply) |
| t3-quote-shapes-025 | Who directed 'The Matrix?'? | Sorry, my knowledge graph has no information about the director of matrix. | relation refused (no_facts reply) |
| t3-quote-shapes-055 | Who directed 'The Pianist.'? | Sorry, my knowledge graph has no information about the director of pianist. | relation refused (no_facts reply) |
| t3-quote-shapes-056 | Who directed 'The Pianist? | Sorry, my knowledge graph has no information about the director of pianist. | relation refused (no_facts reply) |
| t3-quote-shapes-009 | Who directed 'The Godfather? | The factual answer is: Lal and Siddique | trap value returned ('Lal and Siddique') |
| t3-quote-shapes-010 | Who directed 'The Godfather?'? | The factual answer is: Lal and Siddique | trap value returned ('Lal and Siddique') |
| t3-quote-shapes-039 | Who directed 'Batman Begins?'? | The factual answer is: Tim Burton | wrong answer: expected value absent |
