# t2-subvention - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/t2-subvention.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/t2-subvention.log`
- Log: `docs/design/adversarial/eval/iter0/t2-subvention.log`
- Result: 24/60 passed (40.0%). Latency: median 0.00 s, max 0.00 s.
- Fix bar: pass rate >= 0.8, so at least 48/60 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| answered instead of clarifying | 36 | t2-subvention-001 | The factual answer is: Chris Buck and Kevin Lima |

Total failures: 36 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| t2-subvention-001 | Who directed looking tarzan? | The factual answer is: Chris Buck and Kevin Lima | answered instead of clarifying |
| t2-subvention-002 | Who directed 'The tarzan within'? | The factual answer is: Chris Buck and Kevin Lima | answered instead of clarifying |
| t2-subvention-003 | Who wrote the screenplay for tarzan of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-004 | Who directed looking mulan? | The factual answer is: Barry Cook and Tony Bancroft | answered instead of clarifying |
| t2-subvention-005 | Who directed 'The mulan within'? | The factual answer is: Barry Cook and Tony Bancroft | answered instead of clarifying |
| t2-subvention-006 | Who wrote the screenplay for mulan of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-007 | Who directed looking dumbo? | The factual answer is: Ben Sharpsteen, Bill Roberts, Jack Kinney, Norm Ferguson, Samuel A… | answered instead of clarifying |
| t2-subvention-008 | Who directed 'The dumbo within'? | The factual answer is: Ben Sharpsteen, Bill Roberts, Jack Kinney, Norm Ferguson, Samuel A… | answered instead of clarifying |
| t2-subvention-009 | Who wrote the screenplay for dumbo of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-010 | Who directed looking moana? | The factual answer is: Chris Williams, Don Hall, John Musker, and Ron Clements | answered instead of clarifying |
| t2-subvention-011 | Who directed 'The moana within'? | The factual answer is: Chris Williams, Don Hall, John Musker, and Ron Clements | answered instead of clarifying |
| t2-subvention-012 | Who wrote the screenplay for moana of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-013 | Who directed looking thor? | The factual answer is: Kenneth Branagh | answered instead of clarifying |
| t2-subvention-014 | Who directed 'The thor within'? | The factual answer is: Kenneth Branagh | answered instead of clarifying |
| t2-subvention-015 | Who wrote the screenplay for thor of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-016 | Who directed looking bambi? | The factual answer is: Bill Roberts, David Hand, Graham Heid, James Algar, Norman Wright,… | answered instead of clarifying |
| t2-subvention-017 | Who directed 'The bambi within'? | The factual answer is: Bill Roberts, David Hand, Graham Heid, James Algar, Norman Wright,… | answered instead of clarifying |
| t2-subvention-018 | Who wrote the screenplay for bambi of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-019 | Who directed looking ali? | The factual answer is: Michael Mann | answered instead of clarifying |
| t2-subvention-020 | Who directed 'The ali within'? | The factual answer is: Michael Mann | answered instead of clarifying |
| t2-subvention-021 | Who wrote the screenplay for ali of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-022 | Who directed looking frozen? | The factual answer is: Chris Buck and Jennifer Lee | answered instead of clarifying |
| t2-subvention-023 | Who directed 'The frozen within'? | The factual answer is: Chris Buck and Jennifer Lee | answered instead of clarifying |
| t2-subvention-024 | Who wrote the screenplay for frozen of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-025 | Who directed looking munich? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| t2-subvention-026 | Who directed 'The munich within'? | The factual answer is: Steven Spielberg | answered instead of clarifying |
| t2-subvention-027 | Who wrote the screenplay for munich of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-028 | Who directed looking avatar? | The factual answer is: James Cameron | answered instead of clarifying |
| t2-subvention-029 | Who directed 'The avatar within'? | The factual answer is: James Cameron | answered instead of clarifying |
| t2-subvention-030 | Who wrote the screenplay for avatar of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-031 | Who directed looking gandhi? | The factual answer is: Richard Attenborough | answered instead of clarifying |
| t2-subvention-032 | Who directed 'The gandhi within'? | The factual answer is: Richard Attenborough | answered instead of clarifying |
| t2-subvention-033 | Who wrote the screenplay for gandhi of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
| t2-subvention-034 | Who directed looking elvis? | The factual answer is: Buz Luhrmunn | answered instead of clarifying |
| t2-subvention-035 | Who directed 'The elvis within'? | The factual answer is: Buz Luhrmunn | answered instead of clarifying |
| t2-subvention-036 | Who wrote the screenplay for elvis of the deep? | The factual answer is: Peter Benchley | answered instead of clarifying |
