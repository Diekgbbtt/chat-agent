# c-d3-trailing - diagnosis

State: S7.
Cluster: `c-d3-trailing`.
Dataset: `evals/adversarial/d3-trailing-superlative.jsonl` (55 cases, 37 failures at baseline).
Baseline: 18/55 passed (32.7%).
Fix bar: pass rate >= 0.8, so at least 44/55 cases must pass.
Decision anchors: Q3 (seam) and the D3 dataset rule; Q12 is a neighbour concern.

## Red repro

Repro log: `docs/design/adversarial/eval/s7-repros.log`, section `## c-d3-trailing` (lines 299-332).
Capture command, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output for the red repro `d3-trailing-superlative-001` (log lines 301-310):

```
--- d3-trailing-superlative-001
input: "Who directed 'Batman Begins', the first film in the trilogy?"
expected: ['Christopher Nolan']
forbidden: ['no information']
span=(14, 27) candidates=['Q166262', 'Q2891561']
rest_after_span="Who directed ' ', the first film in the trilogy?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [handler] factual
  [question] Question(text="Who directed 'Batman Begins', the first film in the trilogy?", entity='Q166262', predicate='...P57', direction='out', kind='earliest', error=None)
  [sparql] SELECT ?x ?label (MIN(?d) AS ?date) WHERE { <...Q166262> <...P57> ?x . ?x wdt:P31 wd:Q11424 ; <...P577> ?d . ... }
  reply='Sorry, my knowledge graph has no information about the director of Batman Begins.'
```

Observed output for the red repro `d3-trailing-superlative-002` (log lines 312-321):

```
--- d3-trailing-superlative-002
input: "Who directed 'Batman Begins', the latest film I watched?"
span=(14, 27) candidates=['Q166262', 'Q2891561']
rest_after_span="Who directed ' ', the latest film I watched?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(..., entity='Q166262', predicate='...P57', direction='out', kind='latest', error=None)
  [sparql] SELECT ?x ?label (MAX(?d) AS ?date) WHERE { <...Q166262> <...P57> ?x . ?x wdt:P31 wd:Q11424 ; <...P577> ?d . ... }
  reply='Sorry, my knowledge graph has no information about the director of Batman Begins.'
```

Observed output for the green control `d3-trailing-superlative-005` (log lines 323-332):

```
--- d3-trailing-superlative-005
input: "Who directed 'Batman Begins', my favourite film?"
span=(14, 27) candidates=['Q166262', 'Q2891561']
rest_after_span="Who directed ' ', my favourite film?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(..., entity='Q166262', predicate='...P57', direction='out', kind='lookup', error=None)
  reply='The factual answer is: Christopher Nolan'
```

The baseline log `docs/design/adversarial/eval/iter0/d3-trailing-superlative.log` records the same 37 failures.

### Recorded probes

Probe 1, every case through the agent plus the parser `kind`, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
import json
from collections import Counter
from pathlib import Path
from agent.cli import load_agent
agent = load_agent()
parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))
rows = [json.loads(l) for l in Path("evals/adversarial/d3-trailing-superlative.jsonl").read_text().splitlines() if l.strip()]
# passes() applies the eval rule; print PASS/FAIL, kind, entity; tally failed kinds and contexts
PY
```

Observed output (key lines):

```
FAIL d3-trailing-superlative-001 kind=earliest entity=Q166262
FAIL d3-trailing-superlative-002 kind=latest entity=Q166262
FAIL d3-trailing-superlative-004 kind=latest entity=Q166262
PASS d3-trailing-superlative-005 kind=lookup entity=Q166262
...
PASS d3-trailing-superlative-052 kind=lookup entity=Q212775
PASS d3-trailing-superlative-055 kind=lookup entity=Q144483
total 55 failed 37 passed 18
failed kinds: {'earliest': 14, 'latest': 23}
failed by trailing context: {', the first film in the trilogy': 14, ', the latest film I watched': 14, ', the last movie I saw': 6, ', the newest one I own': 3}
```

Probe 2, the fix direction: strip the comma clause after the recognised title, then re-run:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'PY'
import re
from agent.cli import load_agent
agent = load_agent()
parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))
def strip_trailing(text, span):
    close = span[1]
    if close < len(text) and text[close] in "'\"":
        close += 1
    if re.match(r"\s*,", text[close:]):
        return text[:close].rstrip() + "?"
    return text
# for each case: print entity span, raw kind/reply, stripped kind/reply
PY
```

Observed output:

```
"Who directed 'Batman Begins', the first film in the trilogy?"
  entity_span (14, 27) kind earliest reply 'Sorry, my knowledge graph has no information about the director of Batman Begins.'
  stripped   "Who directed 'Batman Begins'?" kind lookup reply 'The factual answer is: Christopher Nolan'
"Who directed 'Batman Begins', the latest film I watched?"
  ... raw kind latest ... stripped kind lookup reply 'The factual answer is: Christopher Nolan'
"Who directed 'Batman Begins', the newest one I own?"
  ... raw kind latest ... stripped kind lookup reply 'The factual answer is: Christopher Nolan'
"Who directed 'Batman Begins', my favourite film?"
  ... raw kind lookup ... stripped kind lookup reply 'The factual answer is: Christopher Nolan'
"Who directed 'The Last Emperor'?"
  entity_span (14, 30) kind lookup ... stripped unchanged, reply 'The factual answer is: Bernardo Bertolucci'
"Who directed 'Schindler's List', the first film in the trilogy?"
  entity_span (14, 30) kind earliest ... stripped "Who directed 'Schindler's List'?" kind lookup reply 'The factual answer is: Steven Spielberg'
"Which movie directed by 'Sofia Coppola' has the earliest release date?"
  entity_span (25, 38) kind earliest ... stripped unchanged, reply 'The factual answer is: The Virgin Suicides'
```

Probe 2 shows the strip flips `kind` to `lookup` and yields the expected answer for every red shape.
The strip fires on the apostrophe title `Schindler's List`.
The strip skips the golden case `official-coppola-earliest`, because its superlative is not comma-led.

## Failure shapes

The 37 failures are one reply shape (`no_facts`, forbidden substring `no information`).
They split by the trailing context in the dataset, which also selects the kind.
Counts come from Probe 1 and agree with `iter0/d3-trailing-superlative.log`.

| Sub-shape | Trigger token | Kind | Count | Case ids |
|---|---|---|---|---|
| trailing "first" clause | `first` | earliest | 14 | 001, 006, 011, 016, 020, 023, 026, 029, 032, 035, 038, 042, 046, 049 |
| trailing "latest" clause | `latest` | latest | 14 | 002, 007, 012, 017, 021, 024, 027, 030, 033, 036, 039, 043, 047, 050 |
| trailing "last" clause | `last` | latest | 6 | 003, 008, 013, 018, 040, 044 |
| trailing "newest" clause | `newest` | latest | 3 | 004, 009, 014 |

Total: 37.

The 18 passing cases are 14 neutral contexts and 4 title controls.
The neutral ids are `005, 010, 015, 019, 022, 025, 028, 031, 034, 037, 041, 045, 048, 051`.
The control ids are `052-055`.
The build script `scripts/adversarial/build_datasets.py:765-768` names the contexts.
The red list starts with `", the first film in the trilogy"`; the green list is `", my favourite film"`.
Every red context carries a token in `LATEST` or `EARLIEST`; the green context carries none.

## Ranked hypotheses

Hypothesis 1 (primary): a superlative word in the trailing clause sets `Question.kind` to earliest or latest and overrides the lookup.
Test: the repro log shows `kind='earliest'` for 001 and `kind='latest'` for 002, with the correct entity.
Probe 1 shows all 37 failures have kind earliest or latest, and all 18 passes have kind lookup.
Verdict: confirmed.

Hypothesis 2: the trailing clause enters the entity span, so the wrong entity is linked.
Test: the repro log shows `span=(14, 27)`, which is exactly the quoted title.
Probe 1 shows the entity is the correct film (`Q166262` = Batman Begins) for every shape.
The reply names the correct title.
Verdict: rejected.

Hypothesis 3: the trailing clause breaks relation detection, so `predicates` is empty and the reply is `no_relation`.
Test: the repro log shows `predicates=['http://www.wikidata.org/prop/direct/P57']` for 001 and 002.
Verdict: rejected.

Hypothesis 4: the `has_facts` gate at `agent/parser.py:86-88` returns empty, so `no_facts` fires before the template.
Test: the repro log shows the superlative SPARQL is built and traced, at `agent/handlers/factual.py:39`.
The handler reaches line 39 only after the gate succeeds at `agent/parser.py:88`.
Verdict: rejected as primary; the empty result comes from the template film filter, a downstream effect of Hypothesis 1.

Hypothesis 5: the 4 title controls fail because `last` or `first` sits inside the title.
Test: Probe 1 shows `052-055` have `kind=lookup`, because the span covers the word.
Verdict: rejected; the controls already pass and must stay.

Hypothesis 6: `newest` is not a superlative, so case 004 fails for another reason.
Test: `LATEST` at `agent/parser.py:28` matches `newest`.
Probe 1 shows `004, 009, 014` have `kind=latest`.
Verdict: rejected.

Hypothesis 7: a `parser.py` edit is required, because the seam cannot recover the title.
Test: Probe 2 strips the comma clause outside the parser and flips every red shape to lookup, including the apostrophe title.
Verdict: rejected; the `agent/preprocess.py` seam suffices.

## Root cause

One primary root cause: Phase 3 reads the trailing clause as relation text.
The clause's superlative word then sets the query kind.
`Parser.parse` blanks only the entity span and keeps the trailing clause in `rest` (`agent/parser.py:71`).
The `EARLIEST` and `LATEST` regexes (`agent/parser.py:27-28`) then scan the whole `rest` (`agent/parser.py:75`).
A trailing `first`, `latest`, `last`, or `newest` sets `question.kind` to earliest or latest (`agent/parser.py:78`).
Phase 4 fills the film-only superlative template (`agent/sparql_builder.py:36-41`).
That template adds `?x wdt:P31 wd:Q11424` (`agent/sparql_builder.py:40`), which drops the human director, writer, or composer.
The result set is empty, so the handler returns `no_facts` (`agent/handlers/factual.py:45-47`, text from `agent/nlg.py:46-47`).
Phase: Phase 3, relation detection.
Boundary: B3 (Phase 2 -> Phase 3), per `02-architecture-contracts.md:36-42`.
B3's receiver assumption is that "the remaining words carry the relation phrase".
Here the remaining words also carry an incidental trailing clause, and its superlative word sets the kind.
B4 (`02-architecture-contracts.md:44-50`) is the downstream half: the template cannot express a person answer, so the lookup becomes `no_facts`.

Code symbols and locations:
- `Parser.parse` at `agent/parser.py:63-93`; `rest` build at `agent/parser.py:71`; kind override at `agent/parser.py:75-79`.
- `EARLIEST` at `agent/parser.py:27`; `LATEST` at `agent/parser.py:28`; the `newest` alternation sits in `LATEST`.
- `sb.superlative` at `agent/sparql_builder.py:36-41`; the film filter at `agent/sparql_builder.py:40`.
- Handler dispatch at `agent/handlers/factual.py:34-35`; execution at `agent/handlers/factual.py:39`; empty-set refusal at `agent/handlers/factual.py:46-47`.
- The quoted-label pass that a seam fix can reuse at `agent/parser.py:102-105`; `Lexicon.lbl2ent` at `agent/lexicon.py:20`.

## Decision constraints

- Q3 (`00-questions.md:114`): the normalisation layer is `agent/preprocess.py`, called before `Parser.parse`; `parser.py` or `nlg.py` edits need a diagnosis proof.
- The D3 dataset rule: the base lookup must run when a quoted title has trailing context.
  The trailing context must not enter the entity span or the relation text.
- The 14 neutral contexts (`, my favourite film`) and the 4 title controls must stay passing.
  The controls are `The Last Emperor`, `The Last Samurai`, `First Blood`, and `The Last of the Mohicans`.
- The 37 red cases forbid the substring `no information`, so the fix must restore the factual answer; no new reply template is allowed.
- Q12 (`00-questions.md:129`): apostrophes inside words are never quote delimiters; the title `Schindler's List` must survive.
- The 10 golden cases `official-coppola-earliest` and `ext-earliest-*` (`evals/stage2_factual.jsonl:4,489-498`) carry a genuine comma-less superlative after a quote; they must stay earliest.
- Stage 2 must stay at 508/508 and Stage 1 at 9/9 (`02-architecture-contracts.md:79-84`).
- A6: `agent/speakeasy_bot.py` stays untouched.

## Suggested fix

Create `agent/preprocess.py` and call it once at the Phase 3 seam, before `Parser.parse`.
The call site is `FactualHandler.handle` at `agent/handlers/factual.py:21` (`self.parser.parse(text)`).
`02-architecture-contracts.md:95-96` names this call as the single intercept point.

Algorithm:
1. Scan quote pairs with the greedy pattern at `agent/parser.py:102`, and accept the pair whose content lowercases to a `Lexicon.lbl2ent` key.
   This mirrors the quoted-label pass and keeps the apostrophe inside `Schindler's List` intact (Q12).
2. If the text after the closing quote matches optional spaces then a comma, delete from that comma to the end.
3. Re-append the terminal `?` and return the shortened string.

Then `Parser.parse` sees `"Who directed 'Batman Begins'?"`.
`rest` holds no superlative word, the kind stays `lookup`, and the handler runs the ordinary lookup at `agent/handlers/factual.py:37`.
Probe 2 predicts this rule fixes all 37 red cases.
Probe 2 also shows the rule leaves the neutral contexts and the 4 controls unchanged.

The rule keys on the comma, because the comma is the only signal that separates trailing context from a genuine post-quote superlative.
The golden `official-coppola-earliest` case has a genuine superlative right after the quote with no comma; the rule does not fire there.
No `parser.py`, `lexicon.py`, or `nlg.py` edit is needed, because the normalised text matches the existing quoted-label pass.
If the operator rejects the small duplication of the quoted-label scan, the equivalent guard is one line at `agent/parser.py:75`.
That guard would ignore a superlative match that follows a comma after the entity span.
Justify that parser edit only on that rejection, because Q3 prefers the seam.

## Regression seam

Primary dataset command, from the worktree root:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval -v evals/adversarial/d3-trailing-superlative.jsonl
```

Success: pass rate >= 0.8 (>= 44/55), with the 37 previously-failing ids now passing.
The 37 ids: `001-004, 006-009, 011-014, 016-018, 020, 021, 023, 024, 026, 027, 029, 030, 032, 033, 035, 036, 038-040, 042-044, 046, 047, 049, 050`.
The three reprod cases in the log are the first proof: `001`, `002`, `005`.
Cases `001` and `002` must answer `Christopher Nolan`; case `005` must keep answering `Christopher Nolan`.

Golden no-regression commands:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl   # 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl  # 508/508
```

Golden cases at risk (`evals/stage2_factual.jsonl`):
- `official-coppola-earliest` and `ext-earliest-*` (10 cases) carry a real superlative after a quote; they must stay earliest.
- `nolan-latest` and `nolan-first` use a superlative without a quote; they must stay latest and earliest.
- The 4 title controls `d3-trailing-superlative-052` to `-055` carry `last` or `first` inside the title; they must stay lookup.
- The 14 neutral cases carry no superlative; they must stay lookup.

Run the neighbour clusters, because they share the `agent/preprocess.py` seam:

```
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d5-yes-no.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d2-multiple-mentions.jsonl
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d8-relation-paraphrases.jsonl
```

Guards: the D5 quoted forms (`Was 'Inception' directed by ...?`) carry relation words after the quote with no comma; the strip must not fire.
The D2 two-mention forms must keep returning the clarification reply.
The D8 paraphrase controls must keep answering.

## Risks and open questions

- The comma rule is the main risk. A trailing superlative without a comma (for example `'X' his first film`) still breaks.
  The dataset and the build script use only comma forms, so Probe 2 covers every red case.
  Open question: must comma-less trailing contexts be handled? A noun-phrase detector would risk the 10 golden earliest cases.
- The strip duplicates the quoted-label pass at `agent/parser.py:102-105`.
  Open question: should the seam re-run `_find_entity` instead, at the cost of a second `_rank` (SPARQL) pass?
- A naive non-greedy quote regex cuts inside `Schindler's List` at the apostrophe.
  The greedy pattern or the lexicon check avoids this; both must be kept.
- The fix removes the tail from the parser input.
  The reply is rebuilt from the entity label, so the visible text does not change.
- If a future D5-like question puts the relation in a comma clause after the quote, the strip would drop the relation.
  No such case exists in the current corpus.
- The `superlative` template stays for genuine superlatives; the fix does not weaken it.
- Open question: should the seam limit the strip to a title followed by one of the listed contexts, instead of any comma?
  A closed list is safer but needs maintenance when the D3 rule grows.
