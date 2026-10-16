# c-t4-typos - diagnosis

State: S7.
Cluster: `c-t4-typos`.
Dataset: `evals/adversarial/t4-typos.jsonl` (60 cases, 21 failures at baseline).
Baseline: 39/60 passed (65.0%).
Fix bar: pass rate >= 0.8, so at least 48/60 cases must pass.
Decision anchors: Q7, Q10, Q11 (and Q3 for the seam, Q15 for prominence).

## Red repro

Repro log: `docs/design/adversarial/eval/s7-repros.log`, section `## c-t4-typos` (lines 133-175).
Capture command, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output for the two `no_entity` repros (`t4-typos-003`, `t4-typos-031`):

```
--- t4-typos-003
input: "Who directed 'godfathre'?"
expected: ['Francis Ford Coppola']
forbidden: ['Lal', 'Siddique']
span=(0, 0) candidates=[]
rest_after_span=" Who directed 'godfathre'?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text="Who directed 'godfathre'?", entity=None, predicate=None, direction='out', kind='lookup', error='no_entity')
reply="I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"
```

Observed output for the wrong-link repro (`t4-typos-002`):

```
--- t4-typos-002
input: 'Who directed godfatherr?'
expected: ['Francis Ford Coppola']
forbidden: ['Lal', 'Siddique']
span=(13, 24) candidates=['Q5576354']
rest_after_span='Who directed  ' predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text='Who directed godfatherr?', entity='Q5576354', predicate='...P57', direction='out', kind='lookup', error=None)
  [sparql] ... <http://www.wikidata.org/entity/Q5576354> <...P57> ?x ...
reply='The factual answer is: Lal and Siddique'
```

Observed output for the wrong-title repro (`t4-typos-033`):

```
--- t4-typos-033
input: 'Who directed batman begns?'
expected: ['Christopher Nolan']
forbidden: []
span=(13, 19) candidates=['Q116852', 'Q810857']
rest_after_span='Who directed   begns?' predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Tim Burton'
```

CLI equivalent for one red case (loads the KG, about 15 s):

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.cli --debug "Who directed 'godfathre'?"
```

The baseline report `docs/design/adversarial/eval/iter0/t4-typos-baseline.md` records the same 21 failures.

### Recorded probes

Probe 1, parser internals on the failing inputs:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
from agent.config import load_settings; from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon; from agent.parser import Parser
s = load_settings(); kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s, max_fetch_rows=s.max_fetch_rows, workers=s.workers)
lex = Lexicon(kg); p = Parser(kg, lex)
for text in ["Who directed 'godfathre'?", "Who directed 'the matrx'?", "Who directed terminater?",
             "Who directed godfahter?", "Who directed godfatherr?", "Who directed batman begns?",
             "Who directed 'batman bigins'?", "Who wrote the screenplay for godfther?"]:
    span, cands = p._find_entity(text)
    print(text, span, repr(text[span[0]:span[1]]), cands)
kg.close()
PY
```

Observed output (key lines):

```
"Who directed 'godfathre'?"   (0, 0)   ''            []
"Who directed 'the matrx'?"   (0, 0)   ''            []
'Who directed terminater?'    (0, 0)   ''            []
'Who directed godfahter?'     (13,23)  'godfahter?'  ['Q5576354']
'Who directed godfatherr?'    (13,24)  'godfatherr?' ['Q5576354']
'Who directed batman begns?'  (13,19)  'batman'      ['Q116852', 'Q810857']
"Who directed 'batman bigins'?" (13,20) "'batman"    ['Q116852', 'Q1247201', ...]
'Who wrote the screenplay for godfther?' (29,38) 'godfther?' ['Q5576354']
```

Probe 2, mention-level fuzzy scores and article-stripped family scores:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
from agent.config import load_settings; from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon; from agent.parser import Parser
from rapidfuzz import process; from rapidfuzz.distance import OSA
s = load_settings(); kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s, max_fetch_rows=s.max_fetch_rows, workers=s.workers)
lex = Lexicon(kg); p = Parser(kg, lex)
print(lex.ent2lbl['Q5576354'], lex.lbl2ent['godfather'], lex.lbl2ent['the godfather'])
for phrase in ["'godfathre'", "godfathre", "terminater", "jwaws", "the matrx", "batman begns", "'batman", "godfahter"]:
    print(phrase, process.extract(phrase, p.fuzzy_labels, scorer=OSA.normalized_similarity, limit=2))
kg.close()
PY
```

Observed output (key lines):

```
Godfather ['Q5576354'] ['Q47703', 'Q3225260', 'Q1139696', 'Q243556']
"'godfathre'" [('godfather', 0.727), ('3 godfathers', 0.667)]
'godfathre'   [('godfather', 0.889), ('3 godfathers', 0.667)]
'terminater'  [('the terminator', 0.643), ('the monster', 0.636)]
'jwaws'       [('jaws', 0.800), ('jeans', 0.600)]
'the matrx'   [('the matrix', 0.900), ('the master', 0.700)]
'batman begns'[('batman begins', 0.923), ('batman returns', 0.714)]
"'batman"     [('batman', 0.857), ('bataan', 0.714)]
'godfahter'   [('godfather', 0.889), ('3 godfathers', 0.667)]
```

Probe 3, the Q7/Q10/Q11 family rule over all 60 cases (corrected re-run; a first attempt scored whole sentences and was discarded):

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
# strip the question prefix, strip quotes, strip articles; score the mention
# against article-stripped label families; accept iff unique best >= thr and gap >= 0.05;
# thr = 0.80 when the stripped core is <= 6 chars, else 0.85; pick films first then degree.
# (full script run in this session)
PY
```

Observed output (every mapped typo accepted and resolved; every scramble refused):

```
t4-typos-001 godfahter  -> family godfather     sc 0.89 gap 0.22 -> pick Q47703   RESOLVES
t4-typos-005 terminater -> family terminator    sc 0.90 gap 0.20 -> pick Q162255  RESOLVES
t4-typos-009 jazws      -> family jaws          sc 0.80 gap 0.20 -> pick Q189505  RESOLVES
t4-typos-012 jwaws      -> family jaws          sc 0.80 gap 0.20 -> pick Q189505  RESOLVES
t4-typos-031 matrx      -> family matrix        sc 0.83 gap 0.17 -> pick Q83495   RESOLVES
t4-typos-033 batman begns -> family batman begins sc 0.92 gap 0.21 -> pick Q166262 RESOLVES
t4-typos-039 prestrige  -> family prestige      sc 0.89 gap 0.29 -> pick Q46551   RESOLVES
t4-typos-046 deparred   -> family departed      sc 0.88 gap 0.18 -> pick Q172975  RESOLVES
t4-typos-004 godfther   -> family godfather     sc 0.89 gap 0.22 -> pick Q47703   RESOLVES
t4-typos-048 otinenpic  -> best family titanic  sc 0.56 gap 0.00 -> refuse
t4-typos-052 txairm     -> best family taxidermy sc 0.56 gap 0.06 -> refuse
t4-typos-055 nmdnhdaiae -> best family mindanao sc 0.50 gap 0.04 -> refuse
```

All 60 rows were scored. Every one of the 47 mapped typos resolved to its `grounding.entity`. All 8 safe scrambles (048-055) and the 5 controls (056-060) were classified correctly.

## Failure shapes

The 21 failures split into four sub-shapes. The counts come from `iter0/t4-typos-baseline.md`.

| Sub-shape | Reply | Count | Case ids |
|---|---|---|---|
| `no_entity` safe failure | `no_entity()` sentence | 16 | 003, 005, 006, 007, 008, 009, 010, 011, 012, 015, 019, 023, 027, 031, 039, 046 |
| trap value returned | `The factual answer is: Lal and Siddique` | 2 | 001, 002 |
| wrong answer, expected absent | `The factual answer is: Tim Burton` | 2 | 033, 035 |
| `no_facts` relation refused | `no information about the screenwriter of Godfather` | 1 | 004 |

Total: 21.
The 16 `no_entity` cases split further by mention form.
Quoted mentions: 10 (003, 007, 011, 015, 019, 023, 027, 031, 039, 046).
Bare mentions: 6 (005, 006, 008, 009, 010, 012).
The remaining 39 passing cases are 26 mapped typos, 8 safe scrambles (048-055), and 5 controls (056-060).

## Ranked hypotheses

Hypothesis 1 (primary): the fuzzy pass rejects near typos because it scores raw labels below 0.85, and because the quoted token keeps its quote characters.
Test: Probe 2. `"'godfathre'"` scores 0.727; the stripped core `"godfathre"` scores 0.889. `"terminater"` scores 0.643 against raw `"the terminator"`, but 0.90 against the article-stripped family `"terminator"`. `"jwaws"` scores 0.800, below the 0.85 cutoff.
Verdict: confirmed.

Hypothesis 2: the 2 wrong-link cases match the raw label `godfather` and link to Q5576354.
Test: Probe 2. `lbl2ent['godfather'] == ['Q5576354']`; `"godfahter"` scores 0.889 against `"godfather"` but only 0.615 against `"the godfather"`. Probe 1 shows `candidates=['Q5576354']`, so `_rank` has nothing else to choose.
Verdict: confirmed.

Hypothesis 3: the 2 wrong-title cases link the single word `batman`, not the full phrase.
Test: Probe 1. Bare `"batman begns"` returns span `(13,19)` `"batman"`; the one-word film fallback at `agent/parser.py:127-132` fires before the fuzzy pass. Quoted `"batman bigins"` returns span `(13,20)` `"'batman"`; the quote is part of the token, so `"'batman"` scores 0.857 against `"batman"` and passes the 0.85 cutoff.
Verdict: confirmed.

Hypothesis 4: the 1 `no_facts` case links `godfther` to Q5576354, which has no P58 edge.
Test: Probe 1 returns `candidates=['Q5576354']` for `"godfther"`. Probe 2 shows `"godfther"` scores 0.889 against raw label `"godfather"`. The reply names `Godfather` (Q5576354) and reports no screenwriter.
Verdict: confirmed.

Hypothesis 5: the failures come from Phase 3 relation detection or a missing KG entity.
Test: The repro log shows `predicates=['http://www.wikidata.org/prop/direct/P57']` for all four repros, and Probe 3 resolves every expected entity from the KG.
Verdict: rejected.

## Root cause

One primary root cause: the Phase 1 fuzzy pass matches a single global best over raw label strings, at a fixed 0.85 cutoff, with no article stripping, no family grouping, and no margin.
Code symbols and locations:
- `Parser._find_entity` fuzzy pass at `agent/parser.py:134-146`; `process.extractOne` with `score_cutoff=0.85` at `agent/parser.py:141-142`.
- `self.fuzzy_labels` is built from raw `lexicon.lbl2ent` keys at `agent/parser.py:60-61`.
- `Lexicon.lbl2ent` stores raw lowercased labels at `agent/lexicon.py:30`.
- The quoted pass matches only exact labels at `agent/parser.py:102-105`.
- The one-word film fallback at `agent/parser.py:127-132` intercepts `"batman begns"` before the fuzzy pass.
- The word token regex `[\w'&:.!?-]+` at `agent/parser.py:107` keeps quote characters inside tokens.
- `Parser._rank` ranks films first then degree at `agent/parser.py:165-171`, but only over the candidate list it receives.

Phase: Phase 1, entity recognition.
Boundary: B1 (source -> Phase 1 recognition) per `02-architecture-contracts.md:20-26`.
The wrong-link and wrong-title failures cross into B2 (Phase 1 -> Phase 2 linking), per `02-architecture-contracts.md:28-34`.
At B2 `_rank` cannot recover, because the candidate list holds only the wrong QID.
The decisions Q7, Q10, and Q11 define the missing acceptance rule: article-stripped families, unique best, film-first by degree, thresholds 0.85 and 0.80 with a margin of 0.05.

## Decision constraints

- Q7 (line 118): accept a fuzzy match only when it is the unique best label at the 0.85 cutoff; otherwise refuse safely.
- Q10 (line 127): rank within article-stripped label families, films first, then graph degree; `Godfather` and `Godfahter` resolve to The Godfather.
- Q11 (line 128): a unique short-word match is accepted with a core of 6 characters or fewer, score >= 0.80, and a gap >= 0.05.
- Q3 (line 114): the fix lives in `agent/preprocess.py`; `parser.py` or `nlg.py` edits need a diagnosis proof.
- Q15 (line 137): prominence ranking everywhere, film-first then degree.
- The dataset manifest rule at `05-dataset-manifest.md:259`: a typo enters the file only when the intended family is the unique best match with those margins; the wrong-link reply is `forbidden`.
- Q2 (line 113): a mention that carries extra words around a title is not the title, so the preprocess must not over-match.
- The safe scrambles (048-055) must stay `no_entity`, and the controls (056-060) must stay green.

## Suggested fix

Create `agent/preprocess.py` and call it once at the Phase 1 seam, before `Parser.parse`.
The call site is `FactualHandler.handle` at `agent/handlers/factual.py:21` (`self.parser.parse(text)`), which `02-architecture-contracts.md:96` names as the single intercept point.
The module normalises the mention, and the seam shape is raw text in and normalised text out (Q3).

Algorithm:
1. Tokenise the question with the same word regex the parser uses (`agent/parser.py:107`).
2. Build an article-stripped family index from `Lexicon.lbl2ent`, stripping a leading `the `, `a `, or `an `.
3. For each contiguous token run (1 to 6 tokens) of at least 5 characters, strip surrounding quotes, strip trailing punctuation, and strip a leading article.
4. Score the stripped mention against family keys with `OSA.normalized_similarity` (the scorer at `agent/parser.py:141`).
5. Keep the best family by score and remember the second-best family.
6. Accept when the best score is >= 0.85, or >= 0.80 when the stripped core is 6 characters or fewer, and the gap to second best is >= 0.05.
7. On accept, pick the film-first, highest-degree member of the family (the `_rank` rule at `agent/parser.py:165-171`) and rewrite the span with that member's exact label in single quotes.
8. On reject, return the input unchanged, so the existing parser still runs and the scrambles stay safe.

Probe 3 predicts this rule fixes all 21 failures and keeps the 39 passing cases.
Example: `"Who directed godfahter?"` becomes `"Who directed 'The Godfather'?"`; the exact quoted pass at `agent/parser.py:102-105` resolves `lbl2ent['the godfather']`, and `_rank` picks Q47703.
Example: `"Who directed batman begns?"` becomes `"Who directed 'Batman Begins'?"`, which bypasses the one-word fallback.
No `parser.py`, `lexicon.py`, or `nlg.py` edit is required, because the normalised mention matches the existing exact passes.
The handler call line is the seam, not a new parser rule, so it fits Q3.

## Regression seam

Primary dataset command, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/t4-typos.jsonl
```

Success: pass rate >= 0.8 (>= 48/60), with all 21 previously-failing ids now passing.
The 21 ids: 001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 015, 019, 023, 027, 031, 033, 035, 039, 046.
Guard cases that must not regress:
- The 8 scrambles 048-055 must still return the `no_entity()` sentence (Probe 3 refuses all eight).
- The 5 controls 056-060 must stay green.
- The wrong-link reply `Lal and Siddique` must stay absent on 001, 002, 003, and 056.

Golden no-regression commands:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl   # 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl  # 508/508
```

Golden cases at risk (`evals/stage2_factual.jsonl`): `godfather-typo` (line 10), `godfather-unquoted` (line 8), `godfather-lowercase` (line 9), `unknown-title` (line 48), `inception-lowercase` (line 11), `jaws-polite` (line 45), `matrix-cast` (line 13).
Run the other adversarial clusters as neighbours, because the same seam can shift T2 and T5:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t5-partial-titles.jsonl
```

## Risks and open questions

- Mention span selection is the main risk. A matcher over the whole question text would rewrite relation words and break every case. The preprocess must score token runs, as the parser does at `agent/parser.py:135-140`.
- T2 subvention is the top cross-cluster risk. A crafted longer non-title could score above the threshold and get rewritten. Q2 and `05-dataset-manifest.md:257` say the cores are far from every family, so the rule should refuse them. Verify with the T2 command above.
- The one-word film fallback and the quote-in-token behaviour stay in `agent/parser.py`. The preprocess only avoids them when it rewrites the full span. Declined mentions keep today's behaviour.
- The rewrite must pick a canonical label that `_rank` maps back to the intended QID. Probe 3 checked this pick for every accepted row and it matched each `grounding.entity`.
- Q11 wording "words <= 6 characters" is ambiguous. This report reads it as the article-stripped core length of 6 or fewer characters. Confirm with the operator.
- Family index and graph degree cost a little startup work. Build them once and cache per entity to respect the latency guardrail A4.
- T5 partial titles share the same seam. The rule would also fix many T5 cases (Q15), so the fix may land as one shared normaliser. That is a scoping decision for the operator.
- Open question: when a family has several labels, which label text should the rewrite use? This report recommends the chosen member's exact label.
