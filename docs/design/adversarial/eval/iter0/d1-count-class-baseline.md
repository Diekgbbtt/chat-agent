# d1-count-class - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/d1-count-class.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/d1-count-class.log`
- Log: `docs/design/adversarial/eval/iter0/d1-count-class.log`
- Result: 6/63 passed (9.5%). Latency: median 0.00 s, max 0.01 s.
- Fix bar: pass rate >= 0.8, so at least 51/63 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| wrong count: 0 | 57 | d1-count-class-001 | The factual answer is: 0 |

Total failures: 57 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| d1-count-class-001 | How many awards did 'Inception' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-002 | How many cast members does 'Inception' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-003 | How many genres does 'Inception' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-004 | How many countries of origin does 'Inception' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-005 | How many awards did 'The Godfather' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-006 | How many cast members does 'The Godfather' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-007 | How many genres does 'The Godfather' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-008 | How many countries of origin does 'The Godfather' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-009 | How many awards did 'Interstellar' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-010 | How many cast members does 'Interstellar' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-011 | How many genres does 'Interstellar' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-012 | How many countries of origin does 'Interstellar' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-013 | How many awards did 'Titanic' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-014 | How many cast members does 'Titanic' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-015 | How many genres does 'Titanic' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-016 | How many countries of origin does 'Titanic' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-017 | How many awards did 'Jaws' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-018 | How many cast members does 'Jaws' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-019 | How many genres does 'Jaws' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-020 | How many countries of origin does 'Jaws' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-021 | How many awards did 'The Matrix' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-022 | How many cast members does 'The Matrix' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-023 | How many genres does 'The Matrix' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-024 | How many countries of origin does 'The Matrix' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-025 | How many awards did 'The Dark Knight' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-026 | How many cast members does 'The Dark Knight' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-027 | How many genres does 'The Dark Knight' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-028 | How many countries of origin does 'The Dark Knight' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-029 | How many awards did 'Parasite' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-030 | How many cast members does 'Parasite' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-031 | How many genres does 'Parasite' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-032 | How many countries of origin does 'Parasite' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-033 | How many awards did 'The Handmaiden' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-034 | How many cast members does 'The Handmaiden' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-035 | How many genres does 'The Handmaiden' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-036 | How many countries of origin does 'The Handmaiden' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-037 | How many awards did 'Whiplash' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-038 | How many cast members does 'Whiplash' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-039 | How many genres does 'Whiplash' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-040 | How many countries of origin does 'Whiplash' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-041 | How many awards did 'Schindler's List' win? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-042 | How many cast members does 'Schindler's List' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-043 | How many genres does 'Schindler's List' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-044 | How many countries of origin does 'Schindler's List' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-045 | How many cast members does 'The Prestige' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-046 | How many genres does 'The Prestige' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-047 | How many countries of origin does 'The Prestige' have? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-048 | How many awards has Christopher Nolan won? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-049 | How many awards did Christopher Nolan receive? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-050 | How many awards has Steven Spielberg won? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-051 | How many awards did Steven Spielberg receive? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-052 | How many awards has Meryl Streep won? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-053 | How many awards did Meryl Streep receive? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-054 | How many awards has Alfred Hitchcock won? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-055 | How many awards did Alfred Hitchcock receive? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-056 | How many awards has Martin Scorsese won? | The factual answer is: 0 | wrong count: 0 |
| d1-count-class-057 | How many awards did Martin Scorsese receive? | The factual answer is: 0 | wrong count: 0 |
