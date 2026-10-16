# c-d2-multi-mention - diagnosis

Cluster: `c-d2-multi-mention`.
Dataset: `evals/adversarial/d2-multiple-mentions.jsonl`.
Baseline: 10/65 passed, 55 failures (`docs/design/adversarial/eval/iter0/d2-multiple-mentions-baseline.md:5`).
Fix bar: pass rate >= 0.8, so at least 52/65 cases must pass.
Contract: Q16 says two title mentions return the clarification reply, and no answer is attempted (`docs/design/adversarial/00-questions.md:138`).

## Red repro

Repro command (from the `scripts/adversarial/capture_repros.py` docstring):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output, section `## c-d2-multi-mention` of `docs/design/adversarial/eval/s7-repros.log` (lines 273-296):

```text
--- d2-multiple-mentions-001
input: "I love 'Jaws'. Who directed 'Inception'?"
expected: ["I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"]
forbidden: ['The factual answer is', 'Steven Spielberg', 'Christopher Nolan']
span=(8, 12) candidates=['Q189505', 'Q6166233', 'Q1322449', 'Q2361723', 'Q333477']
rest_after_span="I love ' '. Who directed 'Inception'?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [handler] factual
  [question] Question(text="I love 'Jaws'. Who directed 'Inception'?", entity='Q189505', predicate='...P57', direction='out', kind='lookup', error=None)
  [sparql] SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q189505> <...P57> ?x ... } LIMIT 200
reply='The factual answer is: Steven Spielberg'

--- d2-multiple-mentions-002
input: "Who directed 'Jaws'? Who directed 'Inception'?"
span=(14, 18) candidates=['Q189505', 'Q6166233', 'Q1322449', 'Q2361723', 'Q333477']
rest_after_span="Who directed ' '? Who directed 'Inception'?" predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text="Who directed 'Jaws'? Who directed 'Inception'?", entity='Q189505', ... error=None)
reply='The factual answer is: Steven Spielberg'
```

Both repros show one span only: `(8, 12)` is "Jaws" and `(14, 18)` is "Jaws".
The span covers the first mention, and the second mention "Inception" stays in `rest_after_span`.
The reply is confident: `error=None`, so no safe failure fires.

### Recorded probe P1 - mention classification over all 65 cases

Command (heredoc; loads the agent once, parses every case, and labels the answered entity as `entities[0]` or `entities[1]`):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'EOF'
import json
from pathlib import Path
from agent.config import load_settings
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.parser import Parser
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
lex = Lexicon(kg); p = Parser(kg, lex)
rows = [json.loads(l) for l in Path("evals/adversarial/d2-multiple-mentions.jsonl").read_text().splitlines() if l.strip()]
tally = {}
for r in rows:
    q = p.parse(r["input"]); ents = r["grounding"]["entities"]
    cls = "no_entity" if q.error == "no_entity" else ("first" if q.entity == ents[0] else ("second" if q.entity == ents[1] else "other"))
    tally[cls] = tally.get(cls, 0) + 1
print(tally)
EOF
```

Observed output:

```text
{'first': 49, 'second': 6, 'other': 0, 'no_entity': 10}
```

The 49 + 6 = 55 failures; the 10 `no_entity` cases are the passing cases.

### Recorded probe P2 - full eval run

Command:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d2-multiple-mentions.jsonl
```

Observed output (tail): `10/65 passed. Latency: median 0.00 s, max 0.01 s`.
The current tree matches the recorded baseline.

### Recorded probe P3 - recognition internals for one pass and one failure

Command: the P1 setup, plus a `cap_hits(text)` replay of the capitalised-span pass. It prints each label match with its `_inside_longer_title` value.

Observed output:

```text
INPUT: 'I love The Matrix. Who directed The Godfather?'
  words: ['I', 'love', 'The', 'Matrix.', 'Who', 'directed', 'The', 'Godfather?']
  _find_entity -> ((0, 0), [])
  parse.error -> no_entity | entity -> None
  first cap-pass matches (needs_capital, phrase, span, guard):
      (True, 'The Matrix', (7, 17), True)
      (True, 'The Godfather', (32, 45), False)

INPUT: 'I love Titanic. Who directed The Matrix?'
  words: ['I', 'love', 'Titanic.', 'Who', 'directed', 'The', 'Matrix?']
  _find_entity -> ((29, 39), ['Q83495', 'Q13014087', 'Q33140061'])
  parse.error -> None | entity -> Q83495
  first cap-pass matches (needs_capital, phrase, span, guard):
      (True, 'The Matrix', (29, 39), False)
      (True, 'Titanic', (7, 14), True)

INPUT: "I love 'Jaws'. Who directed 'Inception'?"
  _find_entity -> ((8, 12), ['Q189505', 'Q6166233', 'Q1322449', 'Q2361723', 'Q333477'])
  parse.error -> None | entity -> Q189505
```

P3 shows the mechanism for the split.
Case 018 ("The Matrix" first) fails safely, because the guard returns `True` when "Who" follows.
Case 028 ("Titanic" first) answers the second mention, because the guard returns `False` when "directed" precedes.
Case 001 answers through the quoted pass at the first quoted title.

## Failure shapes

The baseline report lists one reply cluster, "answered instead of clarifying", for all 55 failures (`d2-multiple-mentions-baseline.md:10-14`).
The failing-case table already holds the reply per case (`d2-multiple-mentions-baseline.md:18-74`).
Probe P1 splits the 55 by which mention the reply answers:

| Sub-shape | Definition | Count | Evidence |
|---|---|---|---|
| S1 | reply answers the first mention (X) | 49 | P1 `first` |
| S2 | reply answers the second mention (Y) | 6 | P1 `second` |

Sum: 49 + 6 = 55, the failure count.

The same 55 split by input form:

| Form | Template | Count | Answered |
|---|---|---|---|
| A | `I love 'X'. Who directed 'Y'?` | 13 | first |
| B | `Who directed 'X'? Who directed 'Y'?` | 13 | first |
| E | `Who wrote 'X'? Also, who directed 'Y'?` | 13 | first |
| D | `Someone told me X is great. Who directed Y?` | 13 | 10 first, 3 second |
| C | `I love X. Who directed Y?` | 3 | second |

Sum: 13 + 13 + 13 + 13 + 3 = 55.
The six S2 cases are `-028`, `-029`, `-033`, `-034`, `-043`, `-044`.
The C form has 13 cases in total: 10 pass and the 3 S2 cases above.
The `grounding.entities` list gives X first and Y second (`evals/adversarial/d2-multiple-mentions.jsonl:1`).
Reply values alone cannot always separate X from Y: Interstellar and Batman Begins share the director Nolan.
P1 resolves those cases by the parsed entity, not by the reply text.

## Ranked hypotheses

- H1: Phase 1 returns a single mention, so a two-mention question answers one mention.
  Test: P1 parses every case and finds one entity; no case reports two mentions.
  Reading `agent/parser.py:100-147`: `_find_entity` returns one `(span, candidates)` pair.
  Verdict: confirmed.
- H2: `Parser.parse` consumes that single mention and never checks for a second.
  Test: reading `agent/parser.py:63-93`: `parse` calls `_find_entity` once at line 66.
  The only clarification path is `error='no_entity'` at `agent/parser.py:67-69`.
  Verdict: confirmed.
- H3: the 10 passing C cases pass by accident through `_inside_longer_title`, not by a Q16 rule.
  Test: P3 records `_find_entity -> ((0, 0), [])` for case 018, and `guard=True` for "The Matrix".
  Case 018's neighbour "Who" is capitalised, so the guard fires at `agent/parser.py:158`.
  Verdict: confirmed.
- H4: the 6 S2 cases answer the second mention. The guard is gated on `needs_capital`, and the left neighbour is a relation word.
  Test: P3 records `guard=False` for "The Matrix" in case 028; "directed" is a relation word (`agent/parser.py:152-155`).
  The capitalised pass matches "The Matrix" at `n=2` before "Titanic" at `n=1` (`agent/parser.py:109`).
  Verdict: confirmed.
- H5: the quoted pass answers the first quoted title, so quoted forms always answer X.
  Test: P3 records `_find_entity -> ((8, 12), [...Q189505])` for case 001; the first quoted hit wins (`agent/parser.py:102-105`).
  P1 attributes 39 A/B/E cases to the first mention.
  Verdict: confirmed.
- H6: a lexicon or linking gap causes the failure.
  Test: every answered entity resolves to a real film with facts; P2 shows no `no_facts` reply.
  Verdict: rejected.
- H7: the `has_facts` gate (B5) causes the wrong answer.
  Test: all 55 replies are real answer values from the first or second film.
  Verdict: rejected.

## Root cause

Primary root cause: Phase 1 (Entity recognition) returns at most one entity mention, and no phase counts title mentions.
Boundary: B1 (source -> Phase 1), from `docs/design/adversarial/02-architecture-contracts.md:20-26`.

The evidence chain:

- `Parser._find_entity` (`agent/parser.py:100-147`) returns one `(span, candidates)` pair.
  Its three return sites are the quoted pass (`agent/parser.py:105`), the capitalised pass (`agent/parser.py:125`), and the lower-case film fallback (`agent/parser.py:132`).
- `Parser.parse` (`agent/parser.py:63-93`) calls it once at `agent/parser.py:66` and answers that single entity.
- The only clarification path is `error='no_entity'`, set when `candidates` is empty (`agent/parser.py:67-69`).
- That empty list comes by accident from `Parser._inside_longer_title` (`agent/parser.py:149-163`), which is a subvention guard, not a multi-mention guard.
  Its `needs_capital` gate (`agent/parser.py:123`) and its relation-word walk (`agent/parser.py:152-155`) make the outcome depend on the neighbouring word.
- The guard walk tests only uppercase or stopword neighbours (`agent/parser.py:158`). It fires for "The Matrix" + "Who", but not for "directed" + "The Matrix".
- This is why case 018 passes and case 028 answers the second mention (P3).

The receiver assumption of B1 is that the question carries a single entity mention.
No code symbol represents "a second title mention", so the 55 failures follow directly from that missing concept.

## Decision constraints

- Q16: two title mentions return the clarification reply, and no answer is attempted (`docs/design/adversarial/00-questions.md:138`).
- Q16: the reply text is the fixed `no_entity()` sentence (`agent/nlg.py:38-39`); both films' answer values stay forbidden.
- The 10 C cases must stay passing (`docs/design/adversarial/07-cluster-index.md:22`, `85`).
- Q3a: the `agent/preprocess.py` seam runs before `Parser.parse`; `parser.py` or `nlg.py` edits need a proof (`docs/design/adversarial/00-questions.md:114`).
- `02-architecture-contracts.md:95-96` names `FactualHandler.handle` line 21 (`self.parser.parse(text)`) as the single intercept site.
- Q15: partial mentions resolve by prominence (`docs/design/adversarial/00-questions.md:137`); the fix must not reject that family.
- A1: the clarification text is the existing `no_entity()` sentence; no new template is needed (`docs/design/adversarial/00-questions.md:98`).

## Suggested fix

Direction, preferring the Q3 seam:

1. Add `agent/preprocess.py` with a film-mention scanner.
   `film_mentions(text, lex)` returns the list of distinct film-title spans in `text`.
   It scans quoted spans and capitalised or lower-case label n-grams, like `Parser._find_entity`.
   It keeps a span only when some candidate maps to a film (`Lexicon.is_film`, `agent/lexicon.py:43-44`).
   It keeps maximal, non-overlapping spans, and dedups by span, not by QID.
2. Add `normalize(text)` for Q12 quote handling as a neighbour concern (`agent/nlg.py` stays unchanged).
3. Call the scanner at the seam `agent/handlers/factual.py:21`, before `self.parser.parse(text)`:

   ```python
   if len(preprocess.film_mentions(text, self.lex)) >= 2:
       return nlg.no_entity()
   ```

   This reuses `no_entity()` (`agent/nlg.py:38-39`) and adds no template.

Justification for the handler edit: section 5.1 of `02-architecture-contracts.md` names the intercept site. It is `FactualHandler.handle` line 21, and Q3a permits the edit.
Justification for no `parser.py` edit: the scanner reuses `STOPWORDS` (`agent/parser.py:24`) and `Lexicon.lbl2ent`/`is_film`, so it needs no parser change.
If the operator rejects the small regex duplication, one `parser.py` edit is justified. Extract the token and quote scan into a shared helper. Both `_find_entity` and `preprocess` then call it.
`agent/lexicon.py` and `agent/nlg.py` need no edit.

## Regression seam

Primary command and bar:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d2-multiple-mentions.jsonl   # -> >= 52/65
```

Required outcomes for this dataset:

- All 55 failing cases return the `no_entity()` sentence, with no answer value.
- The 10 C cases stay passing: `-003`, `-008`, `-013`, `-018`, `-023`, `-038`, `-048`, `-053`, `-058`, `-063`.

No-regression commands:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl              # -> 508/508
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl              # -> 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/d5-yes-no.jsonl      # person + film, must NOT clarify
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t5-partial-titles.jsonl   # Q15 family
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t1-negation.jsonl     # B1 masking family
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl   # B1 subvention family
```

Golden cases at risk:

- `d5-yes-no` questions hold one person mention plus one film mention ("Did Christopher Nolan direct 'Inception'?").
  The film-only filter must not count the person, or the fix breaks that cluster.
- `evals/stage2_factual.jsonl` single-title cases must keep answering.
- The `no_entity()` text is shared with the `greeting` and `unknown-title` golden cases (`02-architecture-contracts.md:99`).
- Q15 partials in `t5-partial-titles.jsonl` must keep resolving.

## Risks and open questions

- The film-only filter is load-bearing.
  A person + film question ("Did Christopher Nolan direct 'Inception'?") must not count as two mentions.
- The contract says "two title mentions", not "two distinct titles".
  The behaviour for the same title twice ("Who directed Titanic? Who directed Titanic?") is unspecified.
- Nested labels ("The Matrix" contains "Matrix") must collapse to one maximal span, or one mention counts twice.
- An exact-label scanner misses Q15 partial core names ("matrix").
  A question with one full title and one partial would count one mention; the datasets do not test this.
- The scanner duplicates the token regex and the quote patterns of `_find_entity` (`agent/parser.py:102`, `107`).
  A shared helper avoids drift, but it is a `parser.py` edit.
- Apostrophe tokens ("Schindler's List") need the same token handling as `agent/parser.py:107`.
- Latency is unaffected: the scan is per message and adds no graph query (P2 median 0.00 s).
