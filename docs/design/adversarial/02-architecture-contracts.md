# S2 - Architecture and phase-boundary contracts (grounded)

State: S2.
Every intermediate value below is a real value from `docs/design/adversarial/eval/s2-trace-examples.log`, produced by `scripts/adversarial/capture_traces.py`.
Baseline numbers come from `docs/design/adversarial/eval/baseline-stage1.log` and `baseline-stage2.log`.

## 1. The six pipeline phases mapped to code symbols

| # | Phase | Code symbol(s) | Input shape | Output shape | Hidden assumption |
|---|---|---|---|---|---|
| 1 | Entity recognition | `Parser._find_entity` (`agent/parser.py` lines 100-147): quoted-label pass (line 102), capitalised-span pass (107-125), lower-case one-word film fallback (127-132), fuzzy pass (134-146, cutoff 0.85) | raw question string | `(start, end)` char span plus candidate QID list | quotes or capitalisation carry the mention; `\w` tokens are the right word boundaries |
| 2 | Entity linking | `Parser._rank` (lines 165-171) plus `Lexicon.lbl2ent` (`agent/lexicon.py` lines 20-30) | span plus candidates | ranked QID list: films first, then graph degree | the first ranked candidate is the intended entity; label collisions are rare |
| 3 | Relation detection | `Parser._find_predicates` (lines 95-98) with `phrase_pattern` (58-59); kind regexes `HOW_MANY`, `EARLIEST`, `LATEST` (27-29, applied 73-79); direction choice in `parse` (84-91) | question text with the entity span blanked | list of predicate IRIs, `kind` in {lookup, count, earliest, latest}, `direction` in {out, in} | the remaining words hold the relation phrase; relation words never interact with negation or quantifiers |
| 4 | Query construction | `FactualHandler.handle` dispatch (`agent/handlers/factual.py` lines 32-37) plus `sparql_builder.lookup / count / superlative / has_facts` | `Question` fields (entity, predicate, direction, kind) | SPARQL string | the predicate and direction fill the template correctly; templates need no negation or complement branch |
| 5 | Validation | `has_facts` ASK checks in `Parser.parse` (lines 86-88); execution and row typing in `FactualHandler.handle` (lines 39-47): `rows[0][0]` for count, `min()` for dates, set of labels, empty set -> `no_facts` | SPARQL string plus raw rows | filtered, typed values or an error label | the ASK gate and the final query agree on direction; a count row exists; answer rows are `(value, label)` pairs |
| 6 | Answer generation | `nlg.format_term`, `join_and`, `answer`, `no_entity`, `no_relation`, `no_facts` (`agent/nlg.py`); values sorted casefold in `factual.py` line 48 | list of formatted strings | reply text | formatting preserves the exact substrings the eval checks; unlabelled IRIs are safe to drop (line 45) |

## 2. The seven boundary contracts

### B1 source -> Phase 1 (recognition)

- Sender assumption: the question is well-formed English.
- Receiver assumption: tokens, quotes, and casing carry the entity mention.
- Real example: `"who directed don't look up"` -> `span=(24, 26) candidates=['Q174811']` (the span covers only "up").
- Real example: `"hello"` -> `span=(0, 0) candidates=[]` -> `error='no_entity'`.
- Attacks: T2 (title inside title), T3 (missing or partial quotes), formatting noise; S4 list.

### B2 Phase 1 -> Phase 2 (linking)

- Sender assumption: the recognised mention is the intended entity.
- Receiver assumption: the mention maps to exactly one right node, or the failure is detectable.
- Real example: `"Who directed 'Inception'?"` -> `candidates=['Q25188', 'Q54888270', 'Q3797611']`; `_rank` picks `Q25188` only because films rank first.
- Real example (red): `"Who directed Godfahter?"` -> `candidates=['Q5576354']` (wrong entity, no detectable failure) -> reply "Lal and Siddique".
- Attacks: T4 (fuzzy links to a wrong but confident node), T5 (no node exists: `handmaiden` -> `[]`), ambiguity.

### B3 Phase 2 -> Phase 3 (relation)

- Sender assumption: the linked entity is correct.
- Receiver assumption: the remaining words carry the relation phrase.
- Real example: `"Who directed 'Inception'?"` -> `rest_after_span="Who directed ' '?"` -> `predicates=['http://www.wikidata.org/prop/direct/P57']`.
- Real example (red): `"Which movies did Christopher Nolan not direct?"` -> same `P57` detection; the word "not" is invisible to this phase and to direction choice (`direction='in'`).
- Attacks: T1 (negation dropped), relation words inside titles, nominalisations; S4 list.

### B4 Phase 3 -> Phase 4 (template fill)

- Sender assumption: the relation map is complete.
- Receiver assumption: the predicate and direction fill the template correctly.
- Real example: `"How many films did Christopher Nolan direct?"` -> `kind='count'`, `direction='in'` -> `SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x <...P57> <...Q25191> . ?x wdt:P31 wd:Q11424 }` -> reply "The factual answer is: 11".
- Real example: `"How tall is 'Inception'?"` -> `error='no_relation'` -> "I found Inception, but I'm not sure what you'd like to know..."
- Attacks: T1 (needs a complement template that does not exist), unknown relations, superlative detection on relation words ("first" inside a title).

### B5 Phase 4 -> Phase 5 (execution and typing)

- Sender assumption: the query is valid SPARQL.
- Receiver assumption: the rows have the expected type and shape.
- Real example: `has_facts(entity, P57, out/in)` ASK gates precede every template in `parse` lines 86-88.
- Real example (red): `"Who directed 'Don't Look Up'?"` -> entity resolves to `Q28008305` ("Don") -> ASK says no facts -> reply "Sorry, my knowledge graph has no information about the director of Don." (a confident wrong answer about a fragment).
- Attacks: empty results for a fragment entity (T2), count rows assumption, truncation at `max_fetch_rows` (10,000), query timeout.

### B6 Phase 5 -> Phase 6 (formatting)

- Sender assumption: the result set is the answer set.
- Receiver assumption: formatting preserves the values the eval checks.
- Real example: `"When did the movie 'Manchester by the Sea' come out?"` -> row value `2016-01-23` -> reply "The factual answer is: 2016-01-23".
- Real example: date literals with time parts exist ("1920-03-05T00:00:00"); `format_term` strips only the `T00:00:00Z` suffix.
- Attacks: date shapes, sorted-join behaviour, unlabelled IRIs dropped silently.

### B7 Phase 6 -> output (eval contract)

- Sender assumption: the answer is complete and safe.
- Receiver assumption: the reply satisfies the expected and forbidden strings, case-insensitive (`agent/eval.py` lines 19-22).
- Real example: `greeting` -> expected `['not sure']` matches "I'm not sure which movie or person you mean...".
- Real example (red for T2): `"who directed don't look up"` -> "The factual answer is: Bob Peterson and Pete Docter" (answer for "Up"; a T2 case must forbid them).

## 3. Baseline eval (recorded, reproducible)

```bash
cd /Users/diekgbbtt/.local/share/opencode/worktree/c6b606/fix/adversarial-normalization
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl   # -> 9/9 passed, exit 0
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl  # -> 508/508 passed, exit 0
```

Saved outputs: `docs/design/adversarial/eval/baseline-stage1.log` ("9/9 passed. Latency: median 0.00 s, max 1.07 s"), `baseline-stage2.log` ("508/508 passed. Latency: median 0.00 s, max 0.11 s").
Stage 2 baseline for no-regression checks: **508/508**.

## 4. Trace capture command (reproduce)

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_traces.py \
  2>&1 | tee docs/design/adversarial/eval/s2-trace-examples.log
```

## 5. Notes for the pre-processing seam (from the mapping above)

1. The natural seam for `agent/preprocess.py` is between B1 and B2: raw text in, normalised text out, before `FactualHandler` builds the `Parser`.
   `FactualHandler.handle` line 21 (`self.parser.parse(text)`) is the single call site to intercept.
2. Phase 3's negation blindness sits between B3 and B4 and needs a `Question`-level flag or a normalised negative form; the complement template is a phase-4 change (operator decision Q1).
3. B5's `has_facts` gate is why fragment entities produce "no facts about Don" replies instead of a recognition failure; T2 fixes must either widen the guard in phase 1 or catch the fragment in the pre-processing layer.
4. The 2 `no_entity` golden cases (`greeting`, `unknown-title`) fix the expected reply text for safe failures: the `nlg.no_entity()` sentence.
