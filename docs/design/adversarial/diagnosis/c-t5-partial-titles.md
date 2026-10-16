# c-t5-partial-titles - diagnosis

State: S7.
Cluster: `c-t5-partial-titles`.
Dataset: `evals/adversarial/t5-partial-titles.jsonl` (51 cases, 31 failures at baseline).
Baseline: 20/51 passed (39.2%).
Fix bar: pass rate >= 0.8, so at least 41/51 cases must pass.
Decision anchors: Q15, Q10, Q2 (and Q3 for the seam).

## Red repro

Repro log: `docs/design/adversarial/eval/s7-repros.log`, section `## c-t5-partials` (lines 178-232).
Capture command, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output for the `no_entity` repro (`t5-partial-titles-001`):

```
--- t5-partial-titles-001
input: 'who directed handmaiden?'
expected: ['Park Chan-wook']
forbidden: []
span=(0, 0) candidates=[]
rest_after_span=' who directed handmaiden?' predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text='who directed handmaiden?', entity=None, predicate=None, direction='out', kind='lookup', error='no_entity')
reply="I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"
```

Observed output for the `no_facts` repro (`t5-partial-titles-006`):

```
--- t5-partial-titles-006
input: "Who directed 'matrix'?"
expected: ['Lana Wachowski', 'Lelly Wechawsku']
forbidden: []
span=(14, 20) candidates=['Q44337']
rest_after_span="Who directed ' '?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text="Who directed 'matrix'?", entity='Q44337', predicate='...P57', direction='out', kind='lookup', error='no_facts')
reply='Sorry, my knowledge graph has no information about the director of matrix.'
```

Observed output for the wrong-title repro (`t5-partial-titles-035`):

```
--- t5-partial-titles-035
input: 'who directed usual suspects?'
expected: ['Bryan Singer']
forbidden: []
span=(19, 28) candidates=['Q1971726']
rest_after_span='who directed usual  ' predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Peter Yates'
```

Observed output for the trap repro (`t5-partial-titles-007`):

```
--- t5-partial-titles-007
input: 'who directed godfather?'
expected: ['Francis Ford Coppola']
forbidden: ['Lal and Siddique']
span=(13, 22) candidates=['Q5576354']
rest_after_span='who directed  ?' predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Lal and Siddique'
```

Observed output for the clarify repro (`t5-partial-titles-045`):

```
--- t5-partial-titles-045
input: 'Who directed twilight zone?'
expected: ["I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"]
forbidden: ['the factual answer is:']
span=(13, 21) candidates=['Q160071']
rest_after_span='Who directed   zone?' predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Catherine Hardwicke'
```

The baseline log `docs/design/adversarial/eval/iter0/t5-partial-titles.log` records the same 31 failures.

### Recorded probes

Probe 1, parser internals and lexicon membership over all 51 cases:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
import json, re, sys
from pathlib import Path
sys.path.insert(0, ".")
from agent.cli import load_agent
from agent.parser import STOPWORDS
agent = load_agent()
parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))
lex = parser.lex
lbl = lex.lbl2ent
# ... membership of crafted keys, then per-case span/candidates/lastresort ...
PY
```

Observed output (key lines):

```
'handmaiden'      -> None            'the handmaiden'   -> ['Q20444585']
'matrix'          -> ['Q44337']      'the matrix'       -> ['Q33140061', 'Q13014087', 'Q83495']
'godfather'       -> ['Q5576354']    'the godfather'    -> ['Q47703', 'Q3225260', 'Q1139696', 'Q243556']
'shawshank redemption' -> None       'the shawshank redemption' -> ['Q110239360', 'Q172241']
'usual suspects'  -> None            'the usual suspects' -> ['Q132351']
'twilight zone'   -> None            'the twilight zone' -> ['Q742103']
t5-partial-titles-001 'who directed handmaiden?'                    span=(0, 0)   cands=[]        expected=Q20444585
t5-partial-titles-004 'who directed matrix?'                        span=(0, 0)   cands=[]        expected=Q83495
t5-partial-titles-006 "Who directed 'matrix'?"                      span=(14, 20) cands=['Q44337'] expected=Q83495
t5-partial-titles-007 'who directed godfather?'                     span=(13, 22) cands=['Q5576354']
   lastresort=[('godfather', ['Q5576354'])]
t5-partial-titles-031 'who directed dark knight?'                   span=(13, 24) cands=['Q194023']
   labelmatches=[('lower', 2, 2, 'dark knight', ['Q194023'])]
t5-partial-titles-035 'who directed usual suspects?'                span=(19, 28) cands=['Q1971726']
t5-partial-titles-037 'who directed silence of the lambs?'          span=(13, 20) cands=['Q18811634']
   lastresort=[('silence', ['Q18811634'])]
t5-partial-titles-043 'who directed truman show?'                   span=(13, 19) cands=['Q21034423']
   lastresort=[('truman', ['Q21034423'])]
t5-partial-titles-045 'Who directed twilight zone?'                 span=(13, 21) cands=['Q160071']
   lastresort=[('twilight', ['Q160071'])]
```

Probe 2, entity facts, family scan, and fuzzy near matches:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, ".")
from rapidfuzz import process; from rapidfuzz.distance import OSA
from agent.cli import load_agent
# ... show(label, is_film, types, P57, P58) for 24 QIDs; scan labels for cores; fuzzy extractOne ...
PY
```

Observed output (key lines):

```
Q44337:   label='matrix'   is_film=False     Q194023: label='Dark Knight'  is_film=False
Q486748:  label='pianist'  is_film=False     Q742103: label='The Twilight Zone' is_film=False
Q5576354: label='Godfather' is_film=True     P57=[Siddique, Lal]
Q1971726: label='Suspect'   is_film=True     P57=[Peter Yates]
Q18811634:label='Silence'   is_film=True     P57=[Martin Scorsese]
Q21034423:label='Truman'    is_film=True     P57=[Cesc Gay]
Q160071:  label='Twilight'  is_film=True     P57=[Catherine Hardwicke]
Q184768:  label='The Godfather Part II' is_film=True  P57=[Francis Ford Coppola]
'suspects'  -> ('suspect', 0.875, ...)   ids=['Q1971726']
'shawshank redemption' -> None
'for shawshank redemption' -> ('the shawshank redemption', 0.875, ...) ids=['Q110239360', 'Q172241']
'twilight' -> ('twilight', 1.0, ...)     ids=['Q189378', 'Q160071']
```

Probe 3, the Q15 family rule over the partial mentions:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
# build an article-stripped family index over label keys; collect entities per core;
# rank films by graph degree; print the top film and its P57 values; variant B adds prefix siblings.
PY
```

Observed output (article-variant family, film-first then degree):

```
'handmaiden'           films=1 top=[('Q20444585', 'The Handmaiden', 76, ['Park Chan-wook'])]
'matrix'               films=1 top=[('Q83495', 'The Matrix', 127, ['Lana Wachowski', 'Lelly Wechawsku'])]
'terminator'           films=1 top=[('Q162255', 'The Terminator', 91, ['James Cameron'])]
'prestige'             films=1 top=[('Q46551', 'The Prestige', 102, ['Christopher Nolan'])]
'departed'             films=1 top=[('Q172975', 'The Departed', 98, ['Martin Scorsese'])]
'pianist'              films=2 top=[('Q150804', 'The Pianist', 146, ['Roman Polanski']), ('Q3522228', ..., 33, ['Claude Gagnon'])]
'shawshank redemption' films=1 top=[('Q172241', 'The Shawshank Redemption', 117, ['Frank Darabont'])]
'usual suspects'       films=1 top=[('Q132351', 'The Usual Suspects', 107, ['Bryan Singer'])]
'silence of the lambs' films=1 top=[('Q133654', 'The Silence of the Lambs', 143, ['Jonathan Demme'])]
'dark knight'          films=1 top=[('Q163872', 'The Dark Knight', 157, ['Christopher Nolan'])]
'godfather'            films=3 top=[('Q47703', 'The Godfather', 159, ['Francis Ford Coppola']), ...]
'truman show'          films=1 top=[('Q214801', 'The Truman Show', 90, ['Peter Weir'])]
'twilight zone'        films=0 top=[]
```

## Failure shapes

The 31 failures split into five sub-shapes. The counts come from `iter0/t5-partial-titles.log`.

| Sub-shape | Reply | Count | Case ids |
|---|---|---|---|
| `no_entity` safe failure | `no_entity()` sentence | 16 | 001, 002, 003, 004, 005, 016, 017, 022, 023, 024, 025, 026, 027, 028, 029, 033 |
| `no_facts` relation refused | `no information about the ...` | 6 | 006, 008, 018, 030, 031, 032 |
| wrong title, expected absent | `The factual answer is: <other film>` | 6 | 035, 036, 037, 038, 043, 044 |
| trap value returned | `The factual answer is: Lal and Siddique` | 2 | 007, 009 |
| answered instead of clarifying | `The factual answer is: Catherine Hardwicke` | 1 | 045 |

Total: 31.

The `no_entity` 16 split further by mechanism.
Partial absent from `Lexicon.lbl2ent` entirely: 10 (001, 002, 003, 022, 023, 024, 025, 026, 027, 033).
Label exists but every entity under it is a non-film, and the single-word film filter drops it: 6 (004, 005, 016, 017, 028, 029).
The `no_facts` 6 split as: a same-string non-film entity wins the link (5: 006, 018, 030, 031, 032); a film label wins but has no edge for the asked predicate (1: 008).
The wrong-title 6 split as: a fuzzy near-match resolves a single token (2: 035, 036); the single-word film fallback links a content word (4: 037, 038, 043, 044).
The remaining 20 cases pass: 6 full-title controls (046-051) and 14 partials whose core is already an exact label (010-015, 019-021, 034, 039-042).

## Ranked hypotheses

Hypothesis 1 (primary): recognition never expands a partial mention into its article-stripped label family, so the intended film is never a candidate.
Test: Probe 1 shows the expected entity absent from `candidates` for every failing case.
Probe 3 shows the family rule (film-first then degree) yields the expected film for all 31.
Verdict: confirmed.

Hypothesis 2: the failures are a ranking problem only, because the right entity is in the candidate list.
Test: Probe 1. Case 035 returns `cands=['Q1971726']` and expected `Q132351`; case 007 returns `['Q5576354']` and expected `Q184768`.
Verdict: rejected.

Hypothesis 3: the 0.85 fuzzy cutoff is the main cause.
Test: Probe 2. Article-stripped partials score 0.60-0.833 against their full labels; `'shawshank redemption'` returns `None`.
Verdict: rejected as primary; the fuzzy pass causes wrong links, not the missing ones.

Hypothesis 4: the wrong titles come from the last-resort single-word fallback and the fuzzy pass.
Test: Probe 1 last-resort lines: `silence` -> Q18811634, `truman` -> Q21034423, `twilight` -> Q160071, `godfather` -> Q5576354.
Probe 2 shows `'suspects'` matches `'suspect'` at 0.875, so case 035 links to Q1971726.
Verdict: confirmed.

Hypothesis 5: the wrong-title cases link `The Usual Suspects` and then rank wrongly.
Test: Probe 2. `Lexicon.lbl2ent['usual suspects']` is `None`; `'the usual suspects'` maps to Q132351.
Verdict: rejected.

Hypothesis 6: quote handling (Q12) causes the failures.
Test: Probe 1. Quoted and unquoted forms fail identically (001 `handmaiden` and 003 `'handmaiden'` both return `cands=[]`).
Verdict: rejected.

Hypothesis 7: the clarify case 045 needs a new reply template.
Test: `agent/nlg.py` holds exactly `no_entity`, `no_relation`, and `no_facts`; the dataset expects the `no_entity()` sentence.
Verdict: rejected; reuse `nlg.no_entity()`.

## Root cause

One primary root cause: recognition proposes candidates only for exact `lbl2ent` keys.
Linking then ranks only within that one key.
Neither step expands the mention into its article-stripped label family (Q10, Q15).
So a partial title either finds no candidate or falls through to another film.
Phase: Phase 1, entity recognition.
Boundary: B2 (Phase 1 -> Phase 2 linking), per `02-architecture-contracts.md:28-34`, which names attack T5 and the `handmaiden -> []` example.
Code symbols and locations:
- `Parser._find_entity` at `agent/parser.py:100-147`; exact-key lookups at `agent/parser.py:104`, `122`, and `130`; fuzzy pass at `agent/parser.py:134-146` with `score_cutoff=0.85` at `agent/parser.py:141-142`.
- The last-resort single-word film fallback at `agent/parser.py:127-132` links `silence`, `truman`, `twilight`, and `godfather` to other films.
- `Parser._rank` at `agent/parser.py:165-171` ranks films first then degree, but only over the one key's entities.
- `Lexicon.lbl2ent` stores exact lowercased labels at `agent/lexicon.py:30`, with no article-stripped index.
- The handler consumes the single QID and refuses or answers at `agent/handlers/factual.py:21-30`.

## Decision constraints

- Q15 (line 137): rank all matching title candidates (exact labels, article variants, prefix siblings) by film-first then graph degree; answer the top film; clarify only when no film candidate exists.
- Q15 revises the Q2 example: `matrix` resolves to The Matrix (Q83495), not to a clarification.
- Q10 (line 127): rank within article-stripped label families; `Godfather` and `Godfahter` resolve to The Godfather.
- Q2 (line 113): a unique core-name match links to the full title; a mention with extra words around a title is not the title.
- Q3 (line 114): the fix lives in `agent/preprocess.py`; `parser.py` or `nlg.py` edits need a diagnosis proof.
- The clarify case 045 has no film candidate in this KG (`05-dataset-manifest.md:260`); it must return the `no_entity()` sentence.
- The eval contract is substring presence and absence, case-insensitive (`agent/eval.py:19-22`).
- Stage 2 must stay at 508/508 and Stage 1 at 9/9.

## Suggested fix

Create `agent/preprocess.py` and call it once at the Phase 1 seam, before `Parser.parse`.
The call site is `FactualHandler.handle` at `agent/handlers/factual.py:21` (`self.parser.parse(text)`).
`02-architecture-contracts.md:96` names this call as the single intercept point.
The seam shape is raw text in and normalised text out (Q3).

Algorithm:
1. Build an article-stripped family index from `Lexicon.lbl2ent`, stripping a leading `the `, `a `, or `an `.
2. Tokenise the question with the word regex at `agent/parser.py:107`.
3. Mark relation-phrase spans with the phrase set at `agent/parser.py:52-59`.
4. For each token run of 1 to 6 tokens outside those spans, strip quotes and trailing punctuation.
5. Look up the stripped core in the family index, and collect its article variants and prefix siblings (Q15).
6. Rank the film members with `Parser._rank` (`agent/parser.py:165-171`), which already ranks film-first then graph degree.
7. When a film exists, rewrite the span as that member's exact label in single quotes, then call the parser.
8. When the family holds no film, return `nlg.no_entity()` directly, so case 045 clarifies.

Probe 3 predicts this rule fixes all 31 failures and keeps the 20 passing cases.
Example: `who directed handmaiden?` becomes `who directed 'The Handmaiden'?`; the quoted pass at `agent/parser.py:102-105` resolves Q20444585.
Example: `Who directed twilight zone?` matches the `twilight zone` family, finds no film, and returns the `no_entity()` sentence.

No `parser.py`, `lexicon.py`, or `nlg.py` edit is required, because the normalised mention matches the existing exact passes.
The one candidate edit beyond the seam is a derived `Lexicon.core2ent` cache at `agent/lexicon.py:30`.
Justify it only if startup cost or latency measured at A4 demands it, because the derivation is pure.

## Regression seam

Primary dataset command, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/t5-partial-titles.jsonl
```

Success: pass rate >= 0.8 (>= 41/51), with the 31 previously-failing ids now passing.
The 31 ids: 001-009, 016-018, 022-033, 035-038, 043-045.
The five reprod cases in the log are the first proof: 001, 006, 035, 007, 045.
Case 045 must return the `no_entity()` sentence, and 007 and 009 must not return `Lal and Siddique`.

Golden no-regression commands:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl   # 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl  # 508/508
```

Golden cases at risk (`evals/stage2_factual.jsonl`): the unquoted and lowercase title forms, such as `godfather-unquoted`, `matrix-cast`, and `inception-lowercase`.
Run the neighbour clusters, because they share the recognition seam:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t4-typos.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t3-quote-shapes.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d2-multiple-mentions.jsonl
```

Guards: the T2 crafted longer non-titles must stay clarifications (for example `looking tarzan`).
The D2 cases with two mentions must keep returning the clarification reply.
The T3 and T4 `godfather` cases must keep forbidding `Lal and Siddique`.

## Risks and open questions

- The family rule choice is the main risk. Article variants alone fix all 31 cases (Probe 3).
  Prefix siblings change several resolutions: `terminator` -> Terminator 2, `godfather` -> The Godfather Part II.
  Both still pass these cases, but prefix expansion can introduce wrong links elsewhere (T2, D2).
- Case 045 needs an active clarification. Leaving the text unchanged lets the parser match `twilight` and answer Twilight.
  The preprocess must return `nlg.no_entity()` when a matched family holds no film.
- The `pianist` family holds two films: Q150804 (degree 146) and Q3522228 (degree 33).
  Degree ranking picks Roman Polanski, so a degree change could flip the answer.
- `titanic` resolves to the 1953 film Q1197729, because Q25173 is not film-typed in this KG.
  This confirms KG type quirks, not a parser rule.
- Mention detection duplicates part of `Parser._find_entity`. A too-broad matcher can rewrite relation words and break cases.
- Case 034 passes only by accident: `for shawshank redemption` scores 0.875 against the full label (Probe 2).
  The fix must resolve it on purpose and must not depend on that accident.
- The dataset grounding uses Q184768 (`The Godfather Part II`) for `godfather`, while Q15 names Q47703.
  Both give Francis Ford Coppola, so the value check passes.
- Open question: does Q15 `prefix siblings` mean titles that share the mention as a prefix?
  This report recommends measuring prefix expansion against T2 and D2 before shipping it.
- Open question: which label text should the rewrite use when a key maps to several QIDs.
  This report recommends the exact label of the chosen family member.
