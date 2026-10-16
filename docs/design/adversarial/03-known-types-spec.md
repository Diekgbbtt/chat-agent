# S3 - Specification of the five known adversarial types (T1-T5)

State: S3.
All red/green evidence comes from `docs/design/adversarial/eval/s3-probe.log` and `s3-probe2.log` (`scripts/adversarial/s3_probe.py`, `s3_probe2.py`).
Decision nodes carry the operator's answers from the S0 batch (Q1-Q8) and the S3 batch (Q9-Q12).

Shared definitions (from `docs/design/adversarial/01-domain-model.md` and `02-architecture-contracts.md`):

- Film universe: `wdt:P31 wd:Q11424` = 12,245 entities.
- Director universe: objects of `wdt:P57` = 6,109 entities.
- Films that have a director (P57 subjects): 13,746 entities.
- Human universe: `wdt:P31 wd:Q5` = 85,854 entities.
- Safe-failure reply: `nlg.no_entity()` = "I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?" (already expected by golden cases `greeting` and `unknown-title`).
- Row cap: `Settings.max_fetch_rows` = 10,000 (`agent/config.py` line 101); a complement reply truncates deterministically at that cap.

---

## T1 - Negation (one-level)

**Definition.** One-level negation scoped to the relation phrase: "not", "no", "never", and contractions ("didn't", "doesn't", "hasn't", "wasn't") applied to the relation verb, in either direction ("Which movies did X not direct?", "Who did not direct Y?").
Out of scope: double negation (operator Q8 - disregarded entirely), yes/no questions, negation outside the relation phrase.

**Invariant.** Negation words inside entity mentions must never trigger T1: "No Country for Old Men", "Don't Look Up".
The entity span is masked before negation detection.

**Attacked boundary.** B3 (Phase 2 -> 3: relation detection) - the word "not" is invisible to `_find_predicates` and to direction choice; and B4 (Phase 3 -> 4) - no complement template exists.

**Breaking phase.** Phase 3 (negation dropped silently) and phase 4 (missing query template).

**Red cases (measured, `s3-probe.log`).**

- R1: `"Which movies did Christopher Nolan not direct?"` -> `"The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstellar, Oppenheimer, The Dark Knight, The Dark Knight Rises, The Dark Knight trilogy, and The Prestige"` (his own films, not the complement).
- R2: `"Who did not direct 'Inception'?"` -> `"The factual answer is: Christopher Nolan"` (the positive answer).

**Green cases (after normalisation).**

- G1: R1 must contain complement members and no positive members.
  Grounded: `"The Godfather"` appears in the complement rows (verified), `"Inception"` does not.
- G2: R2 must contain directors that are not Inception's director; `"Christopher Nolan"` must not appear.
  Grounded: director universe = 6,109 entities (fits under the 10,000-row cap, no truncation).
- G3 (masking control, green today, must stay): `"Who directed 'No Country for Old Men'?"` -> `"The factual answer is: Ethan Coen and Joel Coen"`; the reply must not contain the T1 refusal text.

**Expected behaviour.** The complement of the relation over its domain: films not directed by X (film universe, 12,245, truncated at 10,000 rows), or directors who did not direct Y (director universe, 6,109).
Reply shape: the standard `nlg.answer()` list, same template as positive lookups.

**Decision nodes (resolved).**

- Q1: always compute the complement, regardless of size; one-level negation in scope.
- Q8: double negation disregarded; entity-embedded negation masked.
- Q9: universe = relation domains: films = `wdt:P31 wd:Q11424`; directors = objects of `wdt:P57`.
- Accepted risk: the film complement reply truncates at 10,000 rows; dataset expected values are harvested from the actual reply to stay deterministic.

**Dataset plan (S5).** 50+ cases: >= 10 distinct entities, 2 relations (P57 director; P58 screenwriter complement on the film side), mix of "did not", "has not", "never" forms; 15+ masking control cases with negation words inside titles.

---

## T2 - Subvention (entity name contains another entity name)

**Definition.** A title-like mention Y is not an entity, while a proper substring or token of Y is an entity X; the agent must refuse (no_entity) instead of answering for X.
Includes lowercase forms and fragment links caused by punctuation ("Don" inside "Don't").

**Attacked boundary.** B1 (source -> Phase 1: span selection picks the fragment) and B5 (Phase 4 -> 5: `has_facts` turns the fragment into a confident wrong reply).

**Breaking phase.** Phase 1 primarily (span selection); phase 5 amplifies (no_facts about the fragment instead of a recognition failure).

**Red cases (measured, `s3-probe.log`).**

- R1: `"who directed don't look up"` -> `"The factual answer is: Bob Peterson and Pete Docter"` (directors of "Up", Q174811, `is_film=True`, label "Up"). "Don't Look Up" is not in the KG (grounded: `lex.lbl2ent["don't look up"] == []`).
- R2: `"Who directed 'Don't Look Up'?"` -> `"Sorry, my knowledge graph has no information about the director of Don."` (the apostrophe-quote pairing links "Don", Q28008305, label "Don").

**Green cases (after normalisation).**

- G1: R1 -> the `no_entity()` sentence; forbidden values: "Bob Peterson", "Pete Docter".
- G2: R2 -> the `no_entity()` sentence; forbidden values: "director of Don", "Lal and Siddique" (not reachable here, listed to pin the class).
- G3 (positive control, green today, must stay): `"Who directed 'No Country for Old Men'?"` -> `"The factual answer is: Ethan Coen and Joel Coen"` (a known title that contains the word "No").

**Expected behaviour.** Unknown longer titles refuse with the `no_entity()` sentence.
The guard generalises: if the matched span sits inside a longer contiguous non-stopword run whose full phrase is not a known label, the agent refuses.

**Decision nodes (resolved).**

- A1 (S0): safe failure uses the existing `no_entity()` template.
- Q12: apostrophes inside words are letters, never quote delimiters.

**Dataset plan (S5).** 50+ cases: >= 10 distinct fragment entities (Up Q174811, Her Q788822, Godfather Q5576354, Nine, Giant, Noah, ...), each embedded in a crafted unknown longer title (for example "Don't Look Up", "Looking Up"); forbidden = the fragment entity's real answer values; plus 10+ positive controls with short real titles.

---

## T3 - Sparse entity formatting (citation marks)

**Definition.** Citation-mark variants around the entity mention: none, single, double, smart (curly), unclosed, doubled (`''Inception''`), whitespace inside quotes, punctuation inside or outside quotes, mixed case.
The mention must be recognised in all these forms.

**Attacked boundary.** B1 (source -> Phase 1): "tokens, quotes, and casing carry the entity mention".

**Breaking phase.** Phase 1 (quote pairing and token cleanup).

**Red cases (measured, `s3-probe.log`, `s3-probe2.log`).**

- R1: `"Who directed ''Inception''?"` -> `no_entity` reply (expected: "Christopher Nolan").
- R2: `"Who directed 'Inception.'?"` -> `no_entity` reply (expected: "Christopher Nolan").
- R3: `"Who directed ''The Godfather''?"` -> `"The factual answer is: Lal and Siddique"` (quote doubling plus fragment link to Q5576354; expected: "Francis Ford Coppola" after the Q10 family rule).

**Green cases (measured today, must stay).**

- `"Who directed Inception?"` -> Christopher Nolan.
- `'Who directed "Inception"?'` (straight double) -> Christopher Nolan.
- `"who directed \u201cthe handmaiden\u201d?"` (smart quotes) -> Park Chan-wook.
- `"Who directed 'Inception ?"` (unclosed) -> Christopher Nolan.
- `"Who directed 'Inception' (2010)?"` -> Christopher Nolan.

**Expected behaviour.** All citation-mark variants resolve to the same linked entity as the clean form; doubled quotes and whitespace are normalised away before parsing.

**Decision nodes (resolved).**

- Q12: full normalisation: doubled quotes collapsed, whitespace inside quotes stripped, apostrophes inside words are not delimiters.

**Dataset plan (S5).** 50+ cases: >= 10 distinct entities; 15+ red-form cases (doubled quotes, inner punctuation, inner whitespace, quote pairs around partial titles) plus 35+ variants of already-working shapes to lock the behaviour.

---

## T4 - Minimal entity spelling mistakes

**Definition.** 1-2 edit typos (swap, insert, delete) in a title mention; the typo must normalise to the intended entity when the intended match is unique; a typo that matches nothing must fail safely.

**Attacked boundary.** B2 (Phase 1 -> 2): the fuzzy matcher maps to a wrong or nearby label.

**Breaking phase.** Phase 2 (`Parser._find_entry` fuzzy pass, lines 134-146): article-stripped label families are invisible to the matcher.

**Red cases (measured, `s3-probe.log`, `s3-probe2.log`).**

- R1: `"Who directed Godfahter?"` -> `"The factual answer is: Lal and Siddique"` (fuzzy `godfather` 0.889 -> Q5576354; intended: The Godfather Q47703 -> Francis Ford Coppola; the article variant `the godfather` only scores 0.714, below the 0.85 cutoff).
- R2: `"Who directed Terminater?"` -> `no_entity` reply (intended: The Terminator Q162255; grounded: no fuzzy match >= 0.70 today).
- R3: `"Who directed Jazws?"` -> `no_entity` reply (intended: Jaws Q1322449; grounded: score exactly 0.80 against `jaws`, below the 0.85 cutoff).

**Green cases (measured today or golden, must stay).**

- `"Who directed the Godfahter?"` -> Francis Ford Coppola (golden case `godfather-typo`, score 0.923 against `the godfather`).
- `"Who wrote the screenplay for Intersteller?"` -> "Christopher Nolan and Jonathan Nolan" (score 0.9167 -> Q13417189).
- `"Who directed Schindlers List?"` -> Steven Spielberg.
- `"Who directed Forrst Gump?"` -> Robert Zemeckis.
- Safe failure: `"Who directed 'Qwzxv Plorbnik Unfilmable'?"` -> `no_entity()` (golden case `unknown-title`).

**Expected behaviour.** Article-stripped label families are matched first; a fuzzy match is accepted only when the best match is unique with enough separation; unmatched typos produce the `no_entity()` sentence.

**Decision nodes (resolved).**

- Q7: unique best match only at the 0.85 cutoff (raw labels).
- Q10: rank within an article-stripped family: films first, then graph degree. Bare "Godfather" and "Godfahter" resolve to The Godfather.
- Q11: for candidate labels of at most 6 characters, a unique best match at score >= 0.80 with a >= 0.05 gap to the second best is accepted ("Jazws" -> Jaws).
- Golden-path check: no golden case depends on bare "Godfather" -> Q5576354 (`grep godfather evals/stage2_factual.jsonl`).

**Dataset plan (S5).** 50+ cases: >= 10 distinct target entities; 30+ mapped-typo cases (expected = target answers; forbidden = the wrong-link answer, e.g. "Lal and Siddique"); 15+ safe-failure typo cases; 5+ controls that are not typos.

---

## T5 - Partial entity value specification

**Definition.** The mention gives only the core name of a title ("handmaiden" for "The Handmaiden", "matrix" for "The Matrix"), usually lowercase, with the article dropped.
Unique core-name mapping resolves to the full title; an ambiguous core name (several distinct titles) triggers the clarification reply.

**Attacked boundary.** B2 (Phase 1 -> 2): exact label lookup and the fuzzy pass both fail on the partial string.

**Breaking phase.** Phase 2: "handmaiden" vs "the handmaiden" scores 0.714, and "matrix" vs "the matrix" scores 0.6 - both below the 0.85 cutoff; exact lookup finds nothing.

**Red cases (measured, `s3-probe.log`).**

- R1: `"Who wrote the screenplay for handmaiden?"` -> `no_entity` reply. Grounded: "The Handmaiden" Q20444585 is the only entity whose article-stripped label is "handmaiden"; golden case `official-handmaiden-screenplay` shows the expected value "Jeong Seo-kyeong and Park Chan-wook".
- R2: `"who directed matrix"` -> `no_entity` reply. Grounded: the label `the matrix` has 3 entities (Q83495, Q13014087, Q33140061) plus the separate title `the matrix reloaded` (Q189600) - genuinely ambiguous, so a clarification is the correct behaviour.

**Green cases (measured today or golden, must stay).**

- `"who directed the matrix"` -> "Lana Wachowski and Lelly Wechawsku" (exact label family; first film by degree).
- `"who directed the godfather"` -> Francis Ford Coppola (golden case `godfather-lowercase`).
- `"who directed titanic"` -> Jean Negulesco (golden note in `phases.md`: the only film labelled "Titanic" is the 1953 one; the partial rule must not change this).
- After normalisation: R1 -> "Jeong Seo-kyeong and Park Chan-wook"; R2 -> clarification (`no_entity()` sentence), forbidden: "The factual answer is" (no answer may be attempted).

**Expected behaviour.** Article-stripped core-name matching: unique -> full title; several distinct titles -> clarification via `no_entity()`.
Exact full-title behaviour is unchanged.

**Decision nodes (resolved).**

- Q2: unique match else clarify (clarification reuses the `no_entity()` sentence).
- Q10: family ranking applies after a unique family is resolved.

**Dataset plan (S5).** 50+ cases: >= 10 distinct target titles; 30+ unique-partial cases (expected = full-title answers; forbidden = a neighbouring title's answer); 15+ ambiguous-partial cases (expected = clarification; forbidden = "The factual answer is").

---

## Cross-type checks

1. Masking invariant (Q8) is tested by T1 G3 and T2 G3.
2. Forbidden strings must be chosen so they cannot appear incidentally in the expected reply; S5 verifies every forbidden string against the harness reply before a case is accepted (example trap: "Up" appears inside the word "put" in the `no_entity()` sentence).
3. All five types keep the golden-stage2 and golden-stage1 files untouched; behavior changes are checked with a full eval run after every fix batch (S8).
