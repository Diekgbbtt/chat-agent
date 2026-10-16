# PLAN - Adversarial robustness for Stage 2 factual answers (FSM S0-S11)

Loop budget: `iter` starts at 0; counts G9 failures; S9 returns to S7 while `iter <= 3`; S11 when `iter > 3`.
WIP limit: one state at a time; a state starts only after the previous gate passes.
Status print at every gate: state id, gate result, evidence path.

Worktree plan (default 5a): commit operator baseline on `factual_approach`, then worktree `fix/adversarial-normalization` with `dataset/` and `kg_store/` symlinked in; venv by absolute path `/Users/diekgbbtt/atai-conversation-agent/.venv`.

## Checklist

- [x] S0 CLARIFY AND PLAN - artifacts `docs/design/adversarial/00-questions.md`, `docs/design/adversarial/PLAN.md`.
  - Check G0: both files exist; every question has an answer or default; this plan lists S1 to S11. `test -f docs/design/adversarial/00-questions.md -a -f docs/design/adversarial/PLAN.md`.
- [x] S1 DOMAIN MODEL - artifact `docs/design/adversarial/01-domain-model.md`.
  - Check G1: every relation from the union set (relations.json + stage2 eval property labels + sparql_builder templates) has >= 2 KG-grounded examples; entity types have real QIDs; probe commands and outputs shown.
  - Probe: `.venv/bin/python -m agent.cli --debug "Who directed 'Inception'?"`.
- [x] S2 ARCHITECTURE - artifact `docs/design/adversarial/02-architecture-contracts.md`.
  - Check G2: six phases with five columns; seven boundaries with assumption + real intermediate value; baseline eval run shown.
  - Baseline: `source .venv/bin/activate && python -m agent.eval evals/stage2_factual.jsonl` and `python -m agent.eval evals/stage1_sparql.jsonl`.
- [x] S3 FIVE KNOWN TYPES - artifact `docs/design/adversarial/03-known-types-spec.md`.
  - Check G3: 5/5 sections with definition, boundary, >= 1 red + >= 1 green grounded case, decision nodes resolved.
- [x] S4 DISCOVERY (subagent, template 3.8) - artifact `docs/design/notes-adversarial-factual-questions-discovered.md`.
  - Check G4: >= 5 new types; each names boundary + 2 grounded examples + failing phase; entities probed against the lexicon.
- [x] S5 DATASETS - artifacts `evals/adversarial/<type-id>.jsonl` (one per type), `docs/design/adversarial/05-dataset-manifest.md`.
  - Check G5: the mission's dataset-OK python check; 5 random cases per file re-validated by independent KG query in the manifest; >= 10 distinct entities per file.
- [x] S6 BASELINE MEASUREMENT - artifacts `docs/design/adversarial/eval/iter0/<type-id>.log` and `-baseline.md`.
  - Check G6: per type a log and a report; numeric pass rate from the log; every failure clustered with counts summing to the failure total.
  - Run: `source .venv/bin/activate && python -m agent.eval -v evals/adversarial/<type-id>.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/<type-id>.log`.
- [x] S7 DIAGNOSIS (subagents, template 3.11) - artifacts `docs/design/adversarial/07-cluster-index.md`, `docs/design/adversarial/diagnosis/<cluster-id>.md`.
  - Check G7: report count == cluster count; each has a run red repro, ranked hypotheses, root cause at a phase boundary, suggested fix, regression seam.
- [x] S8 IMPLEMENTATION - code + tests + `docs/design/adversarial/08-fix-log.md`.
  - Check G8: `pytest` green; happy-path eval no regression; every cluster has a change or recorded deferral; diff grep finds no hardcoded eval strings; Stage 1 still 9/9.
  - Commands: `.venv/bin/python -m pytest -q`; `python -m agent.eval evals/stage2_factual.jsonl`; `python -m agent.eval evals/stage1_sparql.jsonl`.
- [x] S9 RE-EVALUATE - artifacts `docs/design/adversarial/09-scoreboard.md` plus `eval/iter<N>/<type-id>.log`.
  - Check G9: every type >= 0.8 and happy path not regressed -> S10; else `iter += 1` and loop to S7 or exit S11 when `iter > 3`.
- [ ] S10 FINAL REPORT - artifact `docs/design/adversarial/10-final-report.md`.
  - Check G10: report exists; every number traces to a saved log; `git status` clean; no open PLAN items.
- [ ] S11 BLOCKED REPORT - artifact `docs/design/adversarial/11-blockers.md`.
  - Check G11: report exists; final reply names the blocker.

## Gate log

| State | Gate | Result | Evidence |
|---|---|---|---|
| S0 | G0 | PASS (2026-10-16) | all 8 questions answered in `00-questions.md`; plan lists S0-S11; baseline evals run: stage1 9/9 exit 0, stage2 508/508 exit 0 (`docs/design/adversarial/eval/baseline-stage1.log`, `baseline-stage2.log`) |
| S1 | G1 | PASS (2026-10-16) | `docs/design/adversarial/01-domain-model.md`: 30/30 union relations with 2 grounded examples; entity types Q11424/Q5 with counts; probes in `scripts/adversarial/probe_domain_model.py`, log `docs/design/adversarial/eval/s1-domain-probe.log` |
| S2 | G2 | PASS (2026-10-16) | `docs/design/adversarial/02-architecture-contracts.md`: 6 phases x 5 columns, 7 boundaries with real traces from `scripts/adversarial/capture_traces.py` (log `docs/design/adversarial/eval/s2-trace-examples.log`); baseline 508/508 and 9/9 recorded |
| S3 | G3 | PASS (2026-10-16) | `docs/design/adversarial/03-known-types-spec.md`: 5/5 types with red+green grounded cases (logs `s3-probe.log`, `s3-probe2.log`); decision nodes Q1-Q12 all answered by the operator |
| S4 | G4 | PASS (2026-10-16) | `docs/design/notes-adversarial-factual-questions-discovered.md`: 8 new types D1-D8; all 16 cited QIDs probed in lexicon and all red replies reproduced (`docs/design/adversarial/eval/s4-verification.log`); impact triage `s4-triage.log`; datasets for the top 5: D2, D3, D5, D8, D1 |
| S5 | G5 | PASS (2026-10-16) | `evals/adversarial/`: 10 files, 607 cases, every file >= 50 cases, >= 10 entities, >= 2 relations; `scripts/adversarial/check_datasets.py` prints "datasets OK" (`eval/s5-check.log`); 50 random cases re-validated in `eval/s5-verify.log` (0 failures), embedded in `05-dataset-manifest.md` |
| S6 | G6 | PASS (2026-10-16) | per type a verbose log + report in `eval/iter0/`; cluster tables written by `scripts/adversarial/cluster_baseline.py`, counts sum to failures; baseline pass rates: t1 8/64, t2 24/60, t3 37/57, t4 39/60, t5 20/51, d1 6/63, d2 10/65, d3 18/55, d5 0/62, d8 10/70 |
| S7 | G7 | PASS (2026-10-16) | `07-cluster-index.md` defines 10 clusters; `diagnosis/` holds 10 reports (count matches); every report carries a red repro from `eval/s7-repros.log` (script `capture_repros.py`), ranked hypotheses, a root cause pinned to a phase and a B1-B7 boundary with file:line, a suggested fix, and a regression seam |
| S8 | G8 | PASS (2026-10-16) | `docs/design/adversarial/08-fix-log.md`: new seam `agent/preprocess.py` + handler wiring + `complement`/`claim` templates + narrowed count filter; pytest 127 passed; stage2 508/508 and stage1 9/9 (exit 0); all 10 clusters carry a change (no deferrals); iter1 607/607 in `eval/iter1/`; diff grep finds no hardcoded eval strings |
| S9 | G9 | PASS (2026-10-16) | `09-scoreboard.md`: iter0 172/607 -> iter1 607/607; every type at 1.00 (>= 0.8); happy path unchanged (stage2 508/508, stage1 9/9, both exit 0); zero iter1 failures, so `iter` stays 1; per-type logs `eval/iter1/<type-id>.log`, table `eval/iter1/summary.md` |
