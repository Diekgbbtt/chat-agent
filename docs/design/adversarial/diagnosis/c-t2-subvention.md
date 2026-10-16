# c-t2-subvention - diagnosis

Cluster: `c-t2-subvention`.
Dataset: `evals/adversarial/t2-subvention.jsonl`.
Baseline: 24/60 passed, 36 failures (`docs/design/adversarial/eval/iter0/t2-subvention.md`).
Fix bar: pass rate >= 0.8, so at least 48/60 cases must pass.

## Red repro

Repro command (from the `scripts/adversarial/capture_repros.py` docstring):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
  2>&1 | tee docs/design/adversarial/eval/s7-repros.log
```

Observed output, section `## c-t2-subvention` of `docs/design/adversarial/eval/s7-repros.log` (lines 53-84):

```text
--- t2-subvention-001
input: 'Who directed looking tarzan?'
expected: ["I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"]
forbidden: ['Chris Buck', 'Kevin Lima']
span=(21, 27) candidates=['Q208696', 'Q27881730']
rest_after_span='Who directed looking  ?' predicates=['http://www.wikidata.org/prop/direct/P57']
  [question] Question(text='Who directed looking tarzan?', entity='Q208696', predicate='...P57', direction='out', kind='lookup', error=None)
  [sparql] SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q208696> <...P57> ?x ... } LIMIT 200
reply='The factual answer is: Chris Buck and Kevin Lima'

--- t2-subvention-002
input: "Who directed 'The tarzan within'?"
span=(18, 24) candidates=['Q208696', 'Q27881730']
rest_after_span="Who directed 'The   within'?" predicates=['http://www.wikidata.org/prop/direct/P57']
reply='The factual answer is: Chris Buck and Kevin Lima'

--- t2-subvention-003
input: 'Who wrote the screenplay for tarzan of the deep?'
span=(39, 47) candidates=['Q494367', 'Q5018929', 'Q7729541', 'Q28517137']
rest_after_span='Who wrote the screenplay for tarzan of  ?' predicates=['http://www.wikidata.org/prop/direct/P58']
reply='The factual answer is: Peter Benchley'
```

The span covers only the embedded title: `(21, 27)` is "tarzan", `(18, 24)` is "tarzan", `(39, 47)` is "the deep".
The `rest_after_span` value keeps the extra words, which proves the trim.
The reply is confident: `error=None`, so no safe failure fires.

### Recorded probe P1 - parser internals

Command (heredoc; loads the agent once through `load_settings` and `KnowledgeGraph.open`;
the script replays the quoted pass, the capitalised pass, and the fallback pass, and names the hit):

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python - <<'EOF'
import re
from agent.config import load_settings
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.parser import Parser, STOPWORDS
s = load_settings()
kg = KnowledgeGraph.open(s.graph_path, s.store_path, query_timeout_s=s.query_timeout_s,
                         max_fetch_rows=s.max_fetch_rows, workers=s.workers)
lex = Lexicon(kg); p = Parser(kg, lex)
inputs = ["Who directed looking tarzan?",
          "Who directed 'The tarzan within'?",
          "Who wrote the screenplay for tarzan of the deep?"]
def branch(text):
    quoted = []
    for pattern in (r"'(.+)'", r"'(.+?)'", r'"(.+?)"'):
        for m in re.finditer(pattern, text):
            if m.group(1).lower() in lex.lbl2ent:
                quoted.append((m.span(1), m.group(1)))
    words = [(m.start(), m.end()) for m in re.finditer(r"[\w'&:.!?-]+", text)]
    cap = []
    for needs_capital in (True, False):
        for n in range(min(len(words), 10), 0, -1):
            for i in range(len(words) - n + 1):
                start, end = words[i][0], words[i + n - 1][1]
                raw = text[start:end].rstrip(",")
                for phrase in dict.fromkeys((raw, raw.rstrip("?."), raw.rstrip("?.!'").removesuffix("'s"))):
                    tokens = phrase.split()
                    capitalised = any(t[0].isupper() or t[0].isdigit() for t in tokens)
                    if all(t.lower().strip("?!.") in STOPWORDS for t in tokens) and (i == 0 or not capitalised):
                        continue
                    if (needs_capital and not capitalised) or (n == 1 and not capitalised):
                        continue
                    if phrase.lower() in lex.lbl2ent:
                        guard = p._inside_longer_title(text, words, i, i + n - 1) if needs_capital else "NOT-CHECKED (gated by needs_capital at parser.py:123)"
                        cap.append((needs_capital, (start, start + len(phrase)), phrase, guard))
    fb = []
    for start, end in reversed(words):
        for phrase in dict.fromkeys((text[start:end], text[start:end].rstrip("?.,"), text[start:end].rstrip("?.!,"))):
            films = [e for e in lex.lbl2ent.get(phrase.lower(), []) if lex.is_film(e)]
            if films and phrase.lower() not in STOPWORDS:
                fb.append(((start, start + len(phrase)), phrase, "no guard at parser.py:127-132"))
    return quoted, cap, fb
for t in inputs:
    print("INPUT:", repr(t))
    print("  _find_entity ->", p._find_entity(t))
    q, c, f = branch(t)
    print("  quoted-pass hits:", q)
    print("  cap-pass hits:", c[:2])
    print("  fallback first hit:", f[0] if f else None)
    words = [(m.start(), m.end()) for m in re.finditer(r"[\w'&:.!?-]+", t)]
    span, cand = p._find_entity(t)
    idx = [k for k, (a, b) in enumerate(words) if a >= span[0] and b <= span[1]]
    if idx:
        print("  guard(observed span words %d..%d) = %s" % (idx[0], idx[-1], p._inside_longer_title(t, words, idx[0], idx[-1])))
    print()
EOF
```

Observed output:

```text
INPUT: 'Who directed looking tarzan?'
  _find_entity -> ((21, 27), ['Q208696', 'Q27881730'])
  quoted-pass hits: []
  cap-pass hits: []
  fallback first hit: ((21, 27), 'tarzan', 'no guard at parser.py:127-132')

INPUT: "Who directed 'The tarzan within'?"
  _find_entity -> ((18, 24), ['Q208696', 'Q27881730'])
  quoted-pass hits: []
  cap-pass hits: []
  fallback first hit: ((18, 24), 'tarzan', 'no guard at parser.py:127-132')
  guard(observed span words 3..3) = False

INPUT: 'Who wrote the screenplay for tarzan of the deep?'
  _find_entity -> ((39, 47), ['Q494367', 'Q5018929', 'Q7729541', 'Q28517137'])
  quoted-pass hits: []
  cap-pass hits: [(False, (39, 47), 'the deep', 'NOT-CHECKED (gated by needs_capital at parser.py:123)')]
  fallback first hit: ((29, 35), 'tarzan', 'no guard at parser.py:127-132')
  guard(observed span words 7..7) = False
```

Probe P1 shows two distinct recognition paths and the guard value for each.
Case 001 has no guard line because its token "tarzan?" ends past the span, so no word indexes sit inside the span.

### Recorded probe P2 - full eval run

Command:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl
```

Observed output (tail): `24/60 passed. Latency: median 0.00 s, max 0.00 s`.
The current tree matches the recorded baseline.

### Recorded probe P3 - pass classification over the datasets

Command: the P1 setup, plus a `pass_of(text)` helper that replays the quoted pass, the
capitalised pass, and the fallback pass to name the pass that returns the observed span.

Observed output:

```text
evals/adversarial/t2-subvention.jsonl  {'fallback': 24, 'cap-lowercase': 12, 'quoted': 24}
evals/stage2_factual.jsonl             {'quoted': 338, 'cap-needs-capital': 165, 'cap-lowercase': 1, 'fallback': 1, 'fuzzy-or-other': 1, 'none': 2}
evals/adversarial/t1-negation.jsonl    {'cap-needs-capital': 38, 'quoted': 26}
evals/adversarial/t5-partial-titles.jsonl {'none': 16, 'quoted': 7, 'fallback': 13, 'cap-lowercase': 12, 'fuzzy-or-other': 3}
```

The 36 t2 failures split into 24 fallback matches and 12 `cap-lowercase` matches.
The 24 t2 controls resolve through the quoted pass.

## Failure shapes

The dataset has five input shapes: three crafted carriers (36 cases) and two control shapes (24 cases).
The baseline report lists one reply cluster, "answered instead of clarifying", for all 36 failures.
The failure splits into three sub-shapes by carrier and by which value the reply returns.

| Sub-shape | Input shape | Count | Reply | Trap list |
|---|---|---|---|---|
| A | `Who directed looking <title>?` | 12 | the embedded film's real director | hit (forbidden) |
| B | `Who directed 'The <title> within'?` | 12 | the embedded film's real director | hit (forbidden) |
| C | `Who wrote the screenplay for <title> of the deep?` | 12 | Peter Benchley, the writer of The Deep | absent |

Sum: 12 + 12 + 12 = 36, the failure count.
The cluster-index note groups these as "24 replies hit the trap list" (A + B) and "12 replies return another value absent from the trap list" (C).
P2 and the classification script confirm the 24 + 12 split.
The manifest gives the shape counts: "expected = clarification 36; real short-title controls 24" (`05-dataset-manifest.md` line 45).

## Ranked hypotheses

- H1: the lowercase one-word film fallback returns the embedded title with no guard.
  Test: P1 records `fallback first hit: ((21, 27), 'tarzan', 'no guard at parser.py:127-132')` for case 001.
  P3 attributes all 24 A/B cases to the fallback pass.
  Verdict: confirmed.
- H2: the capitalised-span pass finds the trailing carrier under `needs_capital=False`, and the guard is gated on `needs_capital`.
  Test: P1 records the cap-pass hit `(needs_capital=False, (39, 47), 'the deep', guard='NOT-CHECKED (gated by needs_capital at parser.py:123)')`.
  P3 attributes all 12 C cases to `cap-lowercase`.
  Verdict: confirmed.
- H3: `_inside_longer_title` is too weak to catch these carriers, even if wired to every return site.
  Test: P1 records `guard= False` for the observed span of cases 002 and 003.
  Reading `agent/parser.py:156-160`: the walk treats only a capitalised or stopword neighbour as "inside".
  The carrier words "looking", "tarzan", "within" are lowercase and are not stopwords.
  Reading `agent/parser.py:158`: a quote-prefixed token gives `word(k)[0].isupper()` false, so "'The" does not count.
  Verdict: confirmed.
- H4: a lexicon or fuzzy gap causes the failure.
  Test: P1 shows the quoted pass returns no hit and the fuzzy pass never runs, because an earlier pass returns first.
  The manifest states the carriers "score below 0.80 against the parser's fuzzy list" (`05-dataset-manifest.md` line 257).
  Verdict: rejected.
- H5: the `has_facts` gate (boundary B5) causes the wrong answer.
  Test: the fragments are real films (Tarzan Q208696, The Deep Q494367).
  Every baseline reply is a real answer value, never `no_facts`.
  Verdict: rejected.

## Root cause

Primary root cause: Phase 1 (Entity recognition) returns a sub-span of a longer, unlinkable phrase.
Boundary: B1 (source -> Phase 1), from `docs/design/adversarial/02-architecture-contracts.md`.
`Parser._find_entity` (`agent/parser.py:100-147`) has two unguarded or under-guarded return sites.

- The capitalised-span pass returns at `agent/parser.py:125`.
  Its subvention guard at `agent/parser.py:123` runs only when `needs_capital` is true.
  The `needs_capital=False` iteration can therefore return a lowercase carrier such as "the deep".
- The lowercase one-word film fallback returns at `agent/parser.py:132`.
  It has no guard for surrounding words.
  It matched "tarzan" inside "looking tarzan" and inside "'The tarzan within'".

The guard `Parser._inside_longer_title` (`agent/parser.py:149-163`) cannot help.
It models only capitalised runs (`word(k)[0].isupper()` at line 158).
A lowercase content word ends the walk, and a quote-prefixed token defeats the uppercase test.
The trimmed span then passes B2 silently.
`Parser._rank` (`agent/parser.py:165-171`) links the embedded title confidently, and the B5 `has_facts` gate (`agent/parser.py:86-88`) succeeds on the real fragment entity.

## Decision constraints

- Q2: a mention that carries extra words around a title is not the title.
  The crafted non-titles must return the `no_entity()` text (`agent/nlg.py:38-39`).
- Q12: quote normalisation collapses doubled quotes and strips inner whitespace.
  Apostrophes inside words are never delimiters.
  This is a neighbour concern for this cluster.
- Q3a: the `agent/preprocess.py` seam runs before `Parser.parse`.
  Edits to `parser.py` or `nlg.py` are allowed only when a diagnosis proves them necessary.
- Q15: partial mentions resolve by prominence, so the fix must not reject the Q15 family.
- Q10 and Q11: rank within article-stripped label families, and accept a unique short-word fuzzy match.
- A1: the T2 expected reply is the existing `no_entity()` sentence.
  No new template is needed.

### Q15 versus Q2 direction rule

Q15 resolves a mention that sits inside a title.
Q2 refuses a title that sits inside a mention.
The separating rule is the direction of the extra words:

- Extra words belong to the title (the mention is a core name, e.g. "matrix" -> "The Matrix").
  Widen the span to the title, by prominence (Q15).
- Extra words belong to the mention and no title covers them (e.g. "tarzan of the deep").
  Refuse with `no_entity` (Q2).

Concretely: widen only to a longer lexicon title that contains the matched tokens.
Refuse when the matched title is a strict sub-run of the mention run and no single title covers that run.

## Suggested fix

Direction, preferring the Q3 seam:

1. Add `agent/preprocess.py` with two functions.
   `normalize(text)` performs Q12 quote normalisation.
   `title_run(text, lex)` returns the maximal content-word run around a candidate label.
   The run excludes question words (`STOPWORDS`, `agent/parser.py:24-25`) and relation words (the `phrase_pattern`, `agent/parser.py:58-59`).
2. Call `preprocess.normalize` at the seam `agent/handlers/factual.py:21`, before `self.parser.parse(text)`.
   This is the single call site named in `02-architecture-contracts.md` section 5.1.
3. Wire `title_run` into `Parser._find_entity`.
   Apply the direction rule at the capitalised-pass return (`agent/parser.py:125`) and the fallback return (`agent/parser.py:132`).
   If the run carries extra content words and no title covers the run, return `((0, 0), [])`.
   An empty candidate list makes `parse` set `error='no_entity'` (`agent/parser.py:67-69`).
4. Keep the guard for the `needs_capital=True` pass, but apply it for both values of `needs_capital`.

Justification for the `parser.py` edit beyond the seam: the fix needs the token span, and only `_find_entity` holds it.
`02-architecture-contracts.md` section 5.3 states the T2 fix may "widen the guard in phase 1".
Q3a permits a `parser.py` edit when the diagnosis proves it necessary; H1-H3 prove it.
`agent/lexicon.py` needs no edit: reuse `lbl2ent`, `is_film`, and `ent2lbl` (`agent/lexicon.py:19-22`, `43-44`).
`agent/nlg.py` needs no edit: reuse `no_entity()` (`agent/nlg.py:38-39`).

## Regression seam

Primary command and bar:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t2-subvention.jsonl   # -> >= 48/60
```

Required outcomes for this dataset:

- All 36 crafted cases (A, B, C) return the `no_entity()` text.
- The 24 quoted controls keep answering: 12 `Who directed '<X>'?` and 12 `Tell me the director of '<X>'.`

No-regression commands:

```bash
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage2_factual.jsonl            # -> 508/508
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/stage1_sparql.jsonl            # -> 9/9
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t5-partial-titles.jsonl   # Q15 family
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m agent.eval evals/adversarial/t1-negation.jsonl         # B1 masking family
```

Golden cases at risk, from probe P3:

- `godfather-lowercase` ("who directed the godfather") uses the `cap-lowercase` path.
- `inception-lowercase` ("who directed inception") uses the fallback path.
- `evals/adversarial/t5-partial-titles.jsonl`: 13 fallback cases and 12 `cap-lowercase` cases depend on Q15 widening.
- `evals/adversarial/t1-negation.jsonl`: 38 `cap-needs-capital` cases exercise the same guard.

The fix must keep linking the Q15 partials ("dark knight", "basic instinct", "silence of the lambs") while refusing the T2 carriers.

## Risks and open questions

- A strict `title_run` test could reject valid Q15 partials.
  The regression seam above guards this, but the boundary cases are not all in the datasets.
- The seam lacks the token span, so `preprocess.py` and `parser.py` must share the relation-word pattern.
  Duplication risks drift; a shared helper in `preprocess.py` is safer.
- The Q15/Q2 direction rule has no case that is both a title inside a mention and a partial title.
  A future dataset could expose that boundary.
- The 12 C cases link the trailing carrier "The Deep" (Q494367), not the leading title.
  The guard must refuse the last title-like run, not only the first.
- `no_entity()` is shared with other safe-failure families (`greeting`, `unknown-title`).
  The fix must not change that text.
- Latency is unaffected (P2 median 0.00 s).
- Probe P3 is a code-reading replay; its fuzzy-or-other bucket is approximate, and it does not change the 24 + 12 split.
