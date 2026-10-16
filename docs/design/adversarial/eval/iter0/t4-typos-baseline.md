# t4-typos - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/t4-typos.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/t4-typos.log`
- Log: `docs/design/adversarial/eval/iter0/t4-typos.log`
- Result: 39/60 passed (65.0%). Latency: median 0.06 s, max 0.20 s.
- Fix bar: pass rate >= 0.8, so at least 48/60 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| safe failure (no_entity reply) | 16 | t4-typos-003 | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'? |
| trap value returned ('Lal') | 2 | t4-typos-001 | The factual answer is: Lal and Siddique |
| wrong answer: expected value absent | 2 | t4-typos-033 | The factual answer is: Tim Burton |
| relation refused (no_facts reply) | 1 | t4-typos-004 | Sorry, my knowledge graph has no information about the screenwriter of Godfather. |

Total failures: 21 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| t4-typos-003 | Who directed 'godfathre'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-005 | Who directed terminater? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-006 | Who directed terminatr? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-007 | Who directed 'termonator'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-008 | Who wrote the screenplay for terminatoor? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-009 | Who directed jazws? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-010 | Who directed jawss? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-011 | Who directed 'jaws!'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-012 | Who wrote the screenplay for jwaws? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-015 | Who directed 'interstellr'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-019 | Who directed 'incepsion'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-023 | Who directed 'schindler's lsit'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-027 | Who directed 'forresst gump'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-031 | Who directed 'the matrx'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-039 | Who directed 'the prestrige'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-046 | Who directed 'the deparred'? | I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who … | safe failure (no_entity reply) |
| t4-typos-001 | Who directed godfahter? | The factual answer is: Lal and Siddique | trap value returned ('Lal') |
| t4-typos-002 | Who directed godfatherr? | The factual answer is: Lal and Siddique | trap value returned ('Lal') |
| t4-typos-033 | Who directed batman begns? | The factual answer is: Tim Burton | wrong answer: expected value absent |
| t4-typos-035 | Who directed 'batman bigins'? | The factual answer is: Tim Burton | wrong answer: expected value absent |
| t4-typos-004 | Who wrote the screenplay for godfther? | Sorry, my knowledge graph has no information about the screenwriter of Godfather. | relation refused (no_facts reply) |
