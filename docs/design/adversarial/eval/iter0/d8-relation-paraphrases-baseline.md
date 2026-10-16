# d8-relation-paraphrases - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/d8-relation-paraphrases.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/d8-relation-paraphrases.log`
- Log: `docs/design/adversarial/eval/iter0/d8-relation-paraphrases.log`
- Result: 10/70 passed (14.3%). Latency: median 0.00 s, max 0.00 s.
- Fix bar: pass rate >= 0.8, so at least 56/70 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| relation word ignored (no_relation reply) | 60 | d8-relation-paraphrases-001 | I found Inception, but I'm not sure what you'd like to know. You can ask about its director, cast, genre, ... |

Total failures: 60 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| d8-relation-paraphrases-001 | Who did the directing for 'Inception'? | I found Inception, but I'm not sure what you'd like to know. You can ask about its direct… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-002 | Who was at the helm of 'Inception'? | I found Inception, but I'm not sure what you'd like to know. You can ask about its direct… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-003 | Who is behind the camera on 'Inception'? | I found Inception, but I'm not sure what you'd like to know. You can ask about its direct… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-004 | Who did the writing for 'Inception'? | I found Inception, but I'm not sure what you'd like to know. You can ask about its direct… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-005 | Who did the composing for 'Inception'? | I found Inception, but I'm not sure what you'd like to know. You can ask about its direct… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-006 | Who did the directing for 'Interstellar'? | I found Interstellar, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-007 | Who was at the helm of 'Interstellar'? | I found Interstellar, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-008 | Who is behind the camera on 'Interstellar'? | I found Interstellar, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-009 | Who did the writing for 'Interstellar'? | I found Interstellar, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-010 | Who did the composing for 'Interstellar'? | I found Interstellar, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-011 | Who did the directing for 'The Godfather'? | I found The Godfather, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-012 | Who was at the helm of 'The Godfather'? | I found The Godfather, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-013 | Who is behind the camera on 'The Godfather'? | I found The Godfather, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-014 | Who did the writing for 'The Godfather'? | I found The Godfather, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-015 | Who did the composing for 'The Godfather'? | I found The Godfather, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-016 | Who did the directing for 'The Godfather Part II'? | I found The Godfather Part II, but I'm not sure what you'd like to know. You can ask abou… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-017 | Who was at the helm of 'The Godfather Part II'? | I found The Godfather Part II, but I'm not sure what you'd like to know. You can ask abou… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-018 | Who is behind the camera on 'The Godfather Part II'? | I found The Godfather Part II, but I'm not sure what you'd like to know. You can ask abou… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-019 | Who did the writing for 'The Godfather Part II'? | I found The Godfather Part II, but I'm not sure what you'd like to know. You can ask abou… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-020 | Who did the composing for 'The Godfather Part II'? | I found The Godfather Part II, but I'm not sure what you'd like to know. You can ask abou… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-021 | Who did the directing for 'The Matrix'? | I found The Matrix, but I'm not sure what you'd like to know. You can ask about its direc… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-022 | Who was at the helm of 'The Matrix'? | I found The Matrix, but I'm not sure what you'd like to know. You can ask about its direc… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-023 | Who is behind the camera on 'The Matrix'? | I found The Matrix, but I'm not sure what you'd like to know. You can ask about its direc… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-024 | Who did the writing for 'The Matrix'? | I found The Matrix, but I'm not sure what you'd like to know. You can ask about its direc… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-025 | Who did the composing for 'The Matrix'? | I found The Matrix, but I'm not sure what you'd like to know. You can ask about its direc… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-026 | Who did the directing for 'The Matrix Reloaded'? | I found The Matrix Reloaded, but I'm not sure what you'd like to know. You can ask about … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-027 | Who was at the helm of 'The Matrix Reloaded'? | I found The Matrix Reloaded, but I'm not sure what you'd like to know. You can ask about … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-028 | Who is behind the camera on 'The Matrix Reloaded'? | I found The Matrix Reloaded, but I'm not sure what you'd like to know. You can ask about … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-029 | Who did the writing for 'The Matrix Reloaded'? | I found The Matrix Reloaded, but I'm not sure what you'd like to know. You can ask about … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-030 | Who did the composing for 'The Matrix Reloaded'? | I found The Matrix Reloaded, but I'm not sure what you'd like to know. You can ask about … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-031 | Who did the directing for 'Jaws'? | I found Jaws, but I'm not sure what you'd like to know. You can ask about its director, c… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-032 | Who was at the helm of 'Jaws'? | I found Jaws, but I'm not sure what you'd like to know. You can ask about its director, c… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-033 | Who is behind the camera on 'Jaws'? | I found Jaws, but I'm not sure what you'd like to know. You can ask about its director, c… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-034 | Who did the writing for 'Jaws'? | I found Jaws, but I'm not sure what you'd like to know. You can ask about its director, c… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-035 | Who did the composing for 'Jaws'? | I found Jaws, but I'm not sure what you'd like to know. You can ask about its director, c… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-036 | Who did the directing for 'The Handmaiden'? | I found The Handmaiden, but I'm not sure what you'd like to know. You can ask about its d… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-037 | Who was at the helm of 'The Handmaiden'? | I found The Handmaiden, but I'm not sure what you'd like to know. You can ask about its d… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-038 | Who is behind the camera on 'The Handmaiden'? | I found The Handmaiden, but I'm not sure what you'd like to know. You can ask about its d… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-039 | Who did the writing for 'The Handmaiden'? | I found The Handmaiden, but I'm not sure what you'd like to know. You can ask about its d… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-040 | Who did the composing for 'The Handmaiden'? | I found The Handmaiden, but I'm not sure what you'd like to know. You can ask about its d… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-041 | Who did the directing for 'Titanic'? | I found Titanic, but I'm not sure what you'd like to know. You can ask about its director… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-042 | Who was at the helm of 'Titanic'? | I found Titanic, but I'm not sure what you'd like to know. You can ask about its director… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-043 | Who is behind the camera on 'Titanic'? | I found Titanic, but I'm not sure what you'd like to know. You can ask about its director… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-044 | Who did the writing for 'Titanic'? | I found Titanic, but I'm not sure what you'd like to know. You can ask about its director… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-045 | Who did the composing for 'Titanic'? | I found Titanic, but I'm not sure what you'd like to know. You can ask about its director… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-046 | Who did the directing for 'Batman Begins'? | I found Batman Begins, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-047 | Who was at the helm of 'Batman Begins'? | I found Batman Begins, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-048 | Who is behind the camera on 'Batman Begins'? | I found Batman Begins, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-049 | Who did the writing for 'Batman Begins'? | I found Batman Begins, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-050 | Who did the composing for 'Batman Begins'? | I found Batman Begins, but I'm not sure what you'd like to know. You can ask about its di… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-051 | Who did the directing for 'The Dark Knight'? | I found The Dark Knight, but I'm not sure what you'd like to know. You can ask about its … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-052 | Who was at the helm of 'The Dark Knight'? | I found The Dark Knight, but I'm not sure what you'd like to know. You can ask about its … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-053 | Who is behind the camera on 'The Dark Knight'? | I found The Dark Knight, but I'm not sure what you'd like to know. You can ask about its … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-054 | Who did the writing for 'The Dark Knight'? | I found The Dark Knight, but I'm not sure what you'd like to know. You can ask about its … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-055 | Who did the composing for 'The Dark Knight'? | I found The Dark Knight, but I'm not sure what you'd like to know. You can ask about its … | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-056 | Who did the directing for 'The Prestige'? | I found The Prestige, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-057 | Who was at the helm of 'The Prestige'? | I found The Prestige, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-058 | Who is behind the camera on 'The Prestige'? | I found The Prestige, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-059 | Who did the writing for 'The Prestige'? | I found The Prestige, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
| d8-relation-paraphrases-060 | Who did the composing for 'The Prestige'? | I found The Prestige, but I'm not sure what you'd like to know. You can ask about its dir… | relation word ignored (no_relation reply) |
