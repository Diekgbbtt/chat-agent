# S5 - Adversarial dataset manifest

State: S5.
Scope: the ten per-type datasets in `evals/adversarial/`, their grounding conventions, and the checks that guard them.
Scripts: `scripts/adversarial/build_datasets.py` (builder), `scripts/adversarial/check_datasets.py` (G5), `scripts/adversarial/verify_datasets.py` (re-validation).
Logs: `docs/design/adversarial/eval/s5-build.log`, `s5-check.log`, `s5-verify.log`.
The golden datasets `evals/stage1_sparql.jsonl` and `evals/stage2_factual.jsonl` are untouched.
`agent/eval.py` semantics are unchanged: a case passes when every `expected` string is in the reply (case-insensitive) and no `forbidden` string is.

## Row schema

Each line is `{"id", "input", "expected", "forbidden", "grounding"}`.

- `expected`: reply substrings that must be present. All values are harvested from the KG.
- `forbidden`: reply substrings that must be absent. All values are audited against the expected reply composition (see below).
- `grounding`: `{"entity", "entities"?, "relation", "check", "assert"}`.
  - `entity`: the asked entity (or the subvention fragment) as a QID; `entities` lists both sides for two-entity cases.
  - `relation`: the relation the answer must come from, e.g. `wdt:P57`.
  - `check`: a SPARQL query that returns the grounding evidence.
  - `assert`: one of `expected_in_rows`, `forbidden_in_rows`, `expected_count`, `ask_yesno`, `no_film_rows`.

| assert | meaning |
|---|---|
| `expected_in_rows` | The check query returns every `expected` value in a result cell. |
| `forbidden_in_rows` | The check query returns every `forbidden` value in a result cell. This proves the trap values exist in the KG. |
| `expected_count` | The check query returns a count equal to `expected[0]`. |
| `ask_yesno` | The ASK result matches `yes` in `expected[0]` (`True` for Yes, `False` for No). |
| `no_film_rows` | The check query returns no row: no film candidate exists for the mention. |

## Safety conventions

- Every `forbidden` string is checked against the expected reply composition at build time.
  The composition includes the `expected` values and the fixed reply templates the case relies on.
  The templates are `the factual answer is: `, the `no_entity()` sentence, `no information`, and `not sure what you'd like to know`.
  The builder raises when a forbidden string collides (for example `Up` inside the `no_entity()` sentence word "put" is impossible, but the check is mechanical).
- The reply templates are read from `agent/nlg.py` at build time, never copied by hand, except the two stable fragments above.
- No question strings and no answers are hardcoded in agent code. The datasets are data files; the fix reads the graph.
- T1 film-side expected values come from the exact query shape the fix must reuse (see the truncation note below).

## Coverage grid

| File | Cases | Entities | Relations | Form classes (counts) |
|---|---|---|---|---|
| `t1-negation.jsonl` | 64 | 28 | P57, P58 | film-side P57 not-direct 28; film-side P58 not-write 10; person-side P57 not-direct 16; combined negation + masked title 2; masking controls 8 |
| `t2-subvention.jsonl` | 60 | 12 | P57, P58 | crafted longer non-title, expected = clarification 36; real short-title controls 24 |
| `t3-quote-shapes.jsonl` | 57 | 12 | P57, P58, P86 | doubled quotes 6; inner spaces 6; inner period 6; inner question mark 4; working shapes (bare, single, double, curly, unclosed, suffix, lowercase) 35 |
| `t4-typos.jsonl` | 60 | 15 | P57, P58 | mapped typos 47; safe scrambles, expected = clarification 8; known-working controls 5 |
| `t5-partial-titles.jsonl` | 51 | 20 | P57, P58 | partial direct phrasings 17; partial + screenplay 17; partial quoted 10; full-title controls 6; no-film-candidate clarification 1 |
| `d1-count-class.jsonl` | 63 | 21 | P166, P161, P136, P495, P57 | awards 21; cast 12; genres 12; countries of origin 12; film-count controls with the film filter 6 |
| `d2-multiple-mentions.jsonl` | 65 | 18 | P57, P58 | two-question and mixed forms over two film mentions 52; extra P57+P58 mixed forms 13 |
| `d3-trailing-superlative.jsonl` | 55 | 18 | P57, P58, P86 | trailing superlative contexts 37; neutral trailing contexts 14; superlative inside the title, controls 4 |
| `d5-yes-no.jsonl` | 62 | 36 | P57, P58 | true claims 34 (28 P57 + 6 P58); false claims 28 |
| `d8-relation-paraphrases.jsonl` | 70 | 16 | P57, P58, P86 | directing / helm / behind the camera 36; writing 12; composing 12; existing phrasings, controls 10 |

Entity counts are distinct QIDs across `grounding.entity` and `grounding.entities`.
Every file has >= 50 cases, >= 10 distinct entities, and >= 2 relations.
Total: 598 cases.

## G5 check

Command: `.venv/bin/python scripts/adversarial/check_datasets.py`

```
10 files checked
datasets OK
```

The check asserts per file: >= 50 rows, unique ids, non-empty `input`, non-empty `expected`, and no empty `forbidden` entry.
Full log: `docs/design/adversarial/eval/s5-check.log`.

## Re-validation, 5 random cases per file

Command: `.venv/bin/python scripts/adversarial/verify_datasets.py`
Sampling: `random.Random(20261016).sample` per file, 5 cases per file, 50 cases total.
Each sampled case re-runs its own `grounding.check` query and asserts the `assert` kind.
Result: 0 failed checks.
The verification output in full:

```
## d1-count-class.jsonl (5/63 sampled, seed 20261016)
- d1-count-class-009: "How many awards did 'Interstellar' win?"
  VERIFIED: count 2 == 2
  query: SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <http://www.wikidata.org/entity/Q13417189> wdt:P166 ?x }
- d1-count-class-047: "How many countries of origin does 'The Prestige' have?"
  VERIFIED: count 2 == 2
  query: SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <http://www.wikidata.org/entity/Q46551> wdt:P495 ?x }
- d1-count-class-036: "How many countries of origin does 'The Handmaiden' have?"
  VERIFIED: count 1 == 1
  query: SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <http://www.wikidata.org/entity/Q20444585> wdt:P495 ?x }
- d1-count-class-033: "How many awards did 'The Handmaiden' win?"
  VERIFIED: count 1 == 1
  query: SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <http://www.wikidata.org/entity/Q20444585> wdt:P166 ?x }
- d1-count-class-043: "How many genres does 'Schindler's List' have?"
  VERIFIED: count 7 == 7
  query: SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <http://www.wikidata.org/entity/Q483941> wdt:P136 ?x }

## d2-multiple-mentions.jsonl (5/65 sampled, seed 20261016)
- d2-multiple-mentions-053: 'I love Forrest Gump. Who directed The Prestige?'
  VERIFIED: forbidden values ['Robert Zemeckis', 'Christopher Nolan'] confirmed in KG
  query: SELECT ?f ?x ?label WHERE { VALUES ?f { <http://www.wikidata.org/entity/Q134773> <http://www.wikidata.org/entity/Q46551> } ?f wdt:P57 ?x OPTIONAL { ?x
- d2-multiple-mentions-038: 'I love The Handmaiden. Who directed Parasite?'
  VERIFIED: forbidden values ['Park Chan-wook', 'Bong Joon-ho'] confirmed in KG
  query: SELECT ?f ?x ?label WHERE { VALUES ?f { <http://www.wikidata.org/entity/Q20444585> <http://www.wikidata.org/entity/Q61448040> } ?f wdt:P57 ?x OPTIONAL
- d2-multiple-mentions-057: "Who directed 'The Terminator'? Who directed 'Jaws'?"
  VERIFIED: forbidden values ['James Cameron', 'Steven Spielberg'] confirmed in KG
  query: SELECT ?f ?x ?label WHERE { VALUES ?f { <http://www.wikidata.org/entity/Q162255> <http://www.wikidata.org/entity/Q189505> } ?f wdt:P57 ?x OPTIONAL { ?
- d2-multiple-mentions-023: 'I love Up. Who directed Jaws?'
  VERIFIED: forbidden values ['Bob Peterson', 'Pete Docter', 'Steven Spielberg'] confirmed in KG
  query: SELECT ?f ?x ?label WHERE { VALUES ?f { <http://www.wikidata.org/entity/Q174811> <http://www.wikidata.org/entity/Q189505> } ?f wdt:P57 ?x OPTIONAL { ?
- d2-multiple-mentions-013: 'I love Jaws. Who directed Interstellar?'
  VERIFIED: forbidden values ['Steven Spielberg', 'Christopher Nolan'] confirmed in KG
  query: SELECT ?f ?x ?label WHERE { VALUES ?f { <http://www.wikidata.org/entity/Q189505> <http://www.wikidata.org/entity/Q13417189> } ?f wdt:P57 ?x OPTIONAL {

## d3-trailing-superlative.jsonl (5/55 sampled, seed 20261016)
- d3-trailing-superlative-046: "Who directed 'The Pianist', the first film in the trilogy?"
  VERIFIED: expected ['Roman Polanski'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q150804> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d3-trailing-superlative-038: "Who directed 'The Dark Knight', the first film in the trilogy?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q163872> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d3-trailing-superlative-055: "Who directed 'The Last of the Mohicans'?"
  VERIFIED: expected ['Michael Mann'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q144483> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d3-trailing-superlative-034: "Who directed 'The Departed', my favourite film?"
  VERIFIED: expected ['Martin Scorsese'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q172975> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d3-trailing-superlative-015: "Who composed the music for 'Inception', my favourite film?"
  VERIFIED: expected ['Hans Zimmer'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> wdt:P86 ?x OPTIONAL { ?x rdfs:label ?label } }

## d5-yes-no.jsonl (5/62 sampled, seed 20261016)
- d5-yes-no-034: "Did Jean Negulesco direct 'Titanic'?"
  VERIFIED: ASK=True matches expected Yes
  query: ASK { <http://www.wikidata.org/entity/Q1197729> wdt:P57 <http://www.wikidata.org/entity/Q286104> }
- d5-yes-no-018: "Did Lana Wachowski direct 'The Matrix'?"
  VERIFIED: ASK=True matches expected Yes
  query: ASK { <http://www.wikidata.org/entity/Q83495> wdt:P57 <http://www.wikidata.org/entity/Q9545711> }
- d5-yes-no-004: "Was 'Inception' directed by John Ford?"
  VERIFIED: ASK=False matches expected No
  query: ASK { <http://www.wikidata.org/entity/Q25188> wdt:P57 <http://www.wikidata.org/entity/Q51114> }
- d5-yes-no-011: "Did Woody Allen direct 'The Godfather'?"
  VERIFIED: ASK=False matches expected No
  query: ASK { <http://www.wikidata.org/entity/Q47703> wdt:P57 <http://www.wikidata.org/entity/Q25089> }
- d5-yes-no-047: "Did Ridley Scott direct 'The Prestige'?"
  VERIFIED: ASK=False matches expected No
  query: ASK { <http://www.wikidata.org/entity/Q46551> wdt:P57 <http://www.wikidata.org/entity/Q56005> }

## d8-relation-paraphrases.jsonl (5/70 sampled, seed 20261016)
- d8-relation-paraphrases-008: "Who is behind the camera on 'Interstellar'?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q13417189> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d8-relation-paraphrases-001: "Who did the directing for 'Inception'?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d8-relation-paraphrases-061: "Who is the director of 'Inception'?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d8-relation-paraphrases-046: "Who did the directing for 'Batman Begins'?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q166262> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- d8-relation-paraphrases-053: "Who is behind the camera on 'The Dark Knight'?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q163872> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }

## t1-negation.jsonl (5/64 sampled, seed 20261016)
- t1-negation-047: "Who did not direct 'The Matrix'?"
  VERIFIED: expected ['Alfred Hitchcock', 'Steven Spielberg'] found
  query: SELECT DISTINCT ?x ?label WHERE { ?f wdt:P57 ?x . FILTER NOT EXISTS { <http://www.wikidata.org/entity/Q83495> wdt:P57 ?x } OPTIONAL { ?x rdfs:label ?l
- t1-negation-051: "Who did not direct 'Jaws'?"
  VERIFIED: expected ['Alfred Hitchcock', 'Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { ?f wdt:P57 ?x . FILTER NOT EXISTS { <http://www.wikidata.org/entity/Q189505> wdt:P57 ?x } OPTIONAL { ?x rdfs:label ?
- t1-negation-060: "Who directed 'Noah'?"
  VERIFIED: expected ['Darren Aronofsky'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q286868> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t1-negation-016: 'Which movies did Michael Curtiz never direct?'
  VERIFIED: expected ['The BFG', 'The Pirates! In an Adventure with Scientists!'] found
  query: SELECT ?x ?label WHERE { ?x wdt:P31 wd:Q11424 . FILTER NOT EXISTS { ?x wdt:P57 <http://www.wikidata.org/entity/Q51491> } OPTIONAL { ?x rdfs:label ?lab
- t1-negation-056: "Who directed 'Notting Hill'?"
  VERIFIED: expected ['Roger Michell'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q200672> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }

## t2-subvention.jsonl (5/60 sampled, seed 20261016)
- t2-subvention-041: "Who directed 'Dumbo'?"
  VERIFIED: expected ['Ben Sharpsteen', 'Bill Roberts', 'Jack Kinney', 'Norm Ferguson', 'Samuel Armstrong', 'Wilfred Jackson'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q40895> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t2-subvention-027: 'Who wrote the screenplay for munich of the deep?'
  VERIFIED: forbidden values ['Eric Roth', 'Tony Kushner'] confirmed in KG
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q152456> wdt:P58 ?x OPTIONAL { ?x rdfs:label ?label } }
- t2-subvention-023: "Who directed 'The frozen within'?"
  VERIFIED: forbidden values ['Chris Buck', 'Jennifer Lee'] confirmed in KG
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q246283> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t2-subvention-004: 'Who directed looking mulan?'
  VERIFIED: forbidden values ['Barry Cook', 'Tony Bancroft'] confirmed in KG
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q537407> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t2-subvention-033: 'Who wrote the screenplay for gandhi of the deep?'
  VERIFIED: forbidden values ['Juhn Broluy'] confirmed in KG
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q202211> wdt:P58 ?x OPTIONAL { ?x rdfs:label ?label } }

## t3-quote-shapes.jsonl (5/57 sampled, seed 20261016)
- t3-quote-shapes-041: "Who directed 'Parasite'?"
  VERIFIED: expected ['Bong Joon-ho'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q61448040> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t3-quote-shapes-016: "Who wrote the screenplay for ''The Handmaiden''?"
  VERIFIED: expected ['Jeong Seo-kyeong', 'Park Chan-wook'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q20444585> wdt:P58 ?x OPTIONAL { ?x rdfs:label ?label } }
- t3-quote-shapes-045: "Who composed the music for ''Whiplash''?"
  VERIFIED: expected ['Justin Hurwitz'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q15648198> wdt:P86 ?x OPTIONAL { ?x rdfs:label ?label } }
- t3-quote-shapes-049: "Who directed ' The Departed '?"
  VERIFIED: expected ['Martin Scorsese'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q172975> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t3-quote-shapes-002: 'Who directed Inception?'
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }

## t4-typos.jsonl (5/60 sampled, seed 20261016)
- t4-typos-031: "Who directed 'the matrx'?"
  VERIFIED: expected ['Lana Wachowski', 'Lelly Wechawsku'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q83495> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t4-typos-015: "Who directed 'interstellr'?"
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q13417189> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t4-typos-036: 'Who wrote the screenplay for batmon begins?'
  VERIFIED: expected ['Christopher Nolan', 'David S. Goyer'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q166262> wdt:P58 ?x OPTIONAL { ?x rdfs:label ?label } }
- t4-typos-033: 'Who directed batman begns?'
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q166262> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t4-typos-021: 'Who directed schindlers list?'
  VERIFIED: expected ['Steven Spielberg'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q483941> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }

## t5-partial-titles.jsonl (5/51 sampled, seed 20261016)
- t5-partial-titles-049: 'who directed the matrix?'
  VERIFIED: expected ['Lana Wachowski', 'Lelly Wechawsku'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q83495> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t5-partial-titles-010: 'who directed inception?'
  VERIFIED: expected ['Christopher Nolan'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t5-partial-titles-009: "Who directed 'godfather'?"
  VERIFIED: expected ['Francis Ford Coppola'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q184768> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }
- t5-partial-titles-017: 'Who wrote the screenplay for terminator?'
  VERIFIED: expected ['Gale Anne Hurd', 'James Cameron', 'William Wisher Jr.'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q170564> wdt:P58 ?x OPTIONAL { ?x rdfs:label ?label } }
- t5-partial-titles-050: 'who directed the departed?'
  VERIFIED: expected ['Martin Scorsese'] found
  query: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q172975> wdt:P57 ?x OPTIONAL { ?x rdfs:label ?label } }

summary: 0 failed checks
```

## Decision mapping

- T1 universes follow Q9. Film side: `?x wdt:P31 wd:Q11424` without `wdt:P57` to the director. Person side: objects of `wdt:P57` without a `wdt:P57` edge from the film.
- T1 film-side truncation follows the accepted risk. A film complement always exceeds `Settings.max_fetch_rows` = 10,000. The builder picks `expected` labels from the first 400 rows of the exact query shape above. The S8 implementation must reuse this query shape so the reply contains these labels.
- T2 restriction follows Q12 plus the subvention guard. All 36 red carriers are absent from the lexicon and score below 0.80 against the parser's fuzzy list. `forbidden` holds the fragment's real answers, so a substring match inside the longer non-title cannot pass.
- T3 shapes follow Q12. Working shapes include the doubled quote-free forms that already pass. The Godfather cases forbid `Lal and Siddique`, the current wrong link.
- T4 matching follows Q7, Q10, and Q11. A typo enters the file only when the intended article-stripped family is the unique best match with score >= 0.85 (>= 0.80 for cores of 6 characters or fewer) and a margin >= 0.05 over the next family. The wrong-link reply of the current parser becomes `forbidden`.
- T5 follows Q15, which revises the Q2 example. "matrix" and "godfather" now resolve to the famous film, not to a clarification. Clarification remains only when no film candidate exists. A probe over the lexicon found one such famous-title partial: "twilight zone". Per the probe, TV and streaming cores in this KG either are film-tagged ("seinfeld", "stranger things") or absent. The clarification reply is covered mainly by D2.
- D1 expects raw counts over the asked relation and keeps the film-type filter only for film-count questions (the D1 control). The red reply `the factual answer is: 0` is forbidden on every case.
- D2 follows Q16: two title mentions produce the clarification reply. `forbidden` forbids any answer, both films' answers, and names the two mentions' directors.
- D3 expects the base lookup and forbids `no information`, the current refusal.
- D5 follows Q13: the reply shape is `The factual answer is: Yes` or `The factual answer is: No`. `forbidden` names the real and the claimed director, so a bare list answer cannot pass.
- D8 follows Q14: nominalisations and idioms map to canonical relation words. `forbidden` is the current refusal `not sure what you'd like to know`.

## Rebuild

Command: `.venv/bin/python scripts/adversarial/build_datasets.py`
The builder is deterministic: fixed seed, sorted pools, no network access.
It overwrites the ten files and prints the coverage grid as JSON (log: `s5-build.log`).
