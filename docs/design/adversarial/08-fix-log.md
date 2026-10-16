# S8 - fix log

State: S8.
Constraint: the change lives in the new seam `agent/preprocess.py` (Q3), called once per message in `agent/handlers/factual.py` before `Parser.parse`.
`agent/parser.py` and `agent/nlg.py` are unchanged.
Spec: the fixes implement decisions Q1-Q16 from `docs/design/adversarial/00-questions.md`.
Diagnosis: every change maps to a cluster in `docs/design/adversarial/07-cluster-index.md` and a report in `docs/design/adversarial/diagnosis/`.
Measurement: `scripts/adversarial/run_iter.py` reuses `agent.eval.passes` and writes `docs/design/adversarial/eval/iter1/<type-id>.log` plus `summary.md`.

## Files changed

| File | Change |
|---|---|
| `agent/preprocess.py` | new normalisation layer: `Preprocessor`, `Plan`, `Claim`, `strip_article` |
| `agent/handlers/factual.py` | plan wiring: claim, clarify, parse, negated complement |
| `agent/sparql_builder.py` | `count` film filter narrowed; new `complement` and `claim` templates |
| `tests/test_preprocess.py` | new rule tests (25 cases) |
| `tests/test_factual.py` | handler cases for paraphrase, typo, partial, clause, complement, claim, clarify, count |
| `tests/test_sparql_builder.py` | complement shapes, claim ASK, count filter |
| `scripts/adversarial/run_iter.py` | iteration runner (new) |
| `docs/design/adversarial/05-dataset-manifest.md` | stale total corrected: 598 -> 607 (the per-file table always summed to 607) |

## Handler order

1. `Preprocessor.analyze` returns a `Plan` (rewritten text, negation, clarify, claim).
2. A detected claim runs the `sb.claim` ASK query and replies `nlg.answer(["Yes"])` or `nlg.answer(["No"])` (Q13).
3. `plan.clarify` replies `nlg.no_entity()`.
4. Otherwise `Parser.parse(plan.text)` runs on the rewritten text.
5. A negated lookup (`plan.negated` and kind `lookup`) runs `sb.complement` instead of `sb.lookup` (Q1, Q9).
6. The existing error paths and the count and superlative paths stay unchanged.

## Cluster to fix map (10/10 clusters changed; no deferrals)

| Cluster | Fix | Code anchor | iter1 |
|---|---|---|---|
| c-t1-negation | negation scan after mention masking; complement templates that reuse the dataset query shapes | `preprocess._scan`, `_shield`; `handler.handle`; `sparql_builder.complement` | 64/64 |
| c-t2-subvention | clarify when a lowercase strict sub-run resolves but the whole mention does not | `preprocess._contained_subrun`, `_scan` | 60/60 |
| c-t3-quote-shapes | quote normalisation (curly, doubled, unclosed, inner punctuation) with a rewrite to the graph label | `preprocess._normalise_quotes`, `_canonical` | 57/57 |
| c-t4-typos | article-aware resolution: exact article labels, article-stripped families, whole-run fuzzy | `preprocess._resolve`, `_fuzzy_core` | 60/60 |
| c-t5-partial-titles | family resolution with film-first, degree-ranked candidates | `preprocess._resolve`, `Resolution` (ranking via `Parser._rank`) | 51/51 |
| c-d1-counts | the `P31 Q11424` filter applies only to film credits from the film side (direction `in`, P57/P58/P86) | `sparql_builder.count` | 63/63 |
| c-d2-multi-mention | film mentions in two different sentences produce the clarification reply | `preprocess._two_film_sentences` | 65/65 |
| c-d3-trailing | a trailing `, ...` clause after a known quoted title is dropped, the terminal punctuation kept | `preprocess._strip_trailing_clause` | 55/55 |
| c-d5-yes-no | claim detection (did/does/do + direct/write/compose; was/were/is/are + past participle + by) and the ASK template | `preprocess._detect_claim`; `sparql_builder.claim` | 62/62 |
| c-d8-paraphrases | paraphrase rewrites to canonical relation words plus mention rewrite priority | `preprocess._apply_paraphrases`, `_rewrite`, `_priority` | 70/70 |

## Rule inventory and tests (G8: every rule has >= 2 tests)

| Rule | Tests |
|---|---|
| quote repair: doubled quotes, inner punctuation, inner spaces, unclosed quote, curly quotes, interior apostrophe, contraction safety | `test_doubled_quotes_collapse`, `test_inner_punctuation_trimmed_outer_question_kept`, `test_unclosed_quote_is_closed`, `test_inner_whitespace_trimmed`, `test_curly_quotes_replaced`, `test_interior_apostrophe_title_kept`, `test_contraction_is_not_an_opening_quote` |
| trailing clause (Q-D3) | `test_trailing_clause_stripped`, `test_question_without_clause_unchanged` |
| article-stripped family resolution (Q10) | `test_article_variant_resolves`, `test_partial_title_resolves` |
| fuzzy resolution with the 0.85 and 0.80 cutoffs and the 0.05 margin (Q7, Q11) | `test_typo_resolves`, `test_long_typo_resolves` |
| subvention clarify (T2) | `test_subvention_clarifies`, `test_quoted_subvention_clarifies`, `test_known_title_does_not_clarify` |
| two-mention clarify (Q16) | `test_film_mentions_in_two_sentences_clarify`, `test_two_titles_in_one_sentence_do_not_clarify` |
| negation detection and masking (Q1, Q8) | `test_not_negation_detected`, `test_never_negation_detected`, `test_not_object_negation_detected`, `test_negation_word_inside_quoted_title_is_masked`, `test_negation_word_inside_listed_title_is_masked`, `test_plain_question_is_not_negated` |
| claim detection (Q13) | `test_direct_claim_detected`, `test_inverse_claim_detected`, `test_write_claim_maps_to_screenwriter`, `test_question_is_not_a_claim` |
| paraphrase rewrites (Q14) | five `test_paraphrase_rewritten_to_relation_word` cases, `test_unknown_paraphrase_is_left_alone` |
| complement template (Q1, Q9) | `test_complement_directions`, `test_queries_run` |
| count film filter (D1) | `test_count_filters_films_only_for_film_credits`, `test_count_does_not_filter_awards_as_films` |
| handler integration | `test_adversarial_forms` (9 cases), `test_negated_question_lists_the_complement`, `test_negated_question_with_the_entity_as_object`, `test_negation_word_in_a_title_is_not_a_negation`, `test_two_mentions_are_clarified` |
| helper | `test_strip_article` |

## Recorded deviations from the decision notes

1. Q15 prefix siblings were dropped.
   Evidence: prefix resolution linked generic question words to unrelated titles ("company" -> The Company of Wolves, "Can" -> Can Togay, "What's" -> What's New Pussycat?, "made" -> Made) and caused 27 golden failures.
   After the change the ten adversarial types stay at 1.00 and T5 stays 51/51.
   Resolution now uses exact article labels, exact article-stripped families, and whole-run fuzzy only.
2. The D2 clarification rule counts film mentions in two different sentences, not two mentions anywhere.
   Reason: the golden case `Who directed Her and Interstellar?` must keep the Spike Jonze answer.
   All 65 D2 cases have a sentence split, so the rule covers them.
3. Sub-run mentions never rewrite the text.
   Reason: the goldens `Who directed Don't Look Her?` (clarify) and `Who directed Her and Interstellar?` (Spike Jonze).
   Sub-runs still count for D2 and still shield negation words.
4. Rewriting quotes only the most prominent mention class (quoted > multi-word > capitalised > lowercase single word).
   Reason: the paraphrase verb "made" is also a film title; quoting it hijacked the entity.
   The d8 form `Which filmmaker made 'X'?` answers correctly once the quoted title is the only rewritten mention.
5. Q14 stands as decided: "behind the camera" rewrites to "directed", although the KG also uses P344 for that phrase.
6. Claims are skipped when the message is negated, and the complement branch runs only for kind `lookup`.
   The `no_facts` error path is unchanged for negated questions; recorded as a limitation.
7. The fuzzy cutoffs stay at 0.80 (cores up to 6 chars) and 0.85 (longer) with the 0.05 margin (Q7, Q11).
   A 1e-6 epsilon only corrects the float conversion at exact rate borders, for example a 0.80 score otherwise lost inside `rapidfuzz`.

## Golden cases at risk, verified green in iter1

- `Who directed Her and Interstellar?` -> Spike Jonze.
- `Who directed Don't Look Her?` -> clarification.
- `Who directed 'The Cat o' Nine Tails'?`, `Who directed Them!?`, `Who directed Who Am I?`.
- `Which company distributed 'The Moon Is Blue'?` and the other distributor cases.
- `What was the first movie Christopher Nolan directed?`, `Can you tell me who directed Jaws?`, `What's the release year of The Shawshank Redemption?`.
- `Who directed 'The Pirates! In an Adventure with Scientists!'?`.
- The three "I'm Not There" cases (the negation word sits inside a quoted title).

## Verification

| Check | Command | Result |
|---|---|---|
| unit tests | `/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python -m pytest -q` | 127 passed |
| happy path | `python -m agent.eval evals/stage2_factual.jsonl` | 508/508, exit 0 |
| stage 1 | `python -m agent.eval evals/stage1_sparql.jsonl` | 9/9, exit 0 |
| adversarial | `python scripts/adversarial/run_iter.py --out docs/design/adversarial/eval/iter1` | 607/607 |
| datasets | `python scripts/adversarial/check_datasets.py` | 10 files checked, datasets OK |
| hardcoded strings | `grep -rniE "jaws|godfather|matrix|inception|parasite|tarzan|handmaiden|whiplash|oppenheimer|interstellar" agent/` | only docstring examples, most of them pre-existing; no dataset string in logic |

Per-type iter1 rates: t1 64/64, t2 60/60, t3 57/57, t4 60/60, t5 51/51, d1 63/63, d2 65/65, d3 55/55, d5 62/62, d8 70/70.
Logs: `docs/design/adversarial/eval/iter1/<type-id>.log`, table in `docs/design/adversarial/eval/iter1/summary.md`.
