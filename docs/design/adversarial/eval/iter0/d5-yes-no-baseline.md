# d5-yes-no - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/d5-yes-no.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/d5-yes-no.log`
- Log: `docs/design/adversarial/eval/iter0/d5-yes-no.log`
- Result: 0/62 passed (0.0%). Latency: median 0.00 s, max 0.00 s.
- Fix bar: pass rate >= 0.8, so at least 50/62 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| trap value returned ('Christopher Nolan') | 18 | d5-yes-no-002 | The factual answer is: Christopher Nolan |
| wrong answer: expected value absent | 11 | d5-yes-no-001 | The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstellar, Oppenheimer, The… |
| trap value returned ('Francis Ford Coppola') | 9 | d5-yes-no-010 | The factual answer is: Francis Ford Coppola |
| trap value returned ('Lana Wachowski') | 8 | d5-yes-no-018 | The factual answer is: Lana Wachowski and Lelly Wechawsku |
| trap value returned ('Bong Joon-ho') | 3 | d5-yes-no-050 | The factual answer is: Bong Joon-ho |
| trap value returned ('Damien Chazelle') | 3 | d5-yes-no-054 | The factual answer is: Damien Chazelle |
| trap value returned ('Jean Negulesco') | 3 | d5-yes-no-034 | The factual answer is: Jean Negulesco |
| trap value returned ('Park Chan-wook') | 3 | d5-yes-no-030 | The factual answer is: Park Chan-wook |
| trap value returned ('Steven Spielberg') | 3 | d5-yes-no-026 | The factual answer is: Steven Spielberg |
| trap value returned ('the Wachowskis') | 1 | d5-yes-no-061 | The factual answer is: the Wachowskis |

Total failures: 62 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| d5-yes-no-002 | Did Christopher Nolan direct 'Inception'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-003 | Did John Ford direct 'Inception'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-004 | Was 'Inception' directed by John Ford? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-006 | Did Christopher Nolan direct 'Interstellar'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-007 | Did Alfred Hitchcock direct 'Interstellar'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-008 | Was 'Interstellar' directed by Alfred Hitchcock? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-038 | Did Christopher Nolan direct 'Batman Begins'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-039 | Did William Wyler direct 'Batman Begins'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-040 | Was 'Batman Begins' directed by William Wyler? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-041 | Did Christopher Nolan direct The Dark Knight? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-042 | Did Christopher Nolan direct 'The Dark Knight'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-043 | Did Howard Hawks direct 'The Dark Knight'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-044 | Was 'The Dark Knight' directed by Howard Hawks? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-046 | Did Christopher Nolan direct 'The Prestige'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-047 | Did Ridley Scott direct 'The Prestige'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-048 | Was 'The Prestige' directed by Ridley Scott? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-057 | Was 'Inception' written by Christopher Nolan? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-058 | Was 'Interstellar' written by Christopher Nolan? | The factual answer is: Christopher Nolan and Jonathan Nolan | trap value returned ('Christopher Nolan') |
| d5-yes-no-001 | Did Christopher Nolan direct Inception? | The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstell… | wrong answer: expected value absent |
| d5-yes-no-005 | Did Christopher Nolan direct Interstellar? | The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstell… | wrong answer: expected value absent |
| d5-yes-no-009 | Did Francis Ford Coppola direct The Godfather? | The factual answer is: Apocalypse Now, Bram Stoker's Dracula, Captain EO, Dementia 13, Fi… | wrong answer: expected value absent |
| d5-yes-no-017 | Did Lana Wachowski direct The Matrix? | The factual answer is: Bound, Enter the Matrix, Jupiter Ascending, Speed Racer, The Matri… | wrong answer: expected value absent |
| d5-yes-no-025 | Did Steven Spielberg direct Jaws? | The factual answer is: 1941, 1941 Part 2, A.I. Artificial Intelligence, Always, Amistad, … | wrong answer: expected value absent |
| d5-yes-no-029 | Did Park Chan-wook direct The Handmaiden? | The factual answer is: Decision to Leave, I'm a Cyborg, But That's OK, Oldboy, Sympathy f… | wrong answer: expected value absent |
| d5-yes-no-033 | Did Jean Negulesco direct Titanic? | The factual answer is: A Certain Smile, Daddy Long Legs, How to Marry a Millionaire, Humo… | wrong answer: expected value absent |
| d5-yes-no-037 | Did Christopher Nolan direct Batman Begins? | The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstell… | wrong answer: expected value absent |
| d5-yes-no-045 | Did Christopher Nolan direct The Prestige? | The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstell… | wrong answer: expected value absent |
| d5-yes-no-049 | Did Bong Joon-ho direct Parasite? | The factual answer is: Memories of Murder, Mother, Parasite, Snowpiercer, and The Host | wrong answer: expected value absent |
| d5-yes-no-053 | Did Damien Chazelle direct Whiplash? | The factual answer is: Babylon, First Man, First Man Reloaded, La La Land, and Whiplash | wrong answer: expected value absent |
| d5-yes-no-010 | Did Francis Ford Coppola direct 'The Godfather'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-011 | Did Woody Allen direct 'The Godfather'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-012 | Was 'The Godfather' directed by Woody Allen? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-013 | Did Francis Ford Coppola direct The Godfather Part II? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-014 | Did Francis Ford Coppola direct 'The Godfather Part II'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-015 | Did Michael Curtiz direct 'The Godfather Part II'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-016 | Was 'The Godfather Part II' directed by Michael Curtiz? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-059 | Was 'The Godfather' written by Francis Ford Coppola? | The factual answer is: Francis Ford Coppola and Mario Puzo | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-060 | Was 'The Godfather Part II' written by Francis Ford Coppola? | The factual answer is: Francis Ford Coppola and Mario Puzo | trap value returned ('Francis Ford Coppola') |
| d5-yes-no-018 | Did Lana Wachowski direct 'The Matrix'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-019 | Did Steven Spielberg direct 'The Matrix'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-020 | Was 'The Matrix' directed by Steven Spielberg? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-021 | Did Lana Wachowski direct The Matrix Reloaded? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-022 | Did Lana Wachowski direct 'The Matrix Reloaded'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-023 | Did George Cukor direct 'The Matrix Reloaded'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-024 | Was 'The Matrix Reloaded' directed by George Cukor? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-062 | Was 'The Matrix Reloaded' written by Lana Wachowski? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| d5-yes-no-050 | Did Bong Joon-ho direct 'Parasite'? | The factual answer is: Bong Joon-ho | trap value returned ('Bong Joon-ho') |
| d5-yes-no-051 | Did Sidney Lumet direct 'Parasite'? | The factual answer is: Bong Joon-ho | trap value returned ('Bong Joon-ho') |
| d5-yes-no-052 | Was 'Parasite' directed by Sidney Lumet? | The factual answer is: Bong Joon-ho | trap value returned ('Bong Joon-ho') |
| d5-yes-no-054 | Did Damien Chazelle direct 'Whiplash'? | The factual answer is: Damien Chazelle | trap value returned ('Damien Chazelle') |
| d5-yes-no-055 | Did Billy Wilder direct 'Whiplash'? | The factual answer is: Damien Chazelle | trap value returned ('Damien Chazelle') |
| d5-yes-no-056 | Was 'Whiplash' directed by Billy Wilder? | The factual answer is: Damien Chazelle | trap value returned ('Damien Chazelle') |
| d5-yes-no-034 | Did Jean Negulesco direct 'Titanic'? | The factual answer is: Jean Negulesco | trap value returned ('Jean Negulesco') |
| d5-yes-no-035 | Did Martin Scorsese direct 'Titanic'? | The factual answer is: Jean Negulesco | trap value returned ('Jean Negulesco') |
| d5-yes-no-036 | Was 'Titanic' directed by Martin Scorsese? | The factual answer is: Jean Negulesco | trap value returned ('Jean Negulesco') |
| d5-yes-no-030 | Did Park Chan-wook direct 'The Handmaiden'? | The factual answer is: Park Chan-wook | trap value returned ('Park Chan-wook') |
| d5-yes-no-031 | Did John Huston direct 'The Handmaiden'? | The factual answer is: Park Chan-wook | trap value returned ('Park Chan-wook') |
| d5-yes-no-032 | Was 'The Handmaiden' directed by John Huston? | The factual answer is: Park Chan-wook | trap value returned ('Park Chan-wook') |
| d5-yes-no-026 | Did Steven Spielberg direct 'Jaws'? | The factual answer is: Steven Spielberg | trap value returned ('Steven Spielberg') |
| d5-yes-no-027 | Did Clint Eastwood direct 'Jaws'? | The factual answer is: Steven Spielberg | trap value returned ('Steven Spielberg') |
| d5-yes-no-028 | Was 'Jaws' directed by Clint Eastwood? | The factual answer is: Steven Spielberg | trap value returned ('Steven Spielberg') |
| d5-yes-no-061 | Was 'The Matrix' written by the Wachowskis? | The factual answer is: the Wachowskis | trap value returned ('the Wachowskis') |
