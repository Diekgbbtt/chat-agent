# c-d1-counts - diagnosis

State: S7.
Cluster: c-d1-counts.
Dataset: `evals/adversarial/d1-count-class.jsonl` (63 cases).
Baseline: 6/63 passed, 57 failures.
Fix bar: pass rate >= 0.8, so at least 51/63 cases must pass.

## Red repro

The capture script produced the evidence with this command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Section `## c-d1-counts` of `docs/design/adversarial/eval/s7-repros.log` holds three repros (lines 236-269).
Observed output per repro:

- `d1-count-class-001` (`How many awards did 'Inception' win?`): `span=(21, 30) candidates=['Q25188', 'Q54888270', 'Q3797611']`; `predicates=['...P166']`; `direction='out'`; `kind='count'`.
  The SPARQL is `SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <...Q25188> <...P166> ?x . ?x wdt:P31 wd:Q11424 }`.
  The reply is `The factual answer is: 0` (s7-repros.log lines 238-247).
- `d1-count-class-002` (`How many cast members does 'Inception' have?`): entity Q25188, `predicates=['...P161']`, `direction='out'`.
  The same film-type filter appears; the reply is `The factual answer is: 0` (lines 249-258).
- `d1-count-class-036` (`How many countries of origin does 'The Handmaiden' have?`): entity Q20444585, `predicates=['...P495']`, `direction='out'`.
  The same film-type filter appears; the reply is `The factual answer is: 0` (lines 260-269).

Every repro appends `?x wdt:P31 wd:Q11424` to the count pattern.
The counted `?x` is an award, a cast member or a country in these repros.
None of those objects is a film.

### Probe 1 (count with and without the film-type filter)

Command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
from agent.config import load_settings
from agent.kg import KnowledgeGraph
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
WD = "http://www.wikidata.org/entity/"
def cnt(e, p, filt):
    q = f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ <{WD}{e}> <http://www.wikidata.org/prop/direct/{p}> ?x "
    q += (". ?x wdt:P31 wd:Q11424 }" if filt else "}")
    return kg.query(q).rows[0][0].value
cases = [("001 Q25188 P166 awards Inception", "Q25188", "P166"),
         ("002 Q25188 P161 cast Inception", "Q25188", "P161"),
         ("003 Q25188 P136 genres Inception", "Q25188", "P136"),
         ("004 Q25188 P495 countries Inception", "Q25188", "P495"),
         ("036 Q20444585 P495 countries Handmaiden", "Q20444585", "P495"),
         ("048 Q25191 P166 awards Nolan", "Q25191", "P166"),
         ("058 Q51114 P57 films John Ford", "Q51114", "P57")]
for name, e, p in cases:
    print(f"{name}: with_filter={cnt(e,p,True)}  raw={cnt(e,p,False)}")
def cnt_in(e, p, filt):
    q = f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ ?x <http://www.wikidata.org/prop/direct/{p}> <{WD}{e}>"
    q += (" . ?x wdt:P31 wd:Q11424 }" if filt else "}")
    return kg.query(q).rows[0][0].value
for name, e in [("059 Hitchcock Q7374", "Q7374"), ("063 Cukor Q56014", "Q56014")]:
    print(f"{name} P57 in: with_filter={cnt_in(e,'P57',True)}  raw={cnt_in(e,'P57',False)}")
PY
```

Output:

```
001 Q25188 P166 awards Inception: with_filter=0  raw=6
002 Q25188 P161 cast Inception: with_filter=0  raw=21
003 Q25188 P136 genres Inception: with_filter=0  raw=8
004 Q25188 P495 countries Inception: with_filter=0  raw=2
036 Q20444585 P495 countries Handmaiden: with_filter=0  raw=1
048 Q25191 P166 awards Nolan: with_filter=0  raw=10
058 Q51114 P57 films John Ford: with_filter=0  raw=0
059 Hitchcock Q7374 P57 in: with_filter=41  raw=43
063 Cukor Q56014 P57 in: with_filter=32  raw=33
```

The `058` line used direction `out`; the real control resolves direction `in` and passes in the baseline.
The `raw` column matches the dataset `expected` values exactly (6, 21, 8, 2, 1, 10).
The `with_filter` column is 0 for every non-film relation.
The two P57 controls show the opposite: `with_filter` matches the expected 41 and 32, `raw` does not.
So the filter is correct only for film-count questions and fatal for every other count.

### Probe 2 (person-side count trace)

Command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.cli --debug "How many awards has Christopher Nolan won?"
```

Output:

```
  [handler] factual
  [question] Question(text='How many awards has Christopher Nolan won?', entity='Q25191', predicate='http://www.wikidata.org/prop/direct/P166', direction='out', kind='count', error=None)
  [sparql] SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { <http://www.wikidata.org/entity/Q25191> <http://www.wikidata.org/prop/direct/P166> ?x . ?x wdt:P31 wd:Q11424 }
The factual answer is: 0
```

The person case has the same shape as the film cases.
Direction is `out`, predicate is `P166`, and the filter is present.
The reply is the forbidden `0`, although the true count is 10 (probe 1).

### Probe 3 (golden count cases under a filter-free count)

Command:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
import json
from agent.config import load_settings
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.parser import Parser
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
lex = Lexicon(kg)
p = Parser(kg, lex)
WD = "http://www.wikidata.org/entity/"
def cnt(e, pred, dirn, filt):
    if dirn == "in":
        q = f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ ?x <{pred}> <{WD}{e}>"
    else:
        q = f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ <{WD}{e}> <{pred}> ?x"
    q += (" . ?x wdt:P31 wd:Q11424 }" if filt else "}")
    return kg.query(q).rows[0][0].value
for line in open("evals/stage2_factual.jsonl", encoding="utf-8"):
    c = json.loads(line)
    if c["id"].startswith("ext-count-directed") or c["id"] == "sciamma-count":
        q = p.parse(c["input"])
        wf = cnt(q.entity, q.predicate, q.direction, True)
        raw = cnt(q.entity, q.predicate, q.direction, False)
        flag = "BREAKS" if str(raw) != c["expected"][0].split(": ")[1] else "ok"
        print(f"{c['id']}: entity={q.entity} dir={q.direction} filtered={wf} raw={raw} -> {flag}")
PY
```

Output (13 Stage 2 count cases):

```
sciamma-count: entity=Q461350 dir=in filtered=4 raw=4 -> ok
ext-count-directed-how-many-movies-has-palle-kj-rulff-schmidt-direc: entity=Q7127800 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-norbert-ter-hall-directed: entity=Q2110132 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-luca-bercovici-directed: entity=Q1872950 dir=in filtered=1 raw=2 -> BREAKS
ext-count-directed-how-many-movies-has-anders-jacobsson-directed: entity=Q106376315 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-toni-bosturd-directed: entity=Q18649797 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-margreth-olin-directed: entity=Q3430900 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-meruely-revos-directed: entity=Q5997364 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-abel-gance-directed: entity=Q313572 dir=in filtered=1 raw=2 -> BREAKS
ext-count-directed-how-many-movies-has-juhn-wiyne-directed: entity=Q40531 dir=in filtered=5 raw=5 -> ok
ext-count-directed-how-many-movies-has-marek-kanievska-directed: entity=Q3290385 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-anthony-quinn-directed: entity=Q83484 dir=in filtered=1 raw=1 -> ok
ext-count-directed-how-many-movies-has-mati-diop-directed: entity=Q3299073 dir=in filtered=2 raw=2 -> ok
```

Two golden cases break if the filter is simply deleted: Luca Bercovici (Q1872950) and Abel Gance (Q313572).
Those two people have a second `P57` value that is not a film.
The fix must keep the film filter for film-count questions.

## Failure shapes

The baseline report (`eval/iter0/d1-count-class-baseline.md`) records one shape, `wrong count: 0`, with 57 cases.
Every failing reply is `The factual answer is: 0`.
These sub-shapes split the 57 by asked relation and subject side; they sum to 57:

| Sub-shape | Count | Example | Case ids |
|---|---|---|---|
| film subject, award count (`P166`, direction `out`) | 11 | d1-count-class-001 | 001, 005, 009, 013, 017, 021, 025, 029, 033, 037, 041 |
| film subject, cast count (`P161`, direction `out`) | 12 | d1-count-class-002 | 002, 006, 010, 014, 018, 022, 026, 030, 034, 038, 042, 045 |
| film subject, genre count (`P136`, direction `out`) | 12 | d1-count-class-003 | 003, 007, 011, 015, 019, 023, 027, 031, 035, 039, 043, 046 |
| film subject, country count (`P495`, direction `out`) | 12 | d1-count-class-004 | 004, 008, 012, 016, 020, 024, 028, 032, 036, 040, 044, 047 |
| person subject, award count (`P166`, direction `out`) | 10 | d1-count-class-048 | 048-057 |

Rollup: 47 film-subject cases plus 10 person-subject cases.
All 57 have direction `out`; all 57 carry the film-type filter.
The 6 passing cases (058-063) are the only direction-`in` counts.

## Ranked hypotheses

**H1 (primary): `sparql_builder.count` always adds the film-type filter.**
Test: probe 1. The filtered count is 0 for six non-film relations; the raw count matches the dataset.
The filter literal sits in one line (`agent/sparql_builder.py:33`).
Verdict: confirmed.

**H2: entity recognition or linking picks the wrong entity.**
Test: the repro log shows the right QIDs (Q25188 Inception, Q20444585 The Handmaiden).
Probe 1 then returns the expected counts for those QIDs.
Verdict: rejected.

**H3: relation detection maps the question to the wrong predicate or direction.**
Test: the repro log maps awards to P166, cast to P161 and countries to P495.
Probe 1 runs those exact predicates and returns the expected counts.
Probe 2 records `direction='out'` for the person case, which is the correct side.
Verdict: rejected.

**H4: the handler types or truncates the count row.**
Test: `FactualHandler.handle` returns `rows[0][0].value` for counts (`agent/handlers/factual.py:41-42`).
Probe 1 bypasses the handler and gets the same 0 with the filter, and the true count without it.
Verdict: rejected.

**H5: answer generation formats the value wrongly.**
Test: `nlg.answer` joins the collected strings (`agent/nlg.py:34-35`).
The value it formats is the real query result, which is 0 while the filter is present.
Verdict: rejected.

**H6: deleting the film filter is a safe global fix.**
Test: probe 3. Two golden count cases break, and probe 1 breaks two P57 controls.
Verdict: rejected.

## Root cause

Primary root cause: the count template hard-codes a film-type filter on the counted object.

Pinned phase: phase 4 (query construction).
Pinned boundary: B4 (Phase 3 -> Phase 4, template fill).

`sparql_builder.count` builds the pattern and appends `?x wdt:P31 wd:Q11424` unconditionally (`agent/sparql_builder.py:32-33`).
`FactualHandler.handle` calls that builder for every `kind == "count"` question (`agent/handlers/factual.py:32-33`).
The parser sets `kind = "count"` whenever `HOW_MANY` matches (`agent/parser.py:29`, `agent/parser.py:73-74`).
So the filter runs for awards, cast, genres and countries, whose objects are not films.
`COUNT(DISTINCT ?x)` then counts zero rows, and the handler returns that zero (`agent/handlers/factual.py:41-42`).
The zero is a well-formed count row, so no later phase flags it.
That is why B5 also stays silent: the row has the expected type and shape.
The 6 controls survive because they are direction-`in` P57 counts; their `?x` is a film.
Probe 1 proves both directions of the effect.
Probe 3 proves the filter cannot simply be removed.

## Decision constraints

- Q3 (3a): the normalisation seam is `agent/preprocess.py`, before `Parser.parse`.
  Edits to `parser.py` or `nlg.py` need a proven need.
  This cluster needs a phase-4 query-template edit, which is outside that text seam.
- D1 dataset rule: counts are raw `COUNT(DISTINCT ?x)` over the asked relation on the asked film.
  The film-type filter applies only to film-count questions about people.
  The 6 P57 controls pass and must stay.
- Q9: relation domains define the universes; films are `wdt:P31 wd:Q11424`.
  Counting stays on the subject side of the asked film.
- Fix bar: at least 51/63 cases must pass.
- No-regression bar: `evals/stage1_sparql.jsonl` stays 9/9 and `evals/stage2_factual.jsonl` stays 508/508.

## Suggested fix

The defect is a query-template defect, not a text-normalisation defect.
The `agent/preprocess.py` seam rewrites text before `Parser.parse`.
It cannot see or change the SPARQL filter.
So the fix belongs in phase 4, at the count template.

1. `agent/sparql_builder.py:32-33`: make the film filter conditional.
   Give `count` a `film_only` parameter that defaults to `False`.
   Append `?x wdt:P31 wd:Q11424` only when `film_only` is true.
   A raw count then omits the filter, which fixes all 57 cases.
2. Decide `film_only` from the counted object class, not from the surface words.
   Use a small module constant, for example `FILM_VALUE_PREDICATES = {P57, P58}`.
   Set `film_only` when `direction == "in"` and the predicate is in that set.
   P57 covers the 6 controls; P58 is the same film side.
   Keep the default raw, so every non-film relation counts its real objects.
3. Keep the handler call site simple (`agent/handlers/factual.py:32-33`).
   Let `count` itself apply the predicate-and-direction rule.
   Then the handler body does not change.
4. Optionally raise `film_only` at the call site instead.
   That needs a one-argument change in `factual.py`, which is a justified handler edit.

Justification for edits beyond the preprocess seam:

- The root cause lives in the count template (`agent/sparql_builder.py:33`).
  Text surgery at B1-B2 cannot remove a SPARQL type filter.
  Section 5 of `02-architecture-contracts.md` names `FactualHandler.handle` line 21 as the preprocess intercept point; this cluster does not pass through that defect.
- Q3 (3a) allows a non-preprocess edit when a diagnosis proves the need.
  This diagnosis proves it with probes 1 and 3.
- No `parser.py`, `lexicon.py` or `nlg.py` edit is needed.
  `Lexicon.is_film` already answers the class question if reviewers prefer a lexicon-based check (`agent/lexicon.py:43-44`), but predicate metadata is enough here.

## Regression seam

Run the cluster and expect at least 51/63, with 63/63 as the target:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/d1-count-class.jsonl
```

Run the no-regression suites and expect 9/9 and 508/508:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl
```

Cases that prove the fix (expected values from probe 1):

- `d1-count-class-001` (film P166): must answer `6`, not `0`.
- `d1-count-class-002` (film P161): must answer `21`.
- `d1-count-class-003` (film P136): must answer `8`.
- `d1-count-class-004` (film P495): must answer `2`.
- `d1-count-class-036` (film P495, The Handmaiden): must answer `1`.
- `d1-count-class-048` (person P166, Nolan): must answer `10`.
- `d1-count-class-058` to `d1-count-class-063` (six P57 controls, green today): must stay green.

Golden cases at risk:

- The 13 Stage 2 count cases: `sciamma-count` and the 12 `ext-count-directed` cases.
  Probe 3 shows `luca-bercovici` (Q1872950) and `abel-gance` (Q313572) break under a filter-free count.
- `evals/stage1_sparql.jsonl` `sciamma-count` embeds the film filter in its SPARQL (line 2).
- All 63 cluster cases and all 508 Stage 2 cases run through the changed template.

## Risks and open questions

- Predicate whitelist scope: probe 3 only covers P57.
  P58 (screenwriter) and other film-credit properties are untested.
  Confirm the whitelist before release, or derive the film side from relation metadata.
- Contract wording: the D1 rule says counts are raw, yet the 6 controls need the filter.
  The rule and the controls agree only if "film-count question" is a recognised class.
  Pin that definition in `03-known-types-spec.md` if it is still open.
- Direction edge: a `P166` direction-`in` count ("who won this award") counts people.
  The predicate-and-direction rule must not add the filter there.
  The proposed rule keeps the filter off because the predicate is not in the set.
- Preprocess seam: the operator may prefer all changes at `agent/preprocess.py` (Q3).
  This cluster cannot meet that preference, because the filter lives in the template.
  The fix needs an explicit Q3 exception; record the decision.
- Zero as a silent value: the handler prints a count of 0 as fact (`agent/nlg.py:34-35`).
  A real zero and a filter-induced zero look the same.
  A future guard could distinguish "no rows" from "count is zero"; it is out of scope here.
