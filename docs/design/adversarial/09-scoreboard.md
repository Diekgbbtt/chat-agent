# S9 - scoreboard, iteration 1

State: S9.
Gate G9: every type >= 0.8 and the happy path not regressed -> S10; otherwise `iter += 1` and loop to S7 (S11 when `iter > 3`).
Loop counter: `iter` starts at 0 (S6 baseline); the S8 change is iteration 1.
Change under test: commit `1b52a59` (new seam `agent/preprocess.py`, handler wiring, complement and claim templates, narrowed count filter).

## Per-type results

| Type | iter0 (baseline) | iter1 (this run) | Rate iter1 | Threshold | Verdict | Log |
|---|---|---|---|---|---|---|
| t1-negation | 8/64 | 64/64 | 1.00 | 0.8 | PASS | `eval/iter0/t1-negation.log`, `eval/iter1/t1-negation.log` |
| t2-subvention | 24/60 | 60/60 | 1.00 | 0.8 | PASS | `eval/iter0/t2-subvention.log`, `eval/iter1/t2-subvention.log` |
| t3-quote-shapes | 37/57 | 57/57 | 1.00 | 0.8 | PASS | `eval/iter0/t3-quote-shapes.log`, `eval/iter1/t3-quote-shapes.log` |
| t4-typos | 39/60 | 60/60 | 1.00 | 0.8 | PASS | `eval/iter0/t4-typos.log`, `eval/iter1/t4-typos.log` |
| t5-partial-titles | 20/51 | 51/51 | 1.00 | 0.8 | PASS | `eval/iter0/t5-partial-titles.log`, `eval/iter1/t5-partial-titles.log` |
| d1-count-class | 6/63 | 63/63 | 1.00 | 0.8 | PASS | `eval/iter0/d1-count-class.log`, `eval/iter1/d1-count-class.log` |
| d2-multiple-mentions | 10/65 | 65/65 | 1.00 | 0.8 | PASS | `eval/iter0/d2-multiple-mentions.log`, `eval/iter1/d2-multiple-mentions.log` |
| d3-trailing-superlative | 18/55 | 55/55 | 1.00 | 0.8 | PASS | `eval/iter0/d3-trailing-superlative.log`, `eval/iter1/d3-trailing-superlative.log` |
| d5-yes-no | 0/62 | 62/62 | 1.00 | 0.8 | PASS | `eval/iter0/d5-yes-no.log`, `eval/iter1/d5-yes-no.log` |
| d8-relation-paraphrases | 10/70 | 70/70 | 1.00 | 0.8 | PASS | `eval/iter0/d8-relation-paraphrases.log`, `eval/iter1/d8-relation-paraphrases.log` |
| **all** | **172/607** | **607/607** | **1.00** | - | **PASS** | `eval/iter1/summary.md` |

## Happy path (no regression)

| Set | Baseline | iter1 | Evidence |
|---|---|---|---|
| stage 2 factual | 508/508, exit 0 | 508/508, exit 0 | `eval/baseline-stage2.log`, run of 2026-10-16 after commit `1b52a59` |
| stage 1 SPARQL | 9/9, exit 0 | 9/9, exit 0 | `eval/baseline-stage1.log`, run of 2026-10-16 after commit `1b52a59` |
| unit tests | - | 127 passed | `tests/` suite |

## Failure accounting

The iter1 logs hold zero `FAIL` lines, so no cluster is reopened.
The loop counter does not advance: `iter` stays 1.
Every case from iter0 that failed now passes; the per-type logs carry one `PASS` line per case.

## Verdict

G9 PASS -> S10 FINAL REPORT.
Reason: all ten types are at 1.00 (>= 0.8) and both happy-path sets match their baselines.
