# c-d5-yes-no - diagnosis

Cluster: `c-d5-yes-no`.
Dataset: `evals/adversarial/d5-yes-no.jsonl` (62 cases).
Baseline: 0/62 passed, 62 failures (`docs/design/adversarial/eval/iter0/d5-yes-no-baseline.md:5`).
Fix bar: pass rate >= 0.8, so at least 50/62 cases must pass (`docs/design/adversarial/eval/iter0/d5-yes-no-baseline.md:6`).
Contract: Q13 fixes the reply shape as "The factual answer is: Yes" or "The factual answer is: No" (`docs/design/adversarial/00-questions.md:135`).
Claim counts: 34 true claims expect `Yes` (28 P57 + 6 P58); 28 false claims expect `No` (probe P1).

## Red repro

Repro command, from the `scripts/adversarial/capture_repros.py` docstring (`scripts/adversarial/capture_repros.py:7-9`):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output, section `## c-d5-yes-no` of `docs/design/adversarial/eval/s7-repros.log` (lines 336-370):

```text
--- d5-yes-no-001
input: 'Did Christopher Nolan direct Inception?'
expected: ['the factual answer is: Yes']
forbidden: ['Christopher Nolan', 'John Ford']
span=(4, 21) candidates=['Q25191']
rest_after_span='Did   direct Inception?' predicates=['http://www.wikidata.org/prop/direct/P57']
  [handler] factual
  [question] Question(text='Did Christopher Nolan direct Inception?', entity='Q25191', predicate='http://www.wikidata.org/prop/direct/P57', direction='in', kind='lookup', error=None)
  [sparql] SELECT DISTINCT ?x ?label WHERE { ?x <http://www.wikidata.org/prop/direct/P57> <http://www.wikidata.org/entity/Q25191> . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200
reply='The factual answer is: Batman Begins, Dunkirk, Following, Inception, Insomnia, Interstellar, Oppenheimer, The Dark Knight, The Dark Knight Rises, The Dark Knight trilogy, and The Prestige'

--- d5-yes-no-002
input: "Did Christopher Nolan direct 'Inception'?"
expected: ['the factual answer is: Yes']
forbidden: ['Christopher Nolan', 'John Ford']
span=(30, 39) candidates=['Q25188', 'Q54888270', 'Q3797611']
rest_after_span="Did Christopher Nolan direct ' '?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [handler] factual
  [question] Question(text="Did Christopher Nolan direct 'Inception'?", entity='Q25188', predicate='http://www.wikidata.org/prop/direct/P57', direction='out', kind='lookup', error=None)
  [sparql] SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> <http://www.wikidata.org/prop/direct/P57> ?x . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200
reply='The factual answer is: Christopher Nolan'

--- d5-yes-no-003
input: "Did John Ford direct 'Inception'?"
expected: ['the factual answer is: No']
forbidden: ['Christopher Nolan', 'John Ford']
span=(22, 31) candidates=['Q25188', 'Q54888270', 'Q3797611']
rest_after_span="Did John Ford direct ' '?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [handler] factual
  [question] Question(text="Did John Ford direct 'Inception'?", entity='Q25188', predicate='http://www.wikidata.org/prop/direct/P57', direction='out', kind='lookup', error=None)
  [sparql] SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> <http://www.wikidata.org/prop/direct/P57> ?x . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200
reply='The factual answer is: Christopher Nolan'
```

The three repros show one span each: one entity mention only.
Case 002 quotes the film, so `_rank` picks the film and `direction='out'`.
The reply then names the film's real director, not the claim's truth value.
Case 003 asks a false claim ("John Ford"), yet the reply still names Nolan.
Case 001 has no quotes, so the person mention wins and `direction='in'`.
The reply then lists the person's films, so the claimed relation is never checked.

### Recorded probe P1 - pair ASK, mention coverage, and the parsed entity

Command:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -c '
import json, re, collections
from agent.cli import load_agent
agent = load_agent()
h = agent.handlers[1]
kg, lex, parser = h.kg, h.lex, h.parser
rows=[json.loads(l) for l in open("evals/adversarial/d5-yes-no.jsonl")]
# Probe A: pair ASK checks vs expected
ok=0
for r in rows:
    res = kg.query(r["grounding"]["check"])
    exp = r["expected"][0].split(": ")[-1]
    got = "Yes" if res else "No"
    ok += (got==exp)
print("PROBE-A pair ASK matches expected:", ok, "/", len(rows))
# Probe B: both grounding entity labels present in the input text
def norm(s):
    return re.sub(r"^the ","",s.casefold())
miss=[]; two=0
for r in rows:
    labs=[norm(lex.label(e)) for e in r["grounding"]["entities"]]
    text=norm(r["input"])
    present=[l for l in labs if l in text]
    if len(present)==2: two+=1
    else: miss.append((r["id"], labs, r["input"]))
print("PROBE-B both labels in text:", two, "/", len(rows))
for m in miss[:8]: print("   MISS", m)
# Probe C: how many entities the current parser returns per case
c=collections.Counter()
for r in rows:
    q=parser.parse(r["input"])
    c[q.entity is not None]+=1
print("PROBE-C parser returns an entity:", dict(c))
film=0; person=0; other=0
for r in rows:
    q=parser.parse(r["input"])
    if q.entity is None: continue
    if lex.is_film(q.entity): film+=1
    elif lex.is_human(q.entity): person+=1
    else: other+=1
print("PROBE-C entity type: film", film, "human", person, "other", other)
' 2>&1 | grep -v "^INFO"
```

Observed output:

```text
PROBE-A pair ASK matches expected: 62 / 62
PROBE-B both labels in text: 62 / 62
PROBE-C parser returns an entity: {True: 62}
PROBE-C entity type: film 51 human 11 other 0
```

Probe A: the pair ASK `ASK { <film> <predicate> <person> }` matches the expected `Yes` or `No` on all 62 cases.
Probe B: both mention labels are present in the input text on all 62 cases.
Probe C: the current parser returns exactly one entity on all 62 cases.
Probe C: 51 cases resolve to the film, and 11 resolve to the human.
The 51 film cases match the 51 name replies; the 11 human cases match the 11 list replies.

### Recorded probe P2 - current regression baselines in this worktree

Command:

```bash
cd /Users/diekgbbtt/.local/share/opencode/worktree/c6b606/fix/adversarial-normalization
P=/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python
$P -m agent.eval evals/stage1_sparql.jsonl 2>&1 | tail -2
$P -m agent.eval evals/stage2_factual.jsonl 2>&1 | tail -2
$P -m agent.eval evals/adversarial/d2-multiple-mentions.jsonl 2>&1 | tail -2
$P -m agent.eval evals/adversarial/d5-yes-no.jsonl 2>&1 | tail -2
```

Observed output:

```text
== stage1 ==
9/9 passed. Latency: median 0.00 s, max 1.01 s
== stage2 ==
508/508 passed. Latency: median 0.00 s, max 0.11 s
== d2 ==
10/65 passed. Latency: median 0.00 s, max 0.00 s
== d5 ==
0/62 passed. Latency: median 0.00 s, max 0.00 s
```

The goldens match the recorded baseline: stage1 9/9, stage2 508/508, d2 10/65, d5 0/62.

## Failure shapes

The baseline splits the 62 failures into ten reply clusters (`docs/design/adversarial/eval/iter0/d5-yes-no-baseline.md:10-23`).
Probe C splits the same 62 by the entity the parser returns.

Top-level split by parsed entity (probe C):

| Sub-shape | Definition | Count | Reply shape |
|---|---|---|---|
| S1 | parser resolves the film; `direction='out'` | 51 | one director name (the trap value) |
| S2 | parser resolves the human; `direction='in'` | 11 | the person's filmography list |

Sum: 51 + 11 = 62.
S1 matches the nine "trap value returned" clusters; S2 matches the "wrong answer: expected value absent" cluster.

S1 splits by trap value (`docs/design/adversarial/eval/iter0/d5-yes-no-baseline.md:10-21`):

| Trap value | Count | Example id |
|---|---|---|
| 'Christopher Nolan' | 18 | d5-yes-no-002 |
| 'Francis Ford Coppola' | 9 | d5-yes-no-010 |
| 'Lana Wachowski' | 8 | d5-yes-no-018 |
| 'Bong Joon-ho' | 3 | d5-yes-no-050 |
| 'Damien Chazelle' | 3 | d5-yes-no-054 |
| 'Jean Negulesco' | 3 | d5-yes-no-034 |
| 'Park Chan-wook' | 3 | d5-yes-no-030 |
| 'Steven Spielberg' | 3 | d5-yes-no-026 |
| 'the Wachowskis' | 1 | d5-yes-no-061 |

Sum: 18+9+8+3+3+3+3+3+1 = 51.
S2 holds the 11 list replies: `-001`, `-005`, `-009`, `-017`, `-025`, `-029`, `-033`, `-037`, `-045`, `-049`, `-053`.

The same 62 split by input form:

| Form | Count | Typical parse |
|---|---|---|
| `Did <person> direct <film>?` (no quotes) | 14 | 11 human (S2), 3 film (S1) |
| `Did <person> direct '<film>'?` | 28 | film (S1) |
| `Was '<film>' directed by <person>?` | 14 | film (S1) |
| `Was '<film>' written by <person>?` | 6 | film (S1) |

Sum: 14 + 28 + 14 + 6 = 62.
The three bare-form S1 cases are `-013`, `-021`, `-041`.
In those three the film is the longest label run, so it beats the person.

## Ranked hypotheses

- H1: no phase models the question as a claim over two entities.
  Test: reading `agent/parser.py:32-39`, `kind` has only lookup/count/earliest/latest.
  Reading `agent/handlers/factual.py:32-37`, the dispatch builds lookup, count, or superlative only.
  Reading `agent/sparql_builder.py:19-41`, every template has one entity, and none takes an object.
  Verdict: confirmed.
- H2: Phase 1 returns one mention, so the second mention is dropped.
  Test: probe C records one entity on all 62 cases; the repros show one span each.
  `Parser._find_entity` returns one `(span, candidates)` pair (`agent/parser.py:100-147`).
  Verdict: confirmed.
- H3: with one entity, Phase 4 answers a single-hop lookup, so no Yes/No is computed.
  Test: repro 002 (`direction='out'`) replies with Nolan; repro 001 (`direction='in'`) replies with the filmography.
  Probe C attributes 51 cases to the film and 11 to the human, matching the two reply shapes.
  Verdict: confirmed.
- H4: an ASK over the ordered pair decides every case.
  Test: probe A runs the grounding check `ASK { <film> <predicate> <person> }` and matches all 62 expected values.
  All triples order film first and person second (`evals/adversarial/d5-yes-no.jsonl:2`).
  Verdict: confirmed.
- H5: both mentions are recoverable from the text, so a preprocess detector can supply both.
  Test: probe B finds both entity labels in the input text on all 62 cases.
  Verdict: confirmed.
- H6: the failure is a quoting problem, so unquoted forms are the cause.
  Test: 48 quoted cases fail too; even quoted case 002 names the trap value.
  Verdict: rejected.
- H7: the direction rule (`agent/parser.py:90`) is the root cause.
  Test: case 002 already chooses the correct direct lookup (`direction='out'`) and still returns a name.
  The direction is correct for a lookup; the missing step is the claim check.
  Verdict: rejected as the root cause.
- H8: a lexicon or linking gap causes the failure.
  Test: every parsed entity is a real node with facts; no reply is `no_entity` or `no_facts` (probe C).
  Verdict: rejected.

## Root cause

Primary root cause: Phase 4 (Query construction) has no template for a two-entity claim, so it never computes a truth value.
Boundary: B4 (Phase 3 -> Phase 4), `docs/design/adversarial/02-architecture-contracts.md:44-51`.
Its receiver assumption is "the predicate and direction fill the template correctly"; no claim template exists to fill.

The evidence chain:

- Phase 1 returns one mention pair only.
  `Parser._find_entity` has three return sites, each a single `(span, candidates)` pair (`agent/parser.py:105`, `:125`, `:132`).
- Phase 3 masks exactly that one span, then detects the relation in the rest.
  `Parser.parse` builds `rest = text[:span[0]] + " " + text[span[1]:]` (`agent/parser.py:71`).
  The second mention's words stay inside `rest` and are ignored.
- The `Question` model cannot carry two entities or an answer kind.
  `Question.kind` is one of lookup/count/earliest/latest (`agent/parser.py:38`).
- Phase 4 dispatches on that single entity.
  `FactualHandler.handle` calls `lookup` or `count` or `superlative` (`agent/handlers/factual.py:32-37`).
- No query helper builds an ASK over a fixed pair.
  `sparql_builder.has_facts` binds one entity to a variable (`agent/sparql_builder.py:19-20`).
- The reply shape gap at B7 (phase 6 -> output) is the symptom, not the cause.
  `nlg.answer` already renders any string list (`agent/nlg.py:34-35`), so it can render `Yes` and `No` already.

So the 62 failures follow from one missing concept: a claim over an ordered entity pair.
The upstream condition sits at B3 (single-span masking), and the symptom surfaces at B7.

## Decision constraints

- Q13: the reply shape is exactly "The factual answer is: Yes" or "The factual answer is: No".
  Q13 also says to reuse the existing answer template, with no new `nlg` function (`docs/design/adversarial/00-questions.md:135`).
- Q3a: normalisation lives in `agent/preprocess.py` at the seam before `Parser.parse`.
  A `parser.py` or `nlg.py` edit needs a diagnosis proof (`docs/design/adversarial/00-questions.md:114`).
- Q16: the D2 clarification guard counts two title mentions only (`docs/design/adversarial/00-questions.md:138`).
  Each d5 case holds one person mention plus one film mention, so the D2 guard must not fire.
- The dataset forbids the film's real answer names and the claimed name, so a list answer cannot pass (`evals/adversarial/d5-yes-no.jsonl:2`).
- The fix bar is >= 0.8, so at least 50/62 cases must pass (`docs/design/adversarial/eval/iter0/d5-yes-no-baseline.md:6`).
- A5: Stage 1 SPARQL must keep 9/9 (`docs/design/adversarial/00-questions.md:102`).
- A7: Stage 2 must keep 508/508 (`docs/design/adversarial/00-questions.md:104`).
- Q15: ambiguous or partial mentions resolve by prominence through `Parser._rank` (`docs/design/adversarial/00-questions.md:137`).

## Suggested fix

Direction, preferring the Q3 seam:

1. Add `agent/preprocess.py` with a claim detector.
   `detect_claim(text, lex, parser)` returns a `Claim(film_qid, predicate_iri, person_qid)` or `None`.
   Trigger on a leading `Did`/`Was`/`Is`/`Does`/`Were` plus a detected relation phrase.
   Do not trigger on "directed by" alone; 22 Stage 2 superlative cases contain that phrase.
   Extract both mentions: the quoted-span pass (`agent/parser.py:102-105`) plus the capitalised label pass (`agent/parser.py:107-125`).
   Resolve each mention through `Lexicon.lbl2ent` and `Parser._rank` (`agent/lexicon.py:20`, `agent/parser.py:165-171`).
   Assign roles by type: the film is the P57/P58 subject, and the person is the object.
   This keeps the film/person roles correct for both question orders.
2. Call the detector at the seam `agent/handlers/factual.py:21`, before `self.parser.parse(text)`.
   When a `Claim` is found, run the pair ASK and return `nlg.answer(["Yes"] if holds else ["No"])`.
   `nlg.answer` already yields "The factual answer is: Yes" (`agent/nlg.py:34-35`), so Q13 is satisfied.
3. Add one helper to `agent/sparql_builder.py`: `ask_claim(film, predicate, person)`.
   It returns `ASK { <WD film> <predicate> <WD person> }`, mirroring `has_facts` with a fixed object (`agent/sparql_builder.py:19-20`).
   This is a Phase 4 change, and B4 is the boundary that lacks the claim template.
4. `agent/parser.py` needs no edit under this design, because the detector resolves both mentions itself.
   One optional edit is a `Question.kind="ask"` plus a pair field (`agent/parser.py:32-39`), if the operator prefers the generic path.
   `agent/lexicon.py` and `agent/nlg.py` need no edit.
5. On an unresolved mention, fall back to the existing safe failure `nlg.no_entity()` (`agent/nlg.py:38-39`).
   This keeps B1 honest and reuses an existing template.

Justification for the handler edit: section 5.1 of `02-architecture-contracts.md` names `FactualHandler.handle` line 21 as the intercept site.
Justification for the `sparql_builder.py` edit: the query layer is the phase that must express a claim, and no current template takes a pair.

## Regression seam

Primary command and bar:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/d5-yes-no.jsonl   # -> >= 50/62
```

Required outcomes for this dataset:

- All 34 true claims return "The factual answer is: Yes".
- All 28 false claims return "The factual answer is: No".
- The 11 list-reply cases now return Yes/No: `-001`, `-005`, `-009`, `-017`, `-025`, `-029`, `-033`, `-037`, `-045`, `-049`, `-053`.
- The 3 bare-form name cases now return Yes: `-013`, `-021`, `-041`.

No-regression commands:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl              # -> 508/508
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl              # -> 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d2-multiple-mentions.jsonl   # -> 10/65 stays, and d5 must NOT clarify
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d8-relation-paraphrases.jsonl  # -> control 061 stays green
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d1-count-class.jsonl   # -> 6/63 P57 controls stay
```

Golden cases at risk:

- `d8-relation-paraphrases-061` is the same quoted single-entity P57 lookup ("Who is the director of 'Inception'?") and must keep answering.
- The 22 Stage 2 cases with "directed by" are superlative lookups, not claims; the detector must skip them.
- Stage 2 holds no input that starts with `Did`/`Was`/`Is`/`Does`/`Were`, so the trigger is low-risk (grep count 0).
- The d2 clarification guard must count title mentions only, so a person plus film pair does not clarify.

## Risks and open questions

- Risk: a "directed by" substring trigger would capture 22 Stage 2 superlative cases.
  Key the trigger on the leading interrogative word plus a relation phrase.
- Risk: recognition can prefer the film over the person, as in the 3 bare-form cases (`-013`, `-021`, `-041`).
  The detector must resolve both mentions itself, not trust the parser's single pick.
- Risk: role order. All target triples put film first and person second, but the question order varies.
  Assign roles by `is_film`/`is_human`, never by position.
- Risk: the D2 title-only guard and the d5 claim detector both consume mentions.
  Keep the D2 guard on titles and the d5 detector on the claim surface form.
- Risk: a mention may resolve to several candidates.
  Reuse Q15 prominence through `Parser._rank` (`agent/parser.py:165-171`).
- Open question: Q13 allows "a defined refusal when the graph cannot check the claim", but this dataset holds no refusal case.
  Recommend the existing `nlg.no_entity()` sentence for an unresolved mention.
- Open question: whether to carry the claim in `Question` or to keep it inside `preprocess`.
  A preprocess-only path needs no `parser.py` edit and is the smaller diff.
- Open question: `capture_repros.py` prints the parser internals for one span.
  The claim detector should log both entities, so the S7 repro log stays meaningful.
