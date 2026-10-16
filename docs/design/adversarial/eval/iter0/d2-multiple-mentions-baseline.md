# d2-multiple-mentions - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/d2-multiple-mentions.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/d2-multiple-mentions.log`
- Log: `docs/design/adversarial/eval/iter0/d2-multiple-mentions.log`
- Result: 10/65 passed (15.4%). Latency: median 0.00 s, max 0.00 s.
- Fix bar: pass rate >= 0.8, so at least 52/65 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| answered instead of clarifying | 55 | d2-multiple-mentions-001 | The factual answer is: Steven Spielberg |

Total failures: 55 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| d2-multiple-mentions-001 | I love 'Jaws'. Who directed 'Inception'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-002 | Who directed 'Jaws'? Who directed 'Inception'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-004 | Someone told me Jaws is great. Who directed Inception? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-005 | Who wrote 'Jaws'? Also, who directed 'Inception'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-006 | I love 'The Godfather'. Who directed 'Inception'? | The factual answer is: Francis Ford Coppola | answered instead of clarifying |
| d2-multiple-mentions-007 | Who directed 'The Godfather'? Who directed 'Inception'? | The factual answer is: Francis Ford Coppola | answered instead of clarifying |
| d2-multiple-mentions-009 | Someone told me The Godfather is great. Who directed Inception? | The factual answer is: Francis Ford Coppola | answered instead of clarifying |
| d2-multiple-mentions-010 | Who wrote 'The Godfather'? Also, who directed 'Inception'? | The factual answer is: Francis Ford Coppola | answered instead of clarifying |
| d2-multiple-mentions-011 | I love 'Jaws'. Who directed 'Interstellar'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-012 | Who directed 'Jaws'? Who directed 'Interstellar'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-014 | Someone told me Jaws is great. Who directed Interstellar? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-015 | Who wrote 'Jaws'? Also, who directed 'Interstellar'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| d2-multiple-mentions-016 | I love 'The Matrix'. Who directed 'The Godfather'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | answered instead of clarifying |
| d2-multiple-mentions-017 | Who directed 'The Matrix'? Who directed 'The Godfather'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | answered instead of clarifying |
| d2-multiple-mentions-019 | Someone told me The Matrix is great. Who directed The Godfather? | The factual answer is: Lana Wachowski and Lelly Wechawsku | answered instead of clarifying |
| d2-multiple-mentions-020 | Who wrote 'The Matrix'? Also, who directed 'The Godfather'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | answered instead of clarifying |
| d2-multiple-mentions-021 | I love 'Up'. Who directed 'Jaws'? | The factual answer is: Bob Peterson and Pete Docter | answered instead of clarifying |
| d2-multiple-mentions-022 | Who directed 'Up'? Who directed 'Jaws'? | The factual answer is: Bob Peterson and Pete Docter | answered instead of clarifying |
| d2-multiple-mentions-024 | Someone told me Up is great. Who directed Jaws? | The factual answer is: Bob Peterson and Pete Docter | answered instead of clarifying |
| d2-multiple-mentions-025 | Who wrote 'Up'? Also, who directed 'Jaws'? | The factual answer is: Bob Peterson and Pete Docter | answered instead of clarifying |
| d2-multiple-mentions-026 | I love 'Titanic'. Who directed 'The Matrix'? | The factual answer is: Jean Negulesco | answered instead of clarifying |
| d2-multiple-mentions-027 | Who directed 'Titanic'? Who directed 'The Matrix'? | The factual answer is: Jean Negulesco | answered instead of clarifying |
| d2-multiple-mentions-028 | I love Titanic. Who directed The Matrix? | The factual answer is: Lana Wachowski and Lelly Wechawsku | answered instead of clarifying |
| d2-multiple-mentions-029 | Someone told me Titanic is great. Who directed The Matrix? | The factual answer is: Lana Wachowski and Lelly Wechawsku | answered instead of clarifying |
| d2-multiple-mentions-030 | Who wrote 'Titanic'? Also, who directed 'The Matrix'? | The factual answer is: Jean Negulesco | answered instead of clarifying |
| d2-multiple-mentions-031 | I love 'Interstellar'. Who directed 'Batman Begins'? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-032 | Who directed 'Interstellar'? Who directed 'Batman Begins'? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-033 | I love Interstellar. Who directed Batman Begins? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-034 | Someone told me Interstellar is great. Who directed Batman Begins? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-035 | Who wrote 'Interstellar'? Also, who directed 'Batman Begins'? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-036 | I love 'The Handmaiden'. Who directed 'Parasite'? | The factual answer is: Park Chan-wook | answered instead of clarifying |
| d2-multiple-mentions-037 | Who directed 'The Handmaiden'? Who directed 'Parasite'? | The factual answer is: Park Chan-wook | answered instead of clarifying |
| d2-multiple-mentions-039 | Someone told me The Handmaiden is great. Who directed Parasite? | The factual answer is: Park Chan-wook | answered instead of clarifying |
| d2-multiple-mentions-040 | Who wrote 'The Handmaiden'? Also, who directed 'Parasite'? | The factual answer is: Park Chan-wook | answered instead of clarifying |
| d2-multiple-mentions-041 | I love 'Whiplash'. Who directed 'The Departed'? | The factual answer is: Damien Chazelle | answered instead of clarifying |
| d2-multiple-mentions-042 | Who directed 'Whiplash'? Who directed 'The Departed'? | The factual answer is: Damien Chazelle | answered instead of clarifying |
| d2-multiple-mentions-043 | I love Whiplash. Who directed The Departed? | The factual answer is: Martin Scorsese | answered instead of clarifying |
| d2-multiple-mentions-044 | Someone told me Whiplash is great. Who directed The Departed? | The factual answer is: Martin Scorsese | answered instead of clarifying |
| d2-multiple-mentions-045 | Who wrote 'Whiplash'? Also, who directed 'The Departed'? | The factual answer is: Damien Chazelle | answered instead of clarifying |
| d2-multiple-mentions-046 | I love 'The Pianist'. Who directed 'Schindler's List'? | The factual answer is: Roman Polanski | answered instead of clarifying |
| d2-multiple-mentions-047 | Who directed 'The Pianist'? Who directed 'Schindler's List'? | The factual answer is: Roman Polanski | answered instead of clarifying |
| d2-multiple-mentions-049 | Someone told me The Pianist is great. Who directed Schindler's List? | The factual answer is: Roman Polanski | answered instead of clarifying |
| d2-multiple-mentions-050 | Who wrote 'The Pianist'? Also, who directed 'Schindler's List'? | The factual answer is: Roman Polanski | answered instead of clarifying |
| d2-multiple-mentions-051 | I love 'Forrest Gump'. Who directed 'The Prestige'? | The factual answer is: Robert Zemeckis | answered instead of clarifying |
| d2-multiple-mentions-052 | Who directed 'Forrest Gump'? Who directed 'The Prestige'? | The factual answer is: Robert Zemeckis | answered instead of clarifying |
| d2-multiple-mentions-054 | Someone told me Forrest Gump is great. Who directed The Prestige? | The factual answer is: Robert Zemeckis | answered instead of clarifying |
| d2-multiple-mentions-055 | Who wrote 'Forrest Gump'? Also, who directed 'The Prestige'? | The factual answer is: Robert Zemeckis | answered instead of clarifying |
| d2-multiple-mentions-056 | I love 'The Terminator'. Who directed 'Jaws'? | The factual answer is: James Cameron | answered instead of clarifying |
| d2-multiple-mentions-057 | Who directed 'The Terminator'? Who directed 'Jaws'? | The factual answer is: James Cameron | answered instead of clarifying |
| d2-multiple-mentions-059 | Someone told me The Terminator is great. Who directed Jaws? | The factual answer is: James Cameron | answered instead of clarifying |
| d2-multiple-mentions-060 | Who wrote 'The Terminator'? Also, who directed 'Jaws'? | The factual answer is: James Cameron | answered instead of clarifying |
| d2-multiple-mentions-061 | I love 'Oppenheimer'. Who directed 'Titanic'? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-062 | Who directed 'Oppenheimer'? Who directed 'Titanic'? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-064 | Someone told me Oppenheimer is great. Who directed Titanic? | The factual answer is: Christopher Nolan | answered instead of clarifying |
| d2-multiple-mentions-065 | Who wrote 'Oppenheimer'? Also, who directed 'Titanic'? | The factual answer is: Christopher Nolan | answered instead of clarifying |
