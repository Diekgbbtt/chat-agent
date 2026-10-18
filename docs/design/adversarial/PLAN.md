# PLAN - Adversarial robustness for Stage 2 factual answers (FSM S0-S11)

Loop budget: `iter` starts at 0; counts G9 failures; S9 returns to S7 while `iter <= 3`; S11 when `iter > 3`.
WIP limit: one state at a time; a state starts only after the previous gate passes.
Status print at every gate: state id, gate result, evidence path.

Worktree plan (default 5a): commit operator baseline on `factual_approach`, then worktree `fix/adversarial-normalization` with `dataset/` and `kg_store/` symlinked in; venv by absolute path `/Users/diekgbbtt/atai-conversation-agent/.venv`.

## Checklist

- [ ] S0 CLARIFY AND PLAN - artifacts `docs/design/adversarial/00-questions.md`, `docs/design/adversarial/PLAN.md`.
  - Check G0: both files exist; every question has an answer or default; this plan lists S1 to S11. `test -f docs/design/adversarial/00-questions.md -a -f docs/design/adversarial/PLAN.md`.
- [ ] S1 DOMAIN MODEL - artifact `docs/design/adversarial/01-domain-model.md`.
  - Check G1: every relation from the union set (relations.json + stage2 eval property labels + sparql_builder templates) has >= 2 KG-grounded examples; entity types have real QIDs; probe commands and outputs shown.
  - Probe: `.venv/bin/python -m agent.cli --debug "Who directed 'Inception'?"`.
- [ ] S2 ARCHITECTURE - artifact `docs/design/adversarial/02-architecture-contracts.md`.
  - Check G2: six phases with five columns; seven boundaries with assumption + real intermediate value; baseline eval run shown.
  - Baseline: `source .venv/bin/activate && python -m agent.eval evals/stage2_factual.jsonl` and `python -m agent.eval evals/stage1_sparql.jsonl`.
- [ ] S3 FIVE KNOWN TYPES - artifact `docs/design/adversarial/03-known-types-spec.md`.
  - Check G3: 5/5 sections with definition, boundary, >= 1 red + >= 1 green grounded case, decision nodes resolved.
- [ ] S4 DISCOVERY (subagent, template 3.8) - artifact `docs/design/notes-adversarial-factual-questions-discovered.md`.
  - Check G4: >= 5 new types; each names boundary + 2 grounded examples + failing phase; entities probed against the lexicon.
- [ ] S5 DATASETS - artifacts `evals/adversarial/<type-id>.jsonl` (one per type), `docs/design/adversarial/05-dataset-manifest.md`.
  - Check G5: the mission's dataset-OK python check; 5 random cases per file re-validated by independent KG query in the manifest; >= 10 distinct entities per file.
- [ ] S6 BASELINE MEASUREMENT - artifacts `docs/design/adversarial/eval/iter0/<type-id>.log` and `-baseline.md`.
  - Check G6: per type a log and a report; numeric pass rate from the log; every failure clustered with counts summing to the failure total.
  - Run: `source .venv/bin/activate && python -m agent.eval -v evals/adversarial/<type-id>.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/<type-id>.log`.
- [ ] S7 DIAGNOSIS (subagents, template 3.11) - artifacts `docs/design/adversarial/07-cluster-index.md`, `docs/design/adversarial/diagnosis/<cluster-id>.md`.
  - Check G7: report count == cluster count; each has a run red repro, ranked hypotheses, root cause at a phase boundary, suggested fix, regression seam.
- [ ] S8 IMPLEMENTATION - code + tests + `docs/design/adversarial/08-fix-log.md`.
  - Check G8: `pytest` green; happy-path eval no regression; every cluster has a change or recorded deferral; diff grep finds no hardcoded eval strings; Stage 1 still 9/9.
  - Commands: `.venv/bin/python -m pytest -q`; `python -m agent.eval evals/stage2_factual.jsonl`; `python -m agent.eval evals/stage1_sparql.jsonl`.
- [ ] S9 RE-EVALUATE - artifacts `docs/design/adversarial/09-scoreboard.md` plus `eval/iter<N>/<type-id>.log`.
  - Check G9: every type >= 0.8 and happy path not regressed -> S10; else `iter += 1` and loop to S7 or exit S11 when `iter > 3`.
- [ ] S10 FINAL REPORT - artifact `docs/design/adversarial/10-final-report.md`.
  - Check G10: report exists; every number traces to a saved log; `git status` clean; no open PLAN items.
- [ ] S11 BLOCKED REPORT - artifact `docs/design/adversarial/11-blockers.md`.
  - Check G11: report exists; final reply names the blocker.

## Gate log

| State | Gate | Result | Evidence |
|---|---|---|---|
| S0 | G0 | (pending) | `docs/design/adversarial/00-questions.md`, `docs/design/adversarial/PLAN.md` |
