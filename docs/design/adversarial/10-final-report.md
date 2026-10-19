# S10 - final report

State: S10.
Terminal state: S10 success.
S11 was not entered because every gate G0 to G9 passed.
Post-S10 note: the operator requested a negation extension after this report.
The T1 dataset grew to 121 cases and the agent gained the corresponding behavior; see `12-negation-extension.md` and `eval/extension/`.

## Mission outcome

Goal: answer adversarial question forms with the fully symbolic movie-QA agent through a new normalisation layer before `Parser.parse`, proven with grounded datasets and reproducible eval numbers.
Result: all ten adversarial types pass at rate 1.00, and the happy path matches its baseline exactly.

| Metric | Baseline | Final | Evidence log |
|---|---|---|---|
| Adversarial suite (10 types) | 172/607 (iter0) | 607/607 (iter1) | `eval/iter0/`, `eval/iter1/` |
| Stage 2 factual (happy path) | 508/508, exit 0 | 508/508, exit 0 | `eval/baseline-stage2.log`, `eval/final-stage2.log` |
| Stage 1 SPARQL | 9/9, exit 0 | 9/9, exit 0 | `eval/baseline-stage1.log`, `eval/final-stage1.log` |
| Unit tests | 74 cases (Stage 2) | 127 passed | `eval/final-pytest.log` |
| Dataset checker | - | `datasets OK` | `eval/s5-check.log` |

No runtime LLM call was added.
No new runtime dependency was added: the seam uses `rapidfuzz` 3.14.6, which was already in `requirements.txt` and already used by the parser.
`requirements.txt` is unchanged (`git diff bbab868..HEAD` shows no change).

## Deliverables

| Artifact | Content |
|---|---|
| `agent/preprocess.py` (new) | normalisation layer: quote repair, clause strip, mention resolution, subvention clarify, two-mention clarify, negation masking, claim detection, paraphrase rewrites, rewrite priority |
| `agent/handlers/factual.py` | plan wiring: claim, clarify, parse, negated complement |
| `agent/sparql_builder.py` | `complement` and `claim` templates; count film filter limited to film credits from the film side |
| `tests/test_preprocess.py` (new) | 25 rule cases; `tests/test_factual.py` and `tests/test_sparql_builder.py` extended |
| `evals/adversarial/*.jsonl` | 10 grounded datasets, 607 cases, frozen since S5 |
| `scripts/adversarial/` | build, check, verify, repro, and iteration-runner scripts |
| `docs/design/adversarial/00..10` | questions, plan, domain model, contracts, specs, manifest, cluster index, fix log, scoreboard, this report |
| `docs/design/adversarial/diagnosis/` | 10 diagnosis reports, one per cluster |
| `docs/design/adversarial/eval/` | iter0 baseline logs, S7 repro log, iter1 logs, final verification logs |

The golden datasets `evals/stage1_sparql.jsonl` and `evals/stage2_factual.jsonl` are unchanged.
The diff from the operator baseline commit adds only the ten new `evals/adversarial/` files under `evals/`.
`agent/eval.py` semantics are unchanged; `scripts/adversarial/run_iter.py` imports its `passes` function.

## Per-type results

| Type | iter0 | iter1 | Rate | Verdict |
|---|---|---|---|---|
| t1-negation | 8/64 | 64/64 | 1.00 | PASS |
| t2-subvention | 24/60 | 60/60 | 1.00 | PASS |
| t3-quote-shapes | 37/57 | 57/57 | 1.00 | PASS |
| t4-typos | 39/60 | 60/60 | 1.00 | PASS |
| t5-partial-titles | 20/51 | 51/51 | 1.00 | PASS |
| d1-count-class | 6/63 | 63/63 | 1.00 | PASS |
| d2-multiple-mentions | 10/65 | 65/65 | 1.00 | PASS |
| d3-trailing-superlative | 18/55 | 55/55 | 1.00 | PASS |
| d5-yes-no | 0/62 | 62/62 | 1.00 | PASS |
| d8-relation-paraphrases | 10/70 | 70/70 | 1.00 | PASS |

Threshold check: every type is above the required 0.8.
Failure accounting: the iter1 logs hold zero `FAIL` lines.

## Decision compliance

| Decision | Answer | Implementation | Evidence |
|---|---|---|---|
| Q1 | Always compute the complement, regardless of size | `sparql_builder.complement`; handler runs it for negated lookups | t1 64/64 |
| Q2 + Q15 | Prominence ranking for partials; clarify only when no film candidate exists | `preprocess._resolve` family ranking (films first, then degree) | t5 51/51 |
| Q3 | `agent/preprocess.py` seam before `Parser.parse` | new module; `parser.py` and `nlg.py` untouched | `git diff --stat` |
| Q4 | `pytest` into `.venv` only | `requirements.txt` unchanged | `git diff bbab868..HEAD -- requirements.txt` (empty) |
| Q5 | Baseline commit first, then worktree | baseline commit `bbab868` on `factual_approach` | `git log bbab868` |
| Q6 | Up to 5 new types by impact | D2, D3, D5, D8, D1 carried to full datasets | `05-dataset-manifest.md` |
| Q7 | Fuzzy only at unique best >= 0.85 | `preprocess._fuzzy_core` | t4 60/60 |
| Q8 | One-level negation; mask entity spans | `_shield` masks resolved mentions before `NEGATION.search`; no double-negation path | t1 64/64, masking tests |
| Q9 | Complement universes = relation domains | film side `wdt:P31 wd:Q11424`; person side objects of the credit property | `test_complement_directions` |
| Q10 | Rank inside article-stripped families | `strip_article` + `core2ent` + film-first degree rank | t4 and t5 at 1.00 |
| Q11 | Short-word fuzzy at 0.80 with a 0.05 gap | `_fuzzy_core` uses 0.80 for cores up to 6 chars, 0.85 longer | t4 60/60 |
| Q12 | Full quote normalisation; apostrophes inside words stay | `_normalise_quotes`, `_quoted_spans`, `_canonical` | t3 57/57 |
| Q13 | Reply shape "The factual answer is: Yes/No" | `nlg.answer(["Yes"])`; no new nlg function | d5 62/62 |
| Q14 | Paraphrases rewrite to canonical relation words | `PARAPHRASES` in `_apply_paraphrases` | d8 70/70 |
| Q16 | Two title mentions produce the clarification reply | `_two_film_sentences` -> `nlg.no_entity()` | d2 65/65 |

## Deviations and limitations

Full detail and evidence: `docs/design/adversarial/08-fix-log.md`.

1. The "prefix siblings" part of Q15 was dropped after measurement: it hijacked generic words and caused 27 golden failures; T5 stays 51/51 without it.
2. The D2 rule is sentence-scoped: clarification fires when film mentions sit in two different sentences; this keeps the golden "Who directed Her and Interstellar?" case green.
3. Sub-run mentions never rewrite the text; they still count for D2 and still mask negation words.
4. Rewriting quotes only the most prominent mention class (quoted, multi-word, capitalised, lowercase single word); this keeps the paraphrase verb "made" from hijacking the entity.
5. Q14 stands as decided: "behind the camera" rewrites to "directed", although the KG also uses P344 for that phrase.
6. The `no_facts` error path is unchanged for negated questions; a negated question about an entity with no facts still reports the missing fact.
7. The complement reply can be large and truncates deterministically at `Settings.max_fetch_rows` (10,000); Q1 accepted this risk.
8. Three discovered types stay deferred with recorded reason: D4 (mention character folding), D6 (date literal time part), D7 (glued tokens); evidence stays in `docs/design/notes-adversarial-factual-questions-discovered.md`.

## Reproduction

Run from the worktree root with the venv interpreter `/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python`:

1. Unit tests: `python -m pytest -q` -> 127 passed.
2. Happy path: `python -m agent.eval evals/stage2_factual.jsonl` -> 508/508, exit 0.
3. Stage 1: `python -m agent.eval evals/stage1_sparql.jsonl` -> 9/9, exit 0.
4. Adversarial suite: `python scripts/adversarial/run_iter.py --out docs/design/adversarial/eval/iter1` -> 607/607.
5. Dataset check: `python scripts/adversarial/check_datasets.py` -> 10 files checked, `datasets OK`.

## FSM ledger

| State | Commit | Evidence |
|---|---|---|
| S0 | `f3e8d0d` | `00-questions.md`, `PLAN.md` |
| S1 | `c59cbce` | `01-domain-model.md` |
| S2 | `4e4dfdb` | `02-architecture-contracts.md` |
| S3 | `971168a` | `03-known-types-spec.md` |
| S4 | `11a9b4b` | `notes-adversarial-factual-questions-discovered.md` |
| S5 | `c91bdcf` | `evals/adversarial/`, `05-dataset-manifest.md` |
| S6 | `a234cd6` | `eval/iter0/` |
| S7 | `7a6f6c1` | `07-cluster-index.md`, `diagnosis/` |
| S8 | `1b52a59` | `08-fix-log.md`, `eval/iter1/` |
| S9 | `f0b991e` | `09-scoreboard.md` |
| S10 | this commit | this report |

Initial work stays on the operator baseline commit `bbab868` on `factual_approach`.
The branch `fix/adversarial-normalization` was created from it and holds S0 to S10.

## Cleanliness checks

- `git status` is clean after every state commit.
- Golden datasets unchanged; the only `evals/` additions are the ten adversarial files.
- No hardcoded question strings or answers in agent code; the diff grep is recorded in `08-fix-log.md`.
- No runtime LLM calls; the seam is pure text processing plus KG lookups.
- Every number in this report traces to a saved log under `docs/design/adversarial/eval/`.
