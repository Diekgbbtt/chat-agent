# c-d8-paraphrases - diagnosis

Cluster: `c-d8-paraphrases`.
Dataset: `evals/adversarial/d8-relation-paraphrases.jsonl` (70 cases).
Baseline: 10/70 passed, 60 failures (`docs/design/adversarial/eval/iter0/d8-relation-paraphrases-baseline.md:5`).
Fix bar: pass rate >= 0.8, so at least 56/70 cases must pass (`d8-relation-paraphrases-baseline.md:6`).
Contract: Q14 says nominalisations and idioms rewrite to the canonical relation words (`docs/design/adversarial/00-questions.md:136`).

## Red repro

Repro command (from the `scripts/adversarial/capture_repros.py` docstring):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output, section `## c-d8-paraphrases` of `docs/design/adversarial/eval/s7-repros.log` (lines 373-415):

```text
## c-d8-paraphrases

--- d8-relation-paraphrases-001
input: "Who did the directing for 'Inception'?"
expected: ['Christopher Nolan']
forbidden: ["I'm not sure what you'd like to know"]
span=(27, 36) candidates=['Q25188', 'Q54888270', 'Q3797611']
rest_after_span="Who did the directing for ' '?" predicates=[]
  [handler] factual
  [question] Question(text="Who did the directing for 'Inception'?", entity='Q25188', predicate=None, direction='out', kind='lookup', error='no_relation')
reply="I found Inception, but I'm not sure what you'd like to know. You can ask about its director, cast, genre, ..."

--- d8-relation-paraphrases-002
input: "Who was at the helm of 'Inception'?"
span=(24, 33) candidates=['Q25188', 'Q54888270', 'Q3797611']
rest_after_span="Who was at the helm of ' '?" predicates=[]
reply="I found Inception, but I'm not sure what you'd like to know. You can ask about its director, cast, genre, ..."

--- d8-relation-paraphrases-003
input: "Who is behind the camera on 'Inception'?"
span=(29, 38) candidates=['Q25188', 'Q54888270', 'Q3797611']
rest_after_span="Who is behind the camera on ' '?" predicates=[]
reply="I found Inception, but I'm not sure what you'd like to know. You can ask about its director, cast, genre, ..."

--- d8-relation-paraphrases-061
input: "Who is the director of 'Inception'?"
span=(24, 33) candidates=['Q25188', 'Q54888270', 'Q3797611']
rest_after_span="Who is the director of ' '?" predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Christopher Nolan'
```

The three red repros show one shared shape.
The entity resolves to `Q25188` with the right span.
`_find_predicates` returns an empty list, so `predicate=None` and `error='no_relation'`.
The green control `-061` shows the same entity span, and the phrase "director" yields P57.

### Recorded probe P1 - phrase-table membership

Command (one agent load; prints the phrase table for each paraphrase and canonical word):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -c "
from agent.cli import load_agent
agent = load_agent()
p = next(h.parser for h in agent.handlers if hasattr(h,'parser'))
words = ['directing','writing','composing','helm','at the helm','behind the camera','camera','directed','wrote','written','composed','director','filmmaker','screenplay','music','script']
for w in words:
    print(f'{w!r:22} in_phrases={w.lower() in p.phrases!s:5} -> {p.phrases.get(w.lower())}')
print('phrase_pattern_matches_directing=', bool(p.phrase_pattern.search(\"Who did the directing for x\")))
print('phrase_pattern_matches_helm=', bool(p.phrase_pattern.search(\"at the helm of x\")))
print('phrase_pattern_matches_camera=', bool(p.phrase_pattern.search(\"behind the camera on x\")))
print('phrase_pattern_matches_writing=', bool(p.phrase_pattern.search(\"Who did the writing for x\")))
print('phrase_pattern_matches_composing=', bool(p.phrase_pattern.search(\"Who did the composing for x\")))
"
```

Observed output:

```text
'directing'            in_phrases=False -> None
'writing'              in_phrases=False -> None
'composing'            in_phrases=False -> None
'helm'                 in_phrases=False -> None
'at the helm'          in_phrases=False -> None
'behind the camera'    in_phrases=False -> None
'camera'               in_phrases=False -> None
'directed'             in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P57']
'wrote'                in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P58']
'written'              in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P58']
'composed'             in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P86']
'director'             in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P57']
'filmmaker'            in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P57']
'screenplay'           in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P58']
'music'                in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P86']
'script'               in_phrases=True  -> ['http://www.wikidata.org/prop/direct/P58']
phrase_pattern_matches_directing= False
phrase_pattern_matches_helm= False
phrase_pattern_matches_camera= False
phrase_pattern_matches_writing= False
phrase_pattern_matches_composing= False
```

All five paraphrase forms are absent from `Parser.phrases`.
The canonical words for the same relations are present.

### Recorded probe P2 - canonical rewrite yields the right predicate

Command (one agent load; parses and answers five hand-rewritten questions):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -c "
from agent.cli import load_agent
agent = load_agent()
p = next(h.parser for h in agent.handlers if hasattr(h,'parser'))
cases = [
  (\"nominalisation directing\", \"Who did directed for 'Inception'?\"),
  (\"idiom helm\", \"Who was directed on 'Inception'?\"),
  (\"idiom camera\", \"Who is directed on 'Inception'?\"),
  (\"nominalisation writing\", \"Who did wrote for 'Inception'?\"),
  (\"nominalisation composing\", \"Who did composed for 'Inception'?\"),
]
for label, s in cases:
    q = p.parse(s)
    reply = agent.answer(s, 'probe2')
    print(f'{label:26} {s!r}')
    print(f'    predicate={q.predicate} direction={q.direction} error={q.error} reply={reply!r}')
"
```

Observed output:

```text
nominalisation directing   "Who did directed for 'Inception'?"
    predicate=http://www.wikidata.org/prop/direct/P57 direction=out error=None reply='The factual answer is: Christopher Nolan'
idiom helm                 "Who was directed on 'Inception'?"
    predicate=http://www.wikidata.org/prop/direct/P57 direction=out error=None reply='The factual answer is: Christopher Nolan'
idiom camera               "Who is directed on 'Inception'?"
    predicate=http://www.wikidata.org/prop/direct/P57 direction=out error=None reply='The factual answer is: Christopher Nolan'
nominalisation writing     "Who did wrote for 'Inception'?"
    predicate=http://www.wikidata.org/prop/direct/P58 direction=out error=None reply='The factual answer is: Christopher Nolan'
nominalisation composing   "Who did composed for 'Inception'?"
    predicate=http://www.wikidata.org/prop/direct/P86 direction=out error=None reply='The factual answer is: Hans Zimmer'
```

Each rewrite reaches the grounded predicate and the grounded answer.
The existing answer template needs no change.

### Recorded probe P3 - dataset form tally

Command (no agent load; tallies the 70 cases by input form and grounding relation):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -c "
import json, collections
rows=[json.loads(l) for l in open('evals/adversarial/d8-relation-paraphrases.jsonl') if l.strip()]
fam=collections.Counter(); form=collections.Counter(); rel=collections.Counter()
for r in rows:
    t=r['input']; g=r['grounding']['relation']
    if 'the directing' in t: f='nominalisation the directing'
    elif 'at the helm' in t: f='idiom at the helm of'
    elif 'behind the camera' in t: f='idiom behind the camera on'
    elif 'the writing' in t: f='nominalisation the writing'
    elif 'the composing' in t: f='nominalisation the composing'
    else: f='control existing phrasing'
    form[f]+=1
    if f=='control existing phrasing': fam['control']+=1
    elif 'directing' in f or 'helm' in f or 'camera' in f: fam['directing family']+=1
    elif 'writing' in f: fam['writing family']+=1
    else: fam['composing family']+=1
    rel[g]+=1
print('total', len(rows))
for k,v in form.most_common(): print(f'{v:3}  {k}')
for k,v in fam.most_common(): print(f'{v:3}  {k}')
for k,v in rel.most_common(): print(f'{v:3}  {k}')
"
```

Observed output (form, family, relation counts):

```text
total 70
 12  nominalisation the directing
 12  idiom at the helm of
 12  idiom behind the camera on
 12  nominalisation the writing
 12  nominalisation the composing
 10  control existing phrasing
 36  directing family
 12  writing family
 12  composing family
 10  control
 42  wdt:P57
 14  wdt:P58
 14  wdt:P86
```

## Failure shapes

The baseline report lists one reply cluster for all 60 failures: "relation word ignored (no_relation reply)" (`d8-relation-paraphrases-baseline.md:12`).
The failing-case table holds the same reply per case (`d8-relation-paraphrases-baseline.md:20-79`).
Probe P3 splits the 60 by input form:

| Sub-shape | Surface form | Relation | Count | Example id |
|---|---|---|---|---|
| S1 | `Who did the directing for 'X'?` | P57 | 12 | d8-relation-paraphrases-001 |
| S2 | `Who was at the helm of 'X'?` | P57 | 12 | d8-relation-paraphrases-002 |
| S3 | `Who is behind the camera on 'X'?` | P57 | 12 | d8-relation-paraphrases-003 |
| S4 | `Who did the writing for 'X'?` | P58 | 12 | d8-relation-paraphrases-004 |
| S5 | `Who did the composing for 'X'?` | P86 | 12 | d8-relation-paraphrases-005 |

Sum: 12 + 12 + 12 + 12 + 12 = 60, the failure count.
The same 60 roll up into three relation families.

| Family | Sub-shapes | Count |
|---|---|---|
| directing | S1 + S2 + S3 | 36 |
| writing | S4 | 12 |
| composing | S5 | 12 |

This matches the operator split (36 directing, 12 writing, 12 composing) and the manifest (`docs/design/adversarial/05-dataset-manifest.md:53`).
Every shape has the same reply shape: the `no_relation` sentence (`agent/nlg.py:42-43`).

## Ranked hypotheses

- H1: the paraphrase words never enter the relation phrase table, so `_find_predicates` returns `[]`.
  Test: P1 prints `in_phrases=False` and `phrase_pattern_matches_*=False` for all five forms.
  Reading `agent/parser.py:52-59`: `self.phrases` holds property labels plus `data/relations.json` synonyms only.
  Verdict: confirmed.
- H2: entity recognition fails, so the reply is `no_entity`.
  Test: the red repro shows `span=(27,36) candidates=['Q25188', ...]` and `error='no_relation'`, not `no_entity`.
  Verdict: rejected.
- H3: the `has_facts` gate (B5) blocks the query.
  Test: the red repro shows `predicates=[]`, and `Parser.parse` returns at `agent/parser.py:80-81` before the gate loop at `agent/parser.py:84-91`.
  Verdict: rejected.
- H4: a canonical rewrite would still fail, on word boundaries or collisions.
  Test: P2 rewrites each form and gets P57, P58, P86 with the grounded replies.
  Verdict: rejected.
- H5: the fix needs a new reply template in `nlg.py`.
  Test: P2 returns the existing `nlg.answer` sentence; the dataset forbids only the `no_relation` text (`evals/adversarial/d8-relation-paraphrases.jsonl:1`).
  Verdict: rejected.
- H6: the 10 control cases pass through words already in the table.
  Test: P1 shows `director`, `filmmaker`, `screenplay`, `composed`, `music` present; the repro for `-061` shows `predicates=['...P57']`.
  Verdict: confirmed, so the fix must not disturb the table.

## Root cause

Primary root cause: Phase 3 (relation detection) cannot see any paraphrase.
Boundary: B3 (Phase 2 -> Phase 3), `docs/design/adversarial/02-architecture-contracts.md:36-42`.

The evidence chain:

- `Parser.__init__` builds `self.phrases` from `lexicon.prop2lbl` and `agent/data/relations.json` (`agent/parser.py:52-57`).
- It compiles `self.phrase_pattern` from those keys only (`agent/parser.py:59`).
- `Parser._find_predicates` returns only pattern matches, with no fallback (`agent/parser.py:95-98`).
- `data/relations.json` holds `directed`, `wrote`, `composed` but not `directing`, `writing`, `composing`, `helm`, or `behind the camera` (`agent/data/relations.json:2-3,10`).
- `Parser.parse` sets `question.error="no_relation"` when `predicates` is empty (`agent/parser.py:80-81`).
- `FactualHandler.handle` maps that error to `nlg.no_relation` (`agent/handlers/factual.py:26-27`, `agent/nlg.py:42-43`).

The B4 sender assumption "the relation map is complete" is the same gap (`02-architecture-contracts.md:46`).
No relation ever reaches Phase 4, so the failure is upstream of B4.
The entity and link phases are correct, so the fix belongs at the relation-phrase boundary.

## Decision constraints

- Q14: nominalisations and idioms both rewrite to the canonical relation words (`00-questions.md:136`).
- Q14 examples: "the directing", "at the helm of", "behind the camera" -> directed; "the writing" -> wrote; "the composing" -> composed.
- Q3: `agent/preprocess.py` is the seam before `Parser.parse`; `parser.py` or `nlg.py` edits need a diagnosis that proves them necessary (`00-questions.md:114`).
- `02-architecture-contracts.md:95-96` names `FactualHandler.handle` line 21 (`self.parser.parse(text)`) as the single intercept site.
- The 60 red cases split 36 directing / 12 writing / 12 composing; the 10 controls pass and must stay (`07-cluster-index.md:25,101`).
- The dataset forbids "I'm not sure what you'd like to know", so `no_relation` must not fire for these cases (`evals/adversarial/d8-relation-paraphrases.jsonl:1`).
- Q8 invariant: mask the entity mention before any relation edit (`00-questions.md:119-122`); a paraphrase word inside a title must not be rewritten.
- Q12 fixes quote normalisation as a neighbour concern (`00-questions.md:129`).
- Hard rules: no edits to the dataset, the harness, or the eval contracts; failing cases stay.

## Suggested fix

Direction, preferring the Q3 seam:

1. Add `agent/preprocess.py` (the module does not exist today).
2. Add `normalize_relations(text) -> str`.
   - Mask quoted spans first, so title text is never rewritten.
   - Apply rewrites longest first, one surface form each:
     - "at the helm of" -> "directed"
     - "behind the camera" -> "directed"
     - "the directing" -> "directed"
     - "the writing" -> "wrote"
     - "the composing" -> "composed"
   - Restore the masked spans unchanged.
3. Call it at the seam `agent/handlers/factual.py:21`, before `self.parser.parse(text)`.

Justify the seam: Q3 names it (`00-questions.md:114`), and `02-architecture-contracts.md:95-96` names the call site.
Justify no `parser.py` edit: P1 shows `directed`, `wrote`, `composed` already key `Parser.phrases`, so the rewrite supplies the missing phrase upstream of B3.
Justify no `lexicon.py` or `nlg.py` edit: the rewrite uses `Lexicon` labels as-is, and P2 reuses the existing answer template.
Justify no handler logic beyond the call line: the handler keeps its current dispatch (`agent/handlers/factual.py:20-37`).

Rejected alternative: add the five paraphrase words to `agent/data/relations.json`.
`relations.json` values feed `phrase_pattern` directly (`agent/parser.py:55-59`), so that would also work.
It sits outside the operator's chosen seam, and Q14 frames the change as a rewrite.
Record this as an open question for the operator.

## Regression seam

Primary command and bar:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d8-relation-paraphrases.jsonl   # -> >= 56/70, target 70/70
```

Required outcomes for this dataset:

- All 60 failing cases (`-001` to `-060`) return the grounded answer, not the `no_relation` sentence.
- The 10 controls (`-061` to `-070`) stay passing.

No-regression commands:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl              # -> 508/508
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl              # -> 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t1-negation.jsonl    # masking family
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl  # recognition family
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t5-partial-titles.jsonl   # resolution family
```

Golden cases at risk:

- "director of photography" must keep resolving to P344 (Wally Pfister), a documented control (`docs/design/notes-adversarial-factual-questions-discovered.md:95`).
  P344 carries that label (`docs/design/adversarial/eval/s1-domain-probe.log:12`), so the rewrite must not touch "director".
- The 17 stage-2 cinematographer rows (for example `evals/stage2_factual.jsonl:17`) must stay green.
- The stage-2 "wrote the screenplay" rows (for example `evals/stage2_factual.jsonl:1`) and "composed the music" rows (for example `evals/stage2_factual.jsonl:26`) must stay green.
- Quoted titles that contain a paraphrase word must survive unchanged (Q12, `00-questions.md:129`).
- Stage 1 (9/9) and its SPARQL path must stay untouched (`02-architecture-contracts.md:79`).

## Risks and open questions

- Semantics of "behind the camera": in this KG P344 is "director of photography", but Q14 and the dataset map the idiom to P57.
  Confirm the operator accepts the P57 mapping.
- Cases `-021` to `-029` expect two labels, including the noisy label "Lelly Wechawsku" (`evals/adversarial/d8-relation-paraphrases.jsonl:21`).
  Fix-time check: confirm the answer rows hold both labels, or 7 cases stay red.
- A naive text rewrite can corrupt a title that contains a paraphrase word.
  Quote masking is required, and it needs the same quote handling as `Parser._find_entity` (`agent/parser.py:102`).
- Placement: preprocess sees the raw text before the `APPROACH_PREFIX` strip (`agent/parser.py:64`).
  Confirm the two edits compose and no prefix text carries a paraphrase word.
- The `relations.json` extension is the simpler alternative.
  It bypasses the operator's seam, so it needs explicit approval.
- `pytest` is not installed in the venv (Q4), so verification runs through `agent.eval` only.
- The exact rewrite targets must stay in `Parser.phrases`, or Phase 3 regains the empty list.
  A small guard test at fix time should assert membership for the five canonical words.
