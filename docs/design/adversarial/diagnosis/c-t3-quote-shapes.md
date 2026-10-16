# c-t3-quote-shapes - diagnosis

Cluster: `c-t3-quote-shapes`.
Dataset: `evals/adversarial/t3-quote-shapes.jsonl`.
Baseline: 37/57 passed, 20 failures (`docs/design/adversarial/eval/iter0/t3-quote-shapes-baseline.md`).
Fix bar: pass rate >= 0.8, so at least 46/57 cases must pass.
This report uses 37 as the green-case count (57 - 20).

## Red repro

Repro command (from the `scripts/adversarial/capture_repros.py` docstring):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output, section `## c-t3-quote-shapes` of `docs/design/adversarial/eval/s7-repros.log` (lines 88-129):

```text
--- t3-quote-shapes-001
input: "Who directed ''Inception''?"
expected: ['Christopher Nolan']
span=(0, 0) candidates=[]
rest_after_span=" Who directed ''Inception''?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text="Who directed ''Inception''?", entity=None, predicate=None, direction='out', kind='lookup', error='no_entity')
reply="I'm not sure which movie or person you mean. ..."

--- t3-quote-shapes-024
input: "Who directed 'The Matrix.'?"
expected: ['Lana Wachowski', 'Lelly Wechawsku']
span=(18, 24) candidates=['Q44337']
rest_after_span="Who directed 'The  .'?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text="Who directed 'The Matrix.'?", entity='Q44337', predicate='...P57', direction='out', kind='lookup', error='no_facts')
reply='Sorry, my knowledge graph has no information about the director of matrix.'

--- t3-quote-shapes-054
input: "Who directed 'The Departed?'?"
span=(0, 0) candidates=[]
  [question] Question(text="Who directed 'The Departed?'?", entity=None, predicate=None, direction='out', kind='lookup', error='no_entity')

--- t3-quote-shapes-010
input: "Who directed 'The Godfather?'?"
expected: ['Francis Ford Coppola']
forbidden: ['Lal and Siddique']
span=(18, 27) candidates=['Q5576354']
rest_after_span="Who directed 'The  ?'?" predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Lal and Siddique'
```

Case 001 proves a doubled quote returns `span=(0, 0)`, so recognition finds nothing.
Case 024 proves a period inside the quotes leaves the bare span `(18, 24)` = `"Matrix"`.
Case 054 proves an inner question mark and no match return `span=(0, 0)`.
Case 010 proves the bare span `(18, 27)` = `"Godfather"` links a wrong node.

### Recorded probe P1 - parser internals and label families

Command (heredoc; loads the agent once through `load_settings` and `KnowledgeGraph.open`):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
from agent.config import load_settings
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.parser import Parser
from agent import sparql_builder as sb
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
lex = Lexicon(kg); p = Parser(kg, lex)
inputs = ["Who directed 'Batman Begins?'?", "Who directed 'Jaws.'?",
          "Who directed ''Inception''?", "Who directed 'The Matrix.'?",
          "Who directed 'The Godfather?'?", "Who directed 'The Pianist.'?",
          "Who wrote the screenplay for 'Interstellar.'?", "Who directed 'The Departed?'?"]
for text in inputs:
    span, cands = p._find_entity(text); q = p.parse(text)
    print(text)
    print("  span=", span, "cands=", cands, "span_text=", repr(text[span[0]:span[1]]))
    print("  q.entity=", q.entity, "q.error=", q.error)
for key in ["godfather", "the godfather", "matrix", "the matrix", "pianist", "the pianist",
            "batman", "batman begins", "begins"]:
    print(key, "->", [(x, lex.label(x), lex.is_film(x)) for x in lex.lbl2ent.get(key, [])])
PY
```

Observed output:

```text
Who directed 'Batman Begins?'?
  span= (13, 20) cands= ['Q116852', ...] span_text= "'Batman"
  q.entity= Q116852 q.error= None
Who directed 'Jaws.'?
  span= (0, 0) cands= [] span_text= ''
  q.entity= None q.error= no_entity
Who directed ''Inception''?
  span= (0, 0) cands= [] span_text= ''
  q.entity= None q.error= no_entity
Who directed 'The Matrix.'?
  span= (18, 24) cands= ['Q44337'] span_text= 'Matrix'
  q.entity= Q44337 q.error= no_facts
Who directed 'The Godfather?'?
  span= (18, 27) cands= ['Q5576354'] span_text= 'Godfather'
  q.entity= Q5576354 q.error= None
Who directed 'The Pianist.'?
  span= (18, 25) cands= ['Q486748'] span_text= 'Pianist'
  q.entity= Q486748 q.error= no_facts
Who wrote the screenplay for 'Interstellar.'?
  span= (0, 0) cands= [] span_text= ''
  q.entity= None q.error= no_entity
Who directed 'The Departed?'?
  span= (0, 0) cands= [] span_text= ''
  q.entity= None q.error= no_entity
godfather -> [('Q5576354', 'Godfather', True)]
the godfather -> [('Q47703', 'The Godfather', True), ('Q3225260', 'The Godfather', True), ('Q1139696', 'The Godfather', False), ('Q243556', 'The Godfather', False)]
matrix -> [('Q44337', 'matrix', False)]
the matrix -> [('Q33140061', 'The Matrix', False), ('Q13014087', 'The Matrix', False), ('Q83495', 'The Matrix', True)]
pianist -> [('Q486748', 'pianist', False)]
the pianist -> [('Q3522228', 'The Pianist', True), ('Q2641481', 'The Pianist', False), ('Q150804', 'The Pianist', True)]
batman -> [('Q116852', 'Batman', True), ..., ('Q810857', 'Batman', True), ...]
batman begins -> [('Q166262', 'Batman Begins', True), ('Q2891561', 'Batman Begins', False)]
begins -> []
```

P1 shows four recognition paths.
The doubled-quote and lone-quote inputs return `span=(0, 0)`.
The inner-punctuation inputs return a bare trailing token: `"Matrix"`, `"Pianist"`, `"Godfather"`.
The `'Batman Begins?'?` input returns the quote-prefixed token `"'Batman"` and links the Batman family.
P1 also proves the bare keys `godfather`, `matrix`, `pianist` are DISTINCT families from `the godfather`, `the matrix`, `the pianist`.

### Recorded probe P2 - fuzzy score of the quote-prefixed token

Command:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
from rapidfuzz import process
from rapidfuzz.distance import OSA
labels = ["batman", "batman begins", "batman forever", "batman returns", "the batman", "batman & robin"]
for phrase in ["'batman", "'batman begins", "'batman begins?'", "batman begins"]:
    print(repr(phrase), "->", process.extractOne(phrase, labels, scorer=OSA.normalized_similarity, score_cutoff=0.85))
PY
```

Observed output:

```text
"'batman" -> ('batman', 0.8571428571428572, 0)
"'batman begins" -> ('batman begins', 0.9285714285714286, 1)
"'batman begins?'" -> None
'batman begins' -> (1.0)
```

P2 proves the trailing quote blocks the `?` strip.
`agent/parser.py:138` strips `"?.!,"` but not `'`, so the fuzzy phrase stays `"'batman begins?"` and misses the 0.85 cutoff.
The fallback single token `"'batman"` then scores 0.857 and wins.

### Recorded probe P3 - normalisation feasibility over all 57 cases

Command: the P1 setup, plus a `normalize(text)` that maps curly quotes to straight and drops every quote char that is not between two letters.
The probe then calls the UNCHANGED `Parser._find_entity` on the normalised text and compares `q.entity` to `grounding.entity`.

Observed output:

```text
normalized parse: 57/57 reach the grounding entity
fails: []
```

P3 proves the seam alone can fix all 20 failures.
After normalisation every case reaches the full article label, so `lbl2ent["the godfather"]` and `lbl2ent["the matrix"]` win.
No ranking change is needed for the two wrong-link cases and the one wrong-title case.
The exact rule in P3 is naive: it drops the elision apostrophe in `o'`.
The rule must be refined before it ships (see Risks).

## Failure shapes

The baseline report splits the 20 failures into four reply clusters.
The cluster index refines the 12 `no_entity` cases into two shapes.
The five sub-shapes sum to 20.

| Sub-shape | Input shape | Cases | Count | Observed reply |
|---|---|---|---|---|
| A | doubled quotes (`''Title''`) | 001, 015, 016, 030, 044, 045 | 6 | `no_entity` |
| B | stray or inner punctuation, no bare label at the tail | 011, 026, 029, 040, 053, 054 | 6 | `no_entity` |
| C | inner punctuation, bare lower-case label at the tail | 021, 024, 025, 055, 056 | 5 | `no_facts` |
| D | bare-word article-strip collision | 009, 010 | 2 | `Lal and Siddique` |
| E | bare-word fuzzy fragment | 039 | 1 | `Tim Burton` |

Sum: 6 + 6 + 5 + 2 + 1 = 20, the failure count.
Shapes A and B are the 12 `no_entity` cases (doubled 6, unclosed or inner punctuation 6).
Shape C is the 5 `no_facts` cases.
Shapes D and E are the 2 wrong-link cases and the 1 wrong-title case.

The mechanism separates B from C.
In shape C the tail token is a real bare label (`matrix` -> Q44337, `pianist` -> Q486748), so linking succeeds and `has_facts` fails (P1).
In shape B the tail has no bare label (`jaws`, `departed`, `interstellar`, `parasite`), so recognition fails first (P1).

## Ranked hypotheses

- H1: the quoted-span pass cannot match doubled or unmatched quotes.
  Test: P1 returns `span=(0, 0)` for `''Inception''`, `'Jaws.'`, `'The Departed?'?`, and `'Interstellar.'`.
  Reading `agent/parser.py:102`: the patterns `r"'(.+)'"`, `r"'(.+?)'"`, `r'"(.+?)"'` each need a matched quote pair; `''Inception''` yields a group `"'Inception'"`.
  Reading `agent/parser.py:104`: the group must equal a label exactly; `"'inception'"` is not a key.
  Verdict: confirmed.
- H2: inner punctuation inside a matched quote breaks the exact label lookup, and the fallback grabs a bare token.
  Test: P1 returns `span=(18, 24)` `"Matrix"` for `'The Matrix.'?` and `span=(18, 27)` `"Godfather"` for `'The Godfather?'?`.
  Reading `agent/parser.py:104`: `group(1) = "The Matrix."` fails the exact membership test.
  Reading `agent/parser.py:107`: the token regex splits on the space, so the leading `'The` is a separate token.
  Verdict: confirmed.
- H3: the strip sets at the token and fuzzy passes omit the quote character, so a trailing quote blocks punctuation removal.
  Test: P2 shows `"'batman begins?"` scores `None`; the trailing `'` stops the `?` strip.
  Reading `agent/parser.py:114,129,138`: the strip strings are `"?.!'"`, `"?.!,"` and `"?.!,"`.
  Only line 114 includes `'`; lines 129 and 138 do not.
  Verdict: confirmed.
- H4: the two wrong-link cases and the one wrong-title case are independent linker bugs.
  Test: P3 shows all 57 cases reach the grounding entity after normalisation, including 009, 010 and 039.
  Reading `agent/parser.py:105,146`: the linker ranks the family it is handed; `_rank` (`agent/parser.py:165-171`) is faithful.
  The linker is handed a fragment, not the full title, so the fragment is the defect.
  Verdict: rejected.
- H5: the article-stripped family ranking (Q10, Q15) is required to fix shapes D and E.
  Test: P3 resolves `"The Godfather"` and `"Batman Begins"` through the existing exact keys.
  The exact keys already exist: `the godfather` -> Q47703 and `batman begins` -> Q166262 (P1).
  Verdict: rejected for this cluster; Q10 and Q15 stay binding for bare-word T4 and T5 forms.

## Root cause

Primary root cause: Phase 1 (Entity recognition) has no quote normalisation, so malformed quotes never reach the exact label lookup.
Boundary: B1 (source -> Phase 1), from `docs/design/adversarial/02-architecture-contracts.md`.

`Parser.parse` normalises only the curly single quotes at `agent/parser.py:64`.
It never collapses doubled straight quotes, never removes a stray quote, and never strips punctuation inside a quote pair.
`Parser._find_entity` (`agent/parser.py:100-147`) then fails on four shapes:

- The quoted-span patterns at `agent/parser.py:102` require a matched pair and capture the doubled inner quotes.
  The membership test at `agent/parser.py:104` then rejects the value.
- The token pass at `agent/parser.py:107` splits a quoted title on its spaces.
  The leading `'The` becomes a separate token and isolates the bare tail token (`"Matrix"`, `"Godfather"`).
- The strip sets at `agent/parser.py:129` and `agent/parser.py:138` omit `'`.
  A trailing quote therefore blocks punctuation removal (P2).
- The returns at `agent/parser.py:125` and `agent/parser.py:146` link the bare token through `self.lex.lbl2ent[phrase.lower()]`.
  The bare keys are wrong families: `godfather` -> Q5576354 and `matrix` -> Q44337 (`agent/lexicon.py:30`, P1).

The linking phase then behaves correctly on its wrong input.
`_rank` (`agent/parser.py:165-171`) returns the given family, and the B5 `has_facts` gate (`agent/parser.py:86-88`) accepts the fragment entity.
The result is a confident wrong link (`Lal and Siddique`) or a confident `no_facts` about a lower-case fragment (`matrix`).

## Decision constraints

- Q12: full quote normalisation covers doubled quotes, inner whitespace and stray punctuation.
  Apostrophes inside words are never quote delimiters.
- Q3a: add `agent/preprocess.py` and call it before `Parser.parse`.
  A `parser.py` or `nlg.py` edit needs a diagnosis that proves it necessary.
- Q10 and Q15: rank title candidates within article-stripped label families, films first, then graph degree.
  Answer the top film.
  These stay binding for bare-word forms from T4 and T5, even though P3 shows they are not needed for c-t3.
- Q16: two title mentions must clarify.
  The normaliser runs for every factual question, so it must not merge two quoted mentions.
- A2: safe failures keep the existing `no_entity()` text (`agent/nlg.py`), so no new template is needed.
- A5: Stage 1 keeps 9/9.
  `SparqlHandler` runs before `FactualHandler` (`agent/core.py:65`), so the seam does not touch Stage 1.

## Suggested fix

Direction, preferring the Q3 seam:

1. Add `agent/preprocess.py` with a `normalize(text)` function.
   `normalize` applies these steps in order:
   - Map curly quotes to straight: `“ ” ‘ ’` -> `'` (`agent/parser.py:64` handles only `‘ ’` today).
   - Collapse a run of quote characters to one.
   - Strip whitespace and stray punctuation (`. ? ! ,`) inside the outer quote pair.
   - Remove an unmatched quote that sits next to whitespace or a string boundary.
   - Keep every apostrophe that is inside a word (`o'`, `Pepper's`, `What's`).
2. Call `preprocess.normalize(text)` at the seam `agent/handlers/factual.py:21`, before `self.parser.parse(text)`.
   This is the single call site named in section 5.1 of `02-architecture-contracts.md`.
3. Do not change the linker for c-t3.
   P3 shows the exact keys `the godfather`, `the matrix`, `batman begins` already resolve correctly.
   Keep Q10 and Q15 for the T4 and T5 bare-word forms in their own clusters.

Optional defensive parser edit, justified by the diagnosis but not required for c-t3:
add `'` to the strip sets at `agent/parser.py:129` and `agent/parser.py:138`.
P2 proves a trailing quote blocks the `?` strip there.
The seam fix removes the quotes first, so this edit is defence in depth.
`02-architecture-contracts.md` section 5.1 permits a `parser.py` edit when a diagnosis proves it necessary.
No `agent/lexicon.py` edit is needed: reuse `lbl2ent` (`agent/lexicon.py:30`) and `is_film` (`agent/lexicon.py:43-44`).
No `agent/nlg.py` edit is needed.

The apostrophe rule is the critical detail.
The naive rule in P3 drops the elision apostrophe in `o'`.
The shipped rule must keep an interior apostrophe that sits inside a matched quote pair.

## Regression seam

Primary command and bar:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/t3-quote-shapes.jsonl   # -> >= 46/57
```

Required outcomes for this dataset, by shape:

- Shape A (001, 015, 016, 030, 044, 045): the full title reaches the exact key and answers.
- Shape B (011, 026, 029, 040, 053, 054): the title resolves; `'Jaws'` -> Steven Spielberg, `'Parasite'` -> Bong Joon-ho.
- Shape C (021, 024, 025, 055, 056): `"The Matrix"` -> Q83495, `"The Pianist"` -> Q150804.
- Shape D (009, 010): the reply must not contain `Lal and Siddique`.
- Shape E (039): the reply must be Christopher Nolan, not Tim Burton.

The verification target is 57/57, per P3.

No-regression commands:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl   # -> 508/508
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl   # -> 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl   # Q12 neighbour
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t5-partial-titles.jsonl   # Q15 family
```

Golden cases at risk, from the file reads:

- `apostrophe-title` ("Who is the director of 'The Cat o' Nine Tails'?"): the `o'` apostrophe must survive.
- `ext-director-who-is-the-director-of-mary-shelley-s-frankenste` ("Mary Shelley's Frankenstein"): possessive apostrophe.
- `ext-director-who-directed-sgt-pepper-s-lonely-hearts-club-ban` ("Sgt. Pepper's Lonely Hearts Club Band"): possessive apostrophe.
- `ext-director-who-directed-the-pirates-in-an-adventure-with-sc` ("The Pirates! In an Adventure with Scientists!"): inner exclamation mark.
- `shawshank-year` ("What's the release year of The Shawshank Redemption?"): contraction apostrophe.
- `unknown-title` ("Who directed 'Qwzxv Plorbnik Unfilmable'?"): the safe-failure path.
- The 37 green t3 cases must keep passing, especially the curly-quote cases 008, 017, 022, 031, 042, 050, 057 and the lowercase cases 059, 060, 061.

## Risks and open questions

- The naive P3 rule drops the elision apostrophe in `o'`.
  The shipped rule must keep interior apostrophes, or `apostrophe-title` can regress.
  The fuzzy pass may recover it, but this needs a run, not a claim.
- Curly double quotes (`“ ”`) currently pass as token separators.
  Mapping them to straight quotes changes the token stream, so those green cases need a re-run.
- Removing a stray quote can turn a crafted quoted non-title into its unquoted form.
  The T2 subvention cases (`t2-subvention-002`, `t2-subvention-005`) use quoted non-titles and must stay safe.
- The normaliser runs before `Parser.parse` for every factual question.
  It must not pair the first and last quote across two mentions (the Q16 d2 family).
- P3 tests recognition only, not the full reply.
  The reply check needs the `agent.eval` run in the regression seam.
- The exact strip set for inner punctuation is a judgement call.
  A title with a legitimate trailing period is not in the KG, so stripping is safe here.
- No unit tests exist for the seam.
  `pytest` is installed into `.venv` only (Q4), so a `tests/test_preprocess.py` is possible but out of this report's scope.
