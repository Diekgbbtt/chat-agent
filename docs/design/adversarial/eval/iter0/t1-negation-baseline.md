# t1-negation - baseline (iter0)

- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/t1-negation.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/t1-negation.log`
- Log: `docs/design/adversarial/eval/iter0/t1-negation.log`
- Result: 8/64 passed (12.5%). Latency: median 0.00 s, max 0.01 s.
- Fix bar: pass rate >= 0.8, so at least 52/64 cases must pass.

## Failure clusters

| Cluster | Count | Example id | Example reply |
|---|---|---|---|
| wrong answer: expected value absent | 28 | t1-negation-001 | The factual answer is: 3 Godfathers, Arrowsmith, Cavalry Trilogy, Cheyenne Autumn, December 7th, Donovan's Re… |
| trap value returned ('Christopher Nolan') | 4 | t1-negation-039 | The factual answer is: Christopher Nolan |
| trap value returned ('Francis Ford Coppola') | 4 | t1-negation-043 | The factual answer is: Francis Ford Coppola |
| trap value returned ('Lana Wachowski') | 4 | t1-negation-047 | The factual answer is: Lana Wachowski and Lelly Wechawsku |
| trap value returned ('Indiana Jones and the Kingdom of the Crystal Skull') | 3 | t1-negation-017 | The factual answer is: 1941, 1941 Part 2, A.I. Artificial Intelligence, Always, Amistad, Bridge of Spies, Cat… |
| trap value returned ('It Should Happen to You') | 3 | t1-negation-020 | The factual answer is: A Bill of Divorcement, A Double Life, A Star Is Born, A Woman's Face, Adam's Rib, Adam… |
| trap value returned ('Colombiana') | 2 | t1-negation-035 | The factual answer is: Angel-A, Anna, Bandidas, Colombiana, District 13, Fanfan la Tulipe, From Paris with Lo… |
| trap value returned ('Men Without Women') | 2 | t1-negation-037 | The factual answer is: Air Force, And Then There Were None, And Then There Were None Returns, Bataan, Bringin… |
| trap value returned ('Park Chan-wook') | 2 | t1-negation-053 | The factual answer is: Park Chan-wook |
| trap value returned ('Steven Spielberg') | 2 | t1-negation-051 | The factual answer is: Steven Spielberg |
| trap value returned ('Ethan Coen') | 1 | t1-negation-063 | The factual answer is: Ethan Coen and Joel Coen |
| trap value returned ('Roger Michell') | 1 | t1-negation-064 | The factual answer is: Roger Michell |

Total failures: 56 (sum of the cluster counts).

## Failing cases

| id | input | reply | cluster |
|---|---|---|---|
| t1-negation-001 | Which movies did John Ford not direct? | The factual answer is: 3 Godfathers, Arrowsmith, Cavalry Trilogy, Cheyenne Autumn, Decemb… | wrong answer: expected value absent |
| t1-negation-002 | Which films has John Ford not directed? | The factual answer is: 3 Godfathers, Arrowsmith, Cavalry Trilogy, Cheyenne Autumn, Decemb… | wrong answer: expected value absent |
| t1-negation-003 | Which movies were not directed by John Ford? | The factual answer is: 3 Godfathers, Arrowsmith, Cavalry Trilogy, Cheyenne Autumn, Decemb… | wrong answer: expected value absent |
| t1-negation-004 | Which movies did John Ford never direct? | The factual answer is: 3 Godfathers, Arrowsmith, Cavalry Trilogy, Cheyenne Autumn, Decemb… | wrong answer: expected value absent |
| t1-negation-005 | Which movies did Alfred Hitchcock not direct? | The factual answer is: Blackmail, Dial M for Murder, Family Plot, Foreign Correspondent, … | wrong answer: expected value absent |
| t1-negation-006 | Which films has Alfred Hitchcock not directed? | The factual answer is: Blackmail, Dial M for Murder, Family Plot, Foreign Correspondent, … | wrong answer: expected value absent |
| t1-negation-007 | Which movies were not directed by Alfred Hitchcock? | The factual answer is: Blackmail, Dial M for Murder, Family Plot, Foreign Correspondent, … | wrong answer: expected value absent |
| t1-negation-008 | Which movies did Alfred Hitchcock never direct? | The factual answer is: Blackmail, Dial M for Murder, Family Plot, Foreign Correspondent, … | wrong answer: expected value absent |
| t1-negation-009 | Which movies did Woody Allen not direct? | The factual answer is: A Midsummer Night's Sex Comedy, Alice, Annie Hall, Bananas, Blue J… | wrong answer: expected value absent |
| t1-negation-010 | Which films has Woody Allen not directed? | The factual answer is: A Midsummer Night's Sex Comedy, Alice, Annie Hall, Bananas, Blue J… | wrong answer: expected value absent |
| t1-negation-011 | Which movies were not directed by Woody Allen? | The factual answer is: A Midsummer Night's Sex Comedy, Alice, Annie Hall, Bananas, Blue J… | wrong answer: expected value absent |
| t1-negation-012 | Which movies did Woody Allen never direct? | The factual answer is: A Midsummer Night's Sex Comedy, Alice, Annie Hall, Bananas, Blue J… | wrong answer: expected value absent |
| t1-negation-013 | Which movies did Michael Curtiz not direct? | The factual answer is: Angels with Dirty Faces, Anthony Adverse, Black Fury, Black Legion… | wrong answer: expected value absent |
| t1-negation-014 | Which films has Michael Curtiz not directed? | The factual answer is: Angels with Dirty Faces, Anthony Adverse, Black Fury, Black Legion… | wrong answer: expected value absent |
| t1-negation-015 | Which movies were not directed by Michael Curtiz? | The factual answer is: Angels with Dirty Faces, Anthony Adverse, Black Fury, Black Legion… | wrong answer: expected value absent |
| t1-negation-016 | Which movies did Michael Curtiz never direct? | The factual answer is: Angels with Dirty Faces, Anthony Adverse, Black Fury, Black Legion… | wrong answer: expected value absent |
| t1-negation-023 | Which movies did Clint Eastwood not direct? | The factual answer is: A Perfect World, Absolute Power, American Sniper, Bird, Breezy, Br… | wrong answer: expected value absent |
| t1-negation-024 | Which films has Clint Eastwood not directed? | The factual answer is: A Perfect World, Absolute Power, American Sniper, Bird, Breezy, Br… | wrong answer: expected value absent |
| t1-negation-025 | Which movies were not directed by Clint Eastwood? | The factual answer is: A Perfect World, Absolute Power, American Sniper, Bird, Breezy, Br… | wrong answer: expected value absent |
| t1-negation-026 | Which movies did John Huston not direct? | The factual answer is: A Farewell to Arms, Across the Pacific, Annie, Beat the Devil, Cas… | wrong answer: expected value absent |
| t1-negation-027 | Which films has John Huston not directed? | The factual answer is: A Farewell to Arms, Across the Pacific, Annie, Beat the Devil, Cas… | wrong answer: expected value absent |
| t1-negation-028 | Which movies were not directed by John Huston? | The factual answer is: A Farewell to Arms, Across the Pacific, Annie, Beat the Devil, Cas… | wrong answer: expected value absent |
| t1-negation-029 | Which films did Ben Hecht not write? | The factual answer is: 7 Faces of Dr. Lao, A Farewell to Arms, Angels Over Broadway, Ange… | wrong answer: expected value absent |
| t1-negation-030 | Which movies has Ben Hecht not written? | The factual answer is: 7 Faces of Dr. Lao, A Farewell to Arms, Angels Over Broadway, Ange… | wrong answer: expected value absent |
| t1-negation-031 | Which films did Woody Allen not write? | The factual answer is: A Midsummer Night's Sex Comedy, Alice, Annie Hall, Bananas, Blue J… | wrong answer: expected value absent |
| t1-negation-032 | Which movies has Woody Allen not written? | The factual answer is: A Midsummer Night's Sex Comedy, Alice, Annie Hall, Bananas, Blue J… | wrong answer: expected value absent |
| t1-negation-033 | Which films did Tonino Guerra not write? | The factual answer is: Amarcord, And the Ship Sails On, Beyond the Clouds, Blowup, Carmen… | wrong answer: expected value absent |
| t1-negation-034 | Which movies has Tonino Guerra not written? | The factual answer is: Amarcord, And the Ship Sails On, Beyond the Clouds, Blowup, Carmen… | wrong answer: expected value absent |
| t1-negation-039 | Who did not direct 'Inception'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| t1-negation-040 | Who has not directed 'Inception'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| t1-negation-041 | Who did not direct 'Interstellar'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| t1-negation-042 | Who has not directed 'Interstellar'? | The factual answer is: Christopher Nolan | trap value returned ('Christopher Nolan') |
| t1-negation-043 | Who did not direct 'The Godfather'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| t1-negation-044 | Who has not directed 'The Godfather'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| t1-negation-045 | Who did not direct 'The Godfather Part II'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| t1-negation-046 | Who has not directed 'The Godfather Part II'? | The factual answer is: Francis Ford Coppola | trap value returned ('Francis Ford Coppola') |
| t1-negation-047 | Who did not direct 'The Matrix'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| t1-negation-048 | Who has not directed 'The Matrix'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| t1-negation-049 | Who did not direct 'The Matrix Reloaded'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| t1-negation-050 | Who has not directed 'The Matrix Reloaded'? | The factual answer is: Lana Wachowski and Lelly Wechawsku | trap value returned ('Lana Wachowski') |
| t1-negation-017 | Which movies did Steven Spielberg not direct? | The factual answer is: 1941, 1941 Part 2, A.I. Artificial Intelligence, Always, Amistad, … | trap value returned ('Indiana Jones and the Kingdom of the … |
| t1-negation-018 | Which films has Steven Spielberg not directed? | The factual answer is: 1941, 1941 Part 2, A.I. Artificial Intelligence, Always, Amistad, … | trap value returned ('Indiana Jones and the Kingdom of the … |
| t1-negation-019 | Which movies were not directed by Steven Spielberg? | The factual answer is: 1941, 1941 Part 2, A.I. Artificial Intelligence, Always, Amistad, … | trap value returned ('Indiana Jones and the Kingdom of the … |
| t1-negation-020 | Which movies did George Cukor not direct? | The factual answer is: A Bill of Divorcement, A Double Life, A Star Is Born, A Woman's Fa… | trap value returned ('It Should Happen to You') |
| t1-negation-021 | Which films has George Cukor not directed? | The factual answer is: A Bill of Divorcement, A Double Life, A Star Is Born, A Woman's Fa… | trap value returned ('It Should Happen to You') |
| t1-negation-022 | Which movies were not directed by George Cukor? | The factual answer is: A Bill of Divorcement, A Double Life, A Star Is Born, A Woman's Fa… | trap value returned ('It Should Happen to You') |
| t1-negation-035 | Which films did Luc Besson not write? | The factual answer is: Angel-A, Anna, Bandidas, Colombiana, District 13, Fanfan la Tulipe… | trap value returned ('Colombiana') |
| t1-negation-036 | Which movies has Luc Besson not written? | The factual answer is: Angel-A, Anna, Bandidas, Colombiana, District 13, Fanfan la Tulipe… | trap value returned ('Colombiana') |
| t1-negation-037 | Which films did Dudley Nichols not write? | The factual answer is: Air Force, And Then There Were None, And Then There Were None Retu… | trap value returned ('Men Without Women') |
| t1-negation-038 | Which movies has Dudley Nichols not written? | The factual answer is: Air Force, And Then There Were None, And Then There Were None Retu… | trap value returned ('Men Without Women') |
| t1-negation-053 | Who did not direct 'The Handmaiden'? | The factual answer is: Park Chan-wook | trap value returned ('Park Chan-wook') |
| t1-negation-054 | Who has not directed 'The Handmaiden'? | The factual answer is: Park Chan-wook | trap value returned ('Park Chan-wook') |
| t1-negation-051 | Who did not direct 'Jaws'? | The factual answer is: Steven Spielberg | trap value returned ('Steven Spielberg') |
| t1-negation-052 | Who has not directed 'Jaws'? | The factual answer is: Steven Spielberg | trap value returned ('Steven Spielberg') |
| t1-negation-063 | Who did not direct 'No Country for Old Men'? | The factual answer is: Ethan Coen and Joel Coen | trap value returned ('Ethan Coen') |
| t1-negation-064 | Who did not direct 'Notting Hill'? | The factual answer is: Roger Michell | trap value returned ('Roger Michell') |
