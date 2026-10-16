# c-t1-negation - diagnosis

State: S7.
Cluster: c-t1-negation.
Dataset: `evals/adversarial/t1-negation.jsonl` (64 cases).
Baseline: 8/64 passed, 56 failures.
Fix bar: pass rate >= 0.8, so at least 52/64 cases must pass.

## Red repro

The capture script produced the evidence with this command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Section `## c-t1-negation` of `docs/design/adversarial/eval/s7-repros.log` holds four repros (lines 3-47).
Observed output per repro:

- `t1-negation-001` (film side, P57): `span=(17, 26) candidates=['Q51114']`; `rest_after_span='Which movies did   not direct?'`; `predicates=['...P57']`; `direction='in'`.
  The query is the positive lookup `?x P57 Q51114`; the reply is John Ford's own filmography (s7-repros.log lines 5-14).
- `t1-negation-029` (film side, P58): the same shape; the reply is Ben Hecht's own films (lines 16-25).
- `t1-negation-039` (person side, P57): the query is `<Q25188> P57 ?x`; the reply is `The factual answer is: Christopher Nolan` (lines 27-36).
- `t1-negation-057` (masking control): `Who directed 'North by Northwest'?` resolves and answers correctly (lines 38-47).

The `rest_after_span` still holds the word "not" in the three red repros.
No trace step records a negation flag.

### Probe 1 (film-side complement shape)

Command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'EOF'
from agent.config import load_settings
from agent.kg import KnowledgeGraph
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
q = ("SELECT ?x ?label WHERE { ?x wdt:P31 wd:Q11424 . "
     "FILTER NOT EXISTS { ?x wdt:P57 <http://www.wikidata.org/entity/Q51114> } "
     "OPTIONAL { ?x rdfs:label ?label } }")
res = kg.query(q)
labels = [(r[1].value if r[1] else None) for r in res.rows]
print("row_count:", len(res.rows), "truncated:", res.truncated)
print("first 8 labels:", labels[:8])
for tgt in ["The BFG", "The Pirates! In an Adventure with Scientists!"]:
    print(f"  index of {tgt!r}:", labels.index(tgt) if tgt in labels else "ABSENT")
pos = kg.query("SELECT DISTINCT ?x ?label WHERE { ?x <http://www.wikidata.org/prop/direct/P57> "
               "<http://www.wikidata.org/entity/Q51114> . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200")
print("positive-set row_count (lookup LIMIT 200):", len(pos.rows))
EOF
```

Output:

```
PROBE-1 film complement query (t1-negation-001, entity Q51114 = John Ford)
row_count: 10000 truncated: True
first 8 labels: ['The BFG', 'The Pirates! In an Adventure with Scientists!', 'Good Morning, Vietnam', 'Gattaca', "Mary Shelley's Frankenstein", 'Johnny Belinda', "My Best Friend's Wedding", 'Loaded Guns']
  index of 'The BFG': 0
  index of 'The Pirates! In an Adventure with Scientists!': 1
positive-set row_count (lookup LIMIT 200): 44
```

The film complement query returns the two expected labels at index 0 and index 1.
The reply truncates deterministically at the 10,000-row cap (`agent/config.py:101`).

### Probe 2 (person-side complement shape)

Command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'EOF'
from agent.config import load_settings
from agent.kg import KnowledgeGraph
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
q = ("SELECT DISTINCT ?x ?label WHERE { ?f wdt:P57 ?x . "
     "FILTER NOT EXISTS { <http://www.wikidata.org/entity/Q25188> wdt:P57 ?x } "
     "OPTIONAL { ?x rdfs:label ?label } }")
res = kg.query(q)
labels = [(r[1].value if r[1] else None) for r in res.rows]
print("row_count:", len(res.rows), "truncated:", res.truncated)
print("first 8 labels:", labels[:8])
for tgt in ["Alfred Hitchcock", "Steven Spielberg"]:
    print(f"  index of {tgt!r}:", labels.index(tgt) if tgt in labels else "ABSENT")
EOF
```

Output:

```
PROBE-2 person complement query (t1-negation-039, entity Q25188 = Inception)
row_count: 6108 truncated: False
first 8 labels: ['Palle Kjærulff-Schmidt', 'Norbert ter Hall', None, 'Luca Bercovici', 'Anders Jacobsson', 'Toni Bosturd', 'Margreth Olin', 'Meruely Revos']
  index of 'Alfred Hitchcock': 4022
  index of 'Steven Spielberg': 1192
```

The person complement returns 6,108 directors.
Both expected labels are inside the returned rows, but they sit past index 200.
The `lookup` template's `LIMIT 200` (agent/sparql_builder.py:10,29) would drop them.

### Probe 3 (combined negation and masking)

Command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.cli --debug "Who did not direct 'No Country for Old Men'?"
```

Output:

```
  [handler] factual
  [question] Question(text="Who did not direct 'No Country for Old Men'?", entity='Q183081', predicate='http://www.wikidata.org/prop/direct/P57', direction='out', kind='lookup', error=None)
  [sparql] SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q183081> <http://www.wikidata.org/prop/direct/P57> ?x . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200
The factual answer is: Ethan Coen and Joel Coen
```

The quoted pass masks the title "No Country for Old Men" and links Q183081.
The word "not" survives in `rest` but the query is still the positive P57 lookup.

## Failure shapes

The baseline report (`eval/iter0/t1-negation-baseline.md`) splits the 56 failures by reply shape.
These counts sum to 56:

| Sub-shape | Count | Example | Case ids |
|---|---|---|---|
| wrong answer: expected value absent | 28 | t1-negation-001 | 001-016, 023-034 |
| trap value returned (`Indiana Jones and the Kingdom of the Crystal Skull`) | 3 | t1-negation-017 | 017-019 |
| trap value returned (`It Should Happen to You`) | 3 | t1-negation-020 | 020-022 |
| trap value returned (`Colombiana`) | 2 | t1-negation-035 | 035-036 |
| trap value returned (`Men Without Women`) | 2 | t1-negation-037 | 037-038 |
| trap value returned (`Christopher Nolan`) | 4 | t1-negation-039 | 039-042 |
| trap value returned (`Francis Ford Coppola`) | 4 | t1-negation-043 | 043-046 |
| trap value returned (`Lana Wachowski`) | 4 | t1-negation-047 | 047-050 |
| trap value returned (`Steven Spielberg`) | 2 | t1-negation-051 | 051-052 |
| trap value returned (`Park Chan-wook`) | 2 | t1-negation-053 | 053-054 |
| trap value returned (`Ethan Coen`) | 1 | t1-negation-063 | 063 |
| trap value returned (`Roger Michell`) | 1 | t1-negation-064 | 064 |

Rollup by the clause in `07-cluster-index.md`:

- Film-side complement answered with the positive filmography: 38 (28 P57 + 10 P58).
- Person-side complement answered with the film's actual director: 18 (16 person-side + 2 combined).

The 28/28 split between "expected value absent" and "trap value returned" is a presentation artifact.
`agent/eval.py:43` logs only `reply[:300]`, and `scripts/adversarial/cluster_baseline.py:56-60` labels a failure "trap" only when a forbidden string appears in that prefix.
All 56 replies are the positive set.
The split records where the first forbidden string falls in the truncated log line.

## Ranked hypotheses

**H1 (primary): phase 3 drops the negation word.**
Test: the repro log shows "not" inside `rest_after_span` (lines 10, 21, 32), yet `Question` has no negation field (`agent/parser.py:32-39`).
`Parser.parse` sets only entity, predicate, direction and kind (`agent/parser.py:63-93`).
Verdict: confirmed.

**H2: phase 4 has no complement template.**
Test: code reading. `agent/sparql_builder.py` defines only `_triple`, `has_facts`, `degree`, `lookup`, `count` and `superlative` (lines 13-41).
A grep for "complement" or "FILTER NOT EXISTS" over `agent/` finds nothing.
Verdict: confirmed.

**H3: the preprocess seam does not exist.**
Test: `ls agent/` has no `preprocess.py`.
A grep for "preprocess" or "normalise" over the repo finds no module.
Verdict: confirmed.

**H4: the Q8 masking invariant already holds for quoted mentions.**
Test: the 8 controls (t1-negation-055..062) pass in the baseline.
Repro 057 is green, and probe 3 masks "No Country for Old Men" (entity Q183081).
Verdict: confirmed.

**H5: the complement query must reuse the exact grounding shape and must not keep `LIMIT 200`.**
Test: probe 1 returns the film expected labels at index 0 and 1.
Probe 2 returns the person expected labels at index 1192 and 4022, past a 200-row limit.
Verdict: confirmed.

**H6: the failures come from wrong entity linking.**
Test: the repro log and probe 3 show correct entities (Q51114 John Ford, Q183081 No Country for Old Men).
The replies are the correct positive answers, not another entity's answers.
Verdict: rejected.

## Root cause

Primary root cause: phase 3 relation detection drops the negation word, and phase 4 has no complement template.

Boundary: B3 (Phase 2 -> Phase 3, relation detection) is the drop point; B4 (Phase 3 -> Phase 4) lacks the complement template (`docs/design/adversarial/02-architecture-contracts.md` lines 36-50, `03-known-types-spec.md` line 26).

`Parser.parse` blanks the entity span into `rest` (`agent/parser.py:63`, `agent/parser.py:71`) and then calls `Parser._find_predicates` (`agent/parser.py:95-98`).
That method returns only relation IRIs matched by `phrase_pattern` (`agent/parser.py:59`).
`Question` carries no negation field (`agent/parser.py:32-39`), and `parse` never records one.
No negation regex exists beside `EARLIEST`, `LATEST` and `HOW_MANY` (`agent/parser.py:27-29`).
`FactualHandler.handle` then dispatches to `sb.lookup` (`agent/handlers/factual.py:32-37`), which fills only the positive triple (`agent/sparql_builder.py:27-29`).
`sparql_builder.py` defines no complement function (lines 13-41).
So every one of the 56 failing cases answers the positive set.

Evidence: the repro log keeps "not" in `rest_after_span` (line 10), and probes 1 and 2 show both complement shapes return the expected labels.

## Decision constraints

- Q1: a negation must always compute the complement, whatever its size.
  The fix needs a real complement query, not a refusal.
  The film complement truncates at `Settings.max_fetch_rows` = 10,000 (`agent/config.py:101`); probe 1 confirms the truncation.
- Q8: negation words inside an entity mention must never trigger the complement.
  Mask the mention span first.
  The 8 controls (055-062), the 2 combined cases (063-064) and 9 golden Stage 2 cases depend on this.
- Q9: complement universes are relation domains.
  Films are subjects with `wdt:P31 wd:Q11424`.
  The person side is objects of `wdt:P57`.
- Q3: normalisation lives at `agent/preprocess.py`.
  `parser.py` or `nlg.py` edits need a proven need.
- Dataset coupling: film-side expected labels were harvested with the complement query shape in `docs/design/adversarial/05-dataset-manifest.md` (10,000-row cap).
  The fix must reuse that shape.
  Probe 1 confirms the shape returns the expected labels at the front.

## Suggested fix

Preferred seam: add `agent/preprocess.py` and call it at the single parse call site.

1. `agent/preprocess.py` (new): expose a function that returns `(text, negated)`.
   It masks quoted entity spans first, then scans the unmasked text for one-level negation words.
   Use word boundaries over "not", "never", "no" and contractions such as "n't".
   Masking first satisfies Q8.
   The function never rewrites a masked mention.
2. `agent/handlers/factual.py:21`: call preprocess before `self.parser.parse(text)`.
   Add `trace.add("negation", negated)` so `--debug` shows the flag.
   Keep the parser call unchanged, so no `parser.py` edit is needed.
   The word "not" may stay in the text; the parser ignores it, as the repros show.
3. `agent/handlers/factual.py:32-37`: when `negated`, dispatch to a new complement builder instead of `sb.lookup`.
4. `agent/sparql_builder.py`: add `complement(entity, predicate, direction)` with the two exact grounding shapes.
   - `direction == "in"` (film side): `SELECT ?x ?label WHERE { ?x wdt:P31 wd:Q11424 . FILTER NOT EXISTS { ?x <pred> <WD/entity> } OPTIONAL { ?x rdfs:label ?label } }`.
   - `direction == "out"` (person side): `SELECT DISTINCT ?x ?label WHERE { ?f <pred> ?x . FILTER NOT EXISTS { <WD/entity> <pred> ?x } OPTIONAL { ?x rdfs:label ?label } }`.
   Do not add `LIMIT 200`.
   Keep the 10,000-row cap that `kg.query` applies.
   Both shapes match `grounding.check` in `evals/adversarial/t1-negation.jsonl` exactly.

Justification for edits beyond the preprocess seam:

- The `factual.py` dispatch and trace edits sit inside the seam.
  `02-architecture-contracts.md` section 5 note 1 names `FactualHandler.handle` line 21 as the single interception point.
- The `sparql_builder.py` edit is a phase-4 change.
  Q1 states that negation needs a complement template (`docs/design/adversarial/00-questions.md` line 110).
  No preprocess text surgery can change which query runs.
- No `parser.py`, `lexicon.py` or `nlg.py` edit is needed.
  The preferred design keeps the negation flag local to the handler.
  If reviewers want the flag on `Question` for trace honesty, that is a justified two-line `parser.py` edit at lines 32-39, not a requirement.

## Regression seam

Run the cluster and expect at least 52/64, with 64/64 as the target:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/t1-negation.jsonl
```

Run the no-regression suites and expect 9/9 and 508/508:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl
```

Cases that prove the fix:

- `t1-negation-001` (film P57): expected `The BFG` and `The Pirates! In an Adventure with Scientists!` must appear; forbidden `The Man Who Shot Liberty Valance` and `When Willie Comes Marching Home` must not.
- `t1-negation-029` (film P58): the complement must run over films.
- `t1-negation-039` (person P57): expected `Alfred Hitchcock` and `Steven Spielberg` must appear; forbidden `Christopher Nolan` must not.
- `t1-negation-057` (masking control, green today): must stay green.
- `t1-negation-063` and `t1-negation-064` (combined negation and masked title): must flip green.

Golden cases at risk:

- The 8 T1 masking controls, `t1-negation-055` to `t1-negation-062`.
- The 9 Stage 2 cases whose quoted titles hold negation words: `City That Never Sleeps` (6 cases) and `I'm Not There` (3 cases).
- All 508 Stage 2 cases now pass through the new preprocess call.

## Risks and open questions

- Reply size: the film complement returns 10,000 labels and the person complement returns 6,108.
  `nlg.answer` joins all values into one string.
  The dataset checks substrings only, but confirm the join stays inside the 25 s reply timeout (`agent/config.py:99`).
- Masking scope: preprocess masks quoted spans only.
  An unquoted negation-word mention would falsely trigger the complement.
  Every T1 case and every at-risk Stage 2 case quotes the title, so the dataset is safe.
  Q8's invariant is only partly enforced for unquoted mentions; record this as a known limit.
- Word "no": the in-scope forms are "not", "no" and "never".
  "no" can act as a determiner in other phrasings.
  A whole-word scan of the unmasked text is the minimal rule; confirm no Stage 2 phrasing breaks.
- Direction rule: the person-side universe is objects of `wdt:P57` (Q9).
  A person-side complement for a non-P57 relation is out of dataset scope.
- Truncation order: the film complement is order dependent because it truncates at 10,000.
  Probe 1 puts `The BFG` at index 0, so reuse of the exact shape is safe.
- Double negation is out of scope (Q8).
  Preprocess must not try to resolve it.
