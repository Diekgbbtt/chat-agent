# S0 - Clarifying questions (adversarial robustness, Stage 2 factual answers)

State: S0.
Branch at S0: `factual_approach`.
Tree at S0: modified `evals/stage2_factual.jsonl` (508 cases), modified `requirements.txt`, untracked `docs/`.

This batch covers the four required decision areas (T1 negation, T5 partial titles, pre-processing scope, test-install tolerance) plus four resource or environment decisions that block planning.
Each question has lettered options and a recommended default.
Reply `defaults` to accept every recommended option.
Reply with compact choices, for example `1a 2b 3a`.

## Grounding notes for the batch

- `evals/stage2_factual.jsonl` has 508 cases in the current tree (`wc -l`), and the operator reports 508/508 pass.
- `agent/nlg.py` has exactly three error templates: `no_entity()`, `no_relation()`, `no_facts()`.
- `agent/parser.py` line 123 already holds a partial subvention guard (`_inside_longer_title`), and the operator reports it is incomplete.
- `phases.md` line 106 says negation, yes/no, follow-ups and similar features were removed in Stage 2 and belong to Stage 3.
- `phases.md` line 111 states 74 unit tests exist under `tests/`, and `pytest` is not installed in `.venv` (brief, section 1.5).

## Batch

### Q1 - T1 negation: complement set or defined refusal?

- a) Defined refusal with one new reply template in `nlg.py` (Recommended). A question with a relation-scoped negation returns one fixed sentence, for example "I cannot answer negative questions.". The reply string becomes the expected value in the T1 dataset; the positive answer values become `forbidden`.
- b) Defined refusal, but reuse the existing `no_relation()` template. No `nlg.py` edit at all.
- c) Compute the complement set when a single template can bound it (for example count queries), else refusal.
- d) Keep answering positive (status quo). Rejected by the mission.

Default rationale: the complement set is unbounded (about 12k films for "not directed by X"), and the mission allows the defined-refusal answer.
Option (a) buys a clean, testable reply; the `nlg.py` edit is small and a diagnosis will justify it because no existing template fits.

### Q2 - T5 partial titles that stay ambiguous

- a) Cover-name match only when it is unique; otherwise a clarification reply (Recommended). Example: "handmaiden" maps to only "The Handmaiden"; "matrix" maps to several titles, so the agent asks which one.
- b) Ambiguous coverage picks the best-known film (films first, then most facts), like `Parser._rank` today.
- c) Refuse every partial title, even the unique case "handmaiden".
- d) Also match plain substrings of longer titles, not only article-stripped core names.

Default rationale: (a) is deterministic, matches the T5 example ("handmaiden" -> "The Handmaiden"), and never guesses between "The Matrix" and "The Matrix Reloaded".
Option (d) risks the T2-class wrong link and is out of the default scope.

### Q3 - Where does the normalisation layer live?

- a) New module `agent/preprocess.py`, called at the Stage 2 seam before `Parser.parse`; edits to `parser.py` or `nlg.py` only when a diagnosis proves them necessary (Recommended). This matches the mission's suggested seam.
- b) `agent/preprocess.py` only; `parser.py` and `nlg.py` stay untouched under all circumstances.
- c) Extend `Parser.parse` and `parser.py` directly, no new module.

Default rationale: (a) keeps the diff small and the boundary contracts in `docs/design/adversarial/02-architecture-contracts.md` honest; (b) is too strict for cases like the incomplete subvention guard (documented in S7 diagnosis flow); (c) spreads normalisation into parsing and hides it in debug traces.

### Q4 - Test installs and dev tooling tolerance

- a) Install `pytest` into `.venv` only, never in `requirements.txt` (Recommended). This is what the brief already says.
- b) Use stdlib `unittest` only; no new installs at all.
- c) Install `pytest` and add a `requirements-dev.txt` for it.

Default rationale: (a) follows the brief (section 1.5); the Nuvolos runtime and `requirements.txt` stay clean.

### Q5 - Handling your uncommitted changes

- a) Commit the current operator changes (`evals/stage2_factual.jsonl`, `requirements.txt`) as-is on `factual_approach` first, then create the worktree `fix/adversarial-normalization` (Recommended). The recorded 508-case baseline becomes a commit.
- b) Leave them uncommitted; I create the worktree and copy the two files into it.
- c) Leave them uncommitted; I work on a new branch in this same checkout.

Default rationale: the mission requires a clean tree at S10 and per-state commits; committing the operator's baseline first preserves it, and a worktree keeps this checkout untouched.

### Q6 - How many S4-discovered types to carry into datasets and fixes?

- a) Up to 5 new types, ranked by measured impact on the current agent (Recommended). This is the mission minimum.
- b) Up to 8 new types, all that measurably fail.
- c) Every discovered type, however many.

Default rationale: every full type costs 50+ cases, a baseline measurement, diagnosis, fix and re-eval; a cap keeps the loop inside the 3-iteration budget while still exceeding the minimum requirement of 5 new types.

### Q7 - T4 fuzzy-match acceptance policy

- a) Accept a fuzzy match only when it is the unique best label and the score passes the existing 0.85 cutoff; otherwise safe refusal (Recommended).
- b) Keep current behaviour and only repair cases where a typo links to the wrong label.
- c) Raise the cutoff to 0.90 and keep the best-match behaviour.

Default rationale: (a) makes "Godfahter" -> "The Godfather" work while a typo that could match several labels fails safely; (b) leaves the wrong-link class partially open; (c) still guesses among near labels.

### Q8 - Which negative surface forms trigger T1 behaviour?

- a) Any relation-scoped "no"/"not" form triggers T1; double negation normalises back to positive when it is unambiguous (Recommended). Example: "Which movies did Nolan not fail to direct?" -> positive director query.
- b) Every "no"/"not" form triggers T1, including double negation. Simpler and more conservative.
- c) Only the literal forms "did not" and "not" trigger T1; other forms stay as today.

Stated invariant for all options: negation words inside entity mentions ("Don't Look Up", "No Country for Old Men") must never trigger T1; the entity span is masked before negation detection.

Default rationale: (a) gives the best answers for forms the KG can in fact answer; (b) is acceptable if the operator prefers maximum conservatism, and it reduces test surface.

## Defaults fast path

Reply `defaults` to accept all recommendations: 1a, 2a, 3a, 4a, 5a, 6a, 7a, 8a.

## Non-blocking assumptions (recorded now, revisited if they break)

1. A1: The T2 unknown-title reply is the existing `no_entity()` sentence; the T2 dataset expects that text and forbids the substring film's answer values.
2. A2: Safe-failure families (T2 unknown, T4 no-match, T5 ambiguous under default 2a) all report via existing templates unless a diagnosis justifies one new template.
3. A3: The adversarial datasets live in `evals/adversarial/`, which extends the eval glob default `evals/*.jsonl` only if the operator runs a bare `python -m agent.eval`; type runs always pass the file explicitly.
4. A4: Latency guardrail: replies stay well below the eval's observed median (about 0.3-0.6 s in `phases.md` line 93 area); no caching is added.
5. A5: Stage 1 SPARQL questions must keep 9/9 in `evals/stage1_sparql.jsonl`.
6. A6: `agent/speakeasy_bot.py` is out of scope and stays untouched.
7. A7: The mission brief's "508 cases" equals the current tree's `evals/stage2_factual.jsonl`; the baseline run at S2 confirms the real number.

## Answers (operator replied 2026-10-16)

- Q1: **1a-modified - always compute the complement, regardless of size. One-level negation questions are in scope.**
  This supersedes all offered options.
  Consequence: negation needs a query-template branch (complement), not only pre-processing text surgery.
  The dataset encodes complement members as `expected` and positive-set members as `forbidden`.
  Accepted risk: the complement reply can be very large; `Settings.max_fetch_rows` is 10,000 (`agent/config.py` line 101), so replies truncate deterministically at that cap.
- Q2: 2a - unique core-name match links to the full title; ambiguous core names trigger the clarification reply.
- Q3: 3a - `agent/preprocess.py` seam before `Parser.parse`; `parser.py` or `nlg.py` edits only when a diagnosis proves them necessary.
- Q4: 4a - `pytest` installs into `.venv` only; `requirements.txt` stays unchanged.
- Q5: 5a - commit the operator changes on `factual_approach` first, then work in the `fix/adversarial-normalization` worktree.
- Q6: 6a - up to 5 new types, ranked by measured impact.
- Q7: 7a - fuzzy match accepted only when it is the unique best label at the 0.85 cutoff; otherwise safe refusal.
- Q8: **modified - double negation is fully out of scope and is disregarded.**
  One-level negation only.
  Stated invariant kept: negation words inside entity mentions ("Don't Look Up", "No Country for Old Men") must never trigger T1; the entity span is masked before negation detection.
  Consequence: T1 datasets never contain double-negation cases; no double-negation code path is written.

## S3 addendum (second decision batch, answered 2026-10-16)

- Q9: relation domains as complement universes - films `wdt:P31 wd:Q11424` (12,245), directors = objects of `wdt:P57` (6,109).
- Q10: rank within article-stripped label families - films first, then graph degree; "Godfather"/"Godfahter" resolve to The Godfather.
- Q11: unique short-word fuzzy match accepted (words <= 6 chars, score >= 0.80, gap >= 0.05) - "Jazws" -> Jaws.
- Q12: full quote normalisation - doubled quotes collapsed, inner whitespace stripped, apostrophes inside words are never quote delimiters.

All four took the recommended option.

## Decision consequences (bind S3 and S5)

1. T1 expected values: members of the complement set, verified absent from the positive set by SPARQL; `forbidden` values: members of the positive set.
2. T1 universe per relation is specified in `03-known-types-spec.md` (film universe for "which films", person universe for "who").
3. T1 needs a complement query branch in the query layer; the pre-processing layer classifies and extracts the relation scope, then hands a normalised question plus a negation flag downstream.
4. The clarification reply for ambiguous partials (2a) reuses the `no_entity()` sentence; no new template is required by default.
