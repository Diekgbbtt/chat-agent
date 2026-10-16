# d3-trailing-superlative - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/d3-trailing-superlative.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/d3-trailing-superlative.log`
- Log: `docs/design/adversarial/eval/iter0/d3-trailing-superlative.log`
- Result: 18/55 passed (32.7%). Latency: median 0.00 s, max 0.00 s.
- Fix bar: pass rate >= 0.8, so at least 44/55 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| relation refused (no_facts reply) | 37 | d3-trailing-superlative-001 | Sorry, my knowledge graph has no information about the director of Batman Begins. |

Total failures: 37 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| d3-trailing-superlative-001 | Who directed 'Batman Begins', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of Batman Begins. | relation refused (no_facts reply) |
| d3-trailing-superlative-002 | Who directed 'Batman Begins', the latest film I watched? | Sorry, my knowledge graph has no information about the director of Batman Begins. | relation refused (no_facts reply) |
| d3-trailing-superlative-003 | Who directed 'Batman Begins', the last movie I saw? | Sorry, my knowledge graph has no information about the director of Batman Begins. | relation refused (no_facts reply) |
| d3-trailing-superlative-004 | Who directed 'Batman Begins', the newest one I own? | Sorry, my knowledge graph has no information about the director of Batman Begins. | relation refused (no_facts reply) |
| d3-trailing-superlative-006 | Who wrote the screenplay of 'The Godfather', the first film in the trilogy? | Sorry, my knowledge graph has no information about the screenwriter of The Godfather. | relation refused (no_facts reply) |
| d3-trailing-superlative-007 | Who wrote the screenplay of 'The Godfather', the latest film I watched? | Sorry, my knowledge graph has no information about the screenwriter of The Godfather. | relation refused (no_facts reply) |
| d3-trailing-superlative-008 | Who wrote the screenplay of 'The Godfather', the last movie I saw? | Sorry, my knowledge graph has no information about the screenwriter of The Godfather. | relation refused (no_facts reply) |
| d3-trailing-superlative-009 | Who wrote the screenplay of 'The Godfather', the newest one I own? | Sorry, my knowledge graph has no information about the screenwriter of The Godfather. | relation refused (no_facts reply) |
| d3-trailing-superlative-011 | Who composed the music for 'Inception', the first film in the trilogy? | Sorry, my knowledge graph has no information about the composer of Inception. | relation refused (no_facts reply) |
| d3-trailing-superlative-012 | Who composed the music for 'Inception', the latest film I watched? | Sorry, my knowledge graph has no information about the composer of Inception. | relation refused (no_facts reply) |
| d3-trailing-superlative-013 | Who composed the music for 'Inception', the last movie I saw? | Sorry, my knowledge graph has no information about the composer of Inception. | relation refused (no_facts reply) |
| d3-trailing-superlative-014 | Who composed the music for 'Inception', the newest one I own? | Sorry, my knowledge graph has no information about the composer of Inception. | relation refused (no_facts reply) |
| d3-trailing-superlative-016 | Who directed 'Interstellar', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of Interstellar. | relation refused (no_facts reply) |
| d3-trailing-superlative-017 | Who directed 'Interstellar', the latest film I watched? | Sorry, my knowledge graph has no information about the director of Interstellar. | relation refused (no_facts reply) |
| d3-trailing-superlative-018 | Who directed 'Interstellar', the last movie I saw? | Sorry, my knowledge graph has no information about the director of Interstellar. | relation refused (no_facts reply) |
| d3-trailing-superlative-020 | Who directed 'The Matrix', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of The Matrix. | relation refused (no_facts reply) |
| d3-trailing-superlative-021 | Who directed 'The Matrix', the latest film I watched? | Sorry, my knowledge graph has no information about the director of The Matrix. | relation refused (no_facts reply) |
| d3-trailing-superlative-023 | Who directed 'Parasite', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of Parasite. | relation refused (no_facts reply) |
| d3-trailing-superlative-024 | Who directed 'Parasite', the latest film I watched? | Sorry, my knowledge graph has no information about the director of Parasite. | relation refused (no_facts reply) |
| d3-trailing-superlative-026 | Who directed 'Whiplash', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of Whiplash. | relation refused (no_facts reply) |
| d3-trailing-superlative-027 | Who directed 'Whiplash', the latest film I watched? | Sorry, my knowledge graph has no information about the director of Whiplash. | relation refused (no_facts reply) |
| d3-trailing-superlative-029 | Who wrote the screenplay of 'The Handmaiden', the first film in the trilogy? | Sorry, my knowledge graph has no information about the screenwriter of The Handmaiden. | relation refused (no_facts reply) |
| d3-trailing-superlative-030 | Who wrote the screenplay of 'The Handmaiden', the latest film I watched? | Sorry, my knowledge graph has no information about the screenwriter of The Handmaiden. | relation refused (no_facts reply) |
| d3-trailing-superlative-032 | Who directed 'The Departed', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of The Departed. | relation refused (no_facts reply) |
| d3-trailing-superlative-033 | Who directed 'The Departed', the latest film I watched? | Sorry, my knowledge graph has no information about the director of The Departed. | relation refused (no_facts reply) |
| d3-trailing-superlative-035 | Who directed 'Jaws', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of Jaws. | relation refused (no_facts reply) |
| d3-trailing-superlative-036 | Who directed 'Jaws', the latest film I watched? | Sorry, my knowledge graph has no information about the director of Jaws. | relation refused (no_facts reply) |
| d3-trailing-superlative-038 | Who directed 'The Dark Knight', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of The Dark Knight. | relation refused (no_facts reply) |
| d3-trailing-superlative-039 | Who directed 'The Dark Knight', the latest film I watched? | Sorry, my knowledge graph has no information about the director of The Dark Knight. | relation refused (no_facts reply) |
| d3-trailing-superlative-040 | Who directed 'The Dark Knight', the last movie I saw? | Sorry, my knowledge graph has no information about the director of The Dark Knight. | relation refused (no_facts reply) |
| d3-trailing-superlative-042 | Who directed 'Schindler's List', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of Schindler's List. | relation refused (no_facts reply) |
| d3-trailing-superlative-043 | Who directed 'Schindler's List', the latest film I watched? | Sorry, my knowledge graph has no information about the director of Schindler's List. | relation refused (no_facts reply) |
| d3-trailing-superlative-044 | Who directed 'Schindler's List', the last movie I saw? | Sorry, my knowledge graph has no information about the director of Schindler's List. | relation refused (no_facts reply) |
| d3-trailing-superlative-046 | Who directed 'The Pianist', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of The Pianist. | relation refused (no_facts reply) |
| d3-trailing-superlative-047 | Who directed 'The Pianist', the latest film I watched? | Sorry, my knowledge graph has no information about the director of The Pianist. | relation refused (no_facts reply) |
| d3-trailing-superlative-049 | Who directed 'The Prestige', the first film in the trilogy? | Sorry, my knowledge graph has no information about the director of The Prestige. | relation refused (no_facts reply) |
| d3-trailing-superlative-050 | Who directed 'The Prestige', the latest film I watched? | Sorry, my knowledge graph has no information about the director of The Prestige. | relation refused (no_facts reply) |
