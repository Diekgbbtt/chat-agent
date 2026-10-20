# Post-S10 extension - Negation: director syntax, actor/director universes, multi-film

State: post-S10.
The operator requested this extension after the S10 final report.
Scope: the T1 negation dataset grows from 64 to 121 cases, and the agent gains the behavior these cases need.
Evidence: `docs/design/adversarial/eval/extension/` (`build.log`, `check.log`, `verify.log`, per-type logs, `summary.md`, `stage2.log`, `stage1.log`, `pytest.log`).

## Request and interpretation

Operator request, in two parts.

1. Add negation queries of the form "What <director(s)> did not direct?" and "Which directors did not direct <film(s)>?".
2. Prevent further ambiguities between different RDF entities, since actors and directors are different entities.

Interpretation.

- The reference template is "What did <director> not direct?": the director names the subject, the films are the answer.
- The semantics stay the film-side complement of T1; only the syntax of the question differs.
- "Actors" and "directors" name answer classes, not relations: actors = cast members (`wdt:P161`), directors = holders of the credit (`wdt:P57`).
- The verb chooses the relation; the noun chooses the answer class.
- A multi-film "or" reads as "neither film": "Which directors did not direct 'A' or 'B'?" excludes directors of A and of B.

## Gaps found (probes on the S10 code, 2026-10-19)

| # | Input | S10 behavior | Expected |
|---|---|---|---|
| 1 | "What did John Ford not direct?" | film complement (already correct) | dataset coverage only |
| 2 | "Which directors did not direct 'Jaws' or 'Alien'?" | ignores the second film; Steven Spielberg (director of Jaws) appears | both films excluded; Spielberg absent |
| 3 | "Which actors did not direct 'Unforgiven'?" | answers the P161 cast complement, the wrong RDF class | actor universe (P161 humans) minus Unforgiven's director; the film's cast members stay |
| 4 | "What did Marilyn Monroe not direct?" | "no information about the directing of Marilyn Monroe" (negation dropped) | the film complement; a person without credits did not direct any film |

## Changes

Code, 3 files.

- `agent/sparql_builder.py`: `complement(entity, predicate, direction, universe=None, others=())`.
  `universe="actor"` scopes person answers to cast members (`?f wdt:P161 ?x . ?x wdt:P31 wd:Q5`) and applies to the P57 director relation only; `others` adds further films to the exclusion set.
  The single-film and film-answer query shapes are byte-identical to S10.
- `agent/preprocess.py`: `Plan.universe` and `Plan.films`.
  `_universe()` reads the person noun outside title mentions; `_detach_noun()` removes it so it cannot hijack the relation phrase; `_mentioned_films()` collects every film mention of a negated question.
- `agent/handlers/factual.py`: a negated lookup no longer stops at `no_facts`; the direction falls back to film -> "out", person -> "in"; the handler passes `plan.universe` and the remaining film mentions to the builder.

Dataset: new groups in `scripts/adversarial/build_datasets.py` (appended after the S5 blocks; cases 001-064 are byte-stable).

| Group | Ids | Cases | Form |
|---|---|---|---|
| F1 director subject, new syntax | 065-086 | 22 | "What did D not direct?", "What has D not directed?", plus 2 noun variants for the first 3 directors |
| F2 director noun, film object | 087-102 | 16 | "Which directors did not direct 'F'?", "What directors have not directed 'F'?" |
| F3 multi-film, neither | 103-111 | 9 | "Which directors did not direct 'A' or 'B'?" (plus 3 noun variants) |
| F4 actor universe | 112-119 | 8 | "Which actors did not direct 'F'?" (plus 3 noun variants) |
| F5 credit-less subject | 120-121 | 2 | "What did Marilyn Monroe not direct?", "What has Audrey Hepburn not directed?" |

Tests: 11 new unit tests (preprocess 5, builder 3, handler 3).

## Universe definitions (the no-ambiguity rule)

- Film universe: `?x wdt:P31 wd:Q11424` (unchanged, Q9).
- Director universe: objects of `wdt:P57` (unchanged, Q9).
- Actor universe: objects of `wdt:P161` with `wdt:P31 wd:Q5` (new; 55,916 humans).
- "Which directors did not direct F?" and "Which actors did not direct F?" ask the same relation.
  The noun selects the answer class: the director list holds P57 holders, the actor list holds cast humans.
- A positive question keeps its noun: "Which actors are in 'F'?" still answers the P161 cast (control test in `tests/test_factual.py`).

## Decisions and accepted risks

- Multi-film "or" means "neither film".
  An "and" form stays out of scope: it is ambiguous in English.
- The first person noun in the text wins when a question names two classes.
- The actor universe scopes the P57 relation only; other relations keep the S10 base.
- The actor complement uses the same bounded candidate query and 50-value serializer as the film complement (see `13-answer-bounding.md`).
  Expected values for F4 are harvested from the serialized rows (same accepted risk as S3, Q1/Q9).
- The credit-less-subject fix is generic: it applies to every negated lookup whose entity has no facts.

## Evidence

| Gate | S10 code | This branch |
|---|---|---|
| t1-negation (121 cases) | 103/121 | 121/121 |
| all ten adversarial types (664 cases) | - | 664/664 |
| stage2_factual.jsonl | 508/508 | 508/508 |
| stage1_sparql.jsonl | 9/9 | 9/9 |
| pytest | 127 passed | 138 passed |

Baseline detail: 18 of the 57 new cases failed on the S10 code (8 actor-universe cases, 8 multi-film cases, 2 credit-less-subject cases).
The 39 new director-syntax and director-noun cases passed on S10; they lock the syntax coverage the request asked for.

Logs: `eval/extension/t1-negation.log`, `eval/extension/summary.md`, `eval/extension/stage2.log`, `eval/extension/stage1.log`, `eval/extension/pytest.log`, `eval/extension/verify.log`.
The full `t1-negation.jsonl` is re-grounded per case: `check.log` (10 files, unique ids, non-empty fields) and `verify.log` (0 failed checks).
