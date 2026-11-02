# Stage 3 Implementation Report

Status: implementation landed; local adversarial suite ready; local model gate pending.
Date: 2026-11-02.
Branch: `feature/guard-two-stage-e2e-evals-local`.
Worktree: `../atai-llm-centric`.
Spec: `.scratch/llm-centric-agent/spec.md`.
Tickets: `.scratch/llm-centric-agent/issues/`.

## 1. Delivered

The deterministic runtime, the guard package, the tool package, and the QA package are implemented.
The legacy path remains the default.
No old handler was deleted.

| Area | Delivered |
|---|---|
| Baseline harness | `agent.eval --json`, `scripts/scoreboard.py` |
| Model access | Local OpenAI-compatible client, retry, typed errors, health probe, client factory |
| Settings | Local endpoint, shared role defaults, per-role overrides; mode, budgets, limits, autostart flag |
| Guard schema | Data-driven scopes, three parent safety types, descriptions, fallbacks, 8 pair examples |
| Normalizer | Trim, cap, quote repair, course-prefix removal |
| Guard discrimination | Forced `submit_discrimination`, exact spans, ambiguity flags, relationship targets |
| Guard classification | Forced `submit_classification` on the fixed decomposition, exact label count enforced with `minItems` and `maxItems` |
| Guard validators | Discrimination spans, order, coverage, relationships, acyclic graph; classification labels, indices, rationales; one retry per stage |
| Policy | One handling per verbatim, aggregate action, redaction, utility invariant |
| Fallback | Canonical text for refusal, boundary, clarification, capability, general, unavailable answer |
| Guard-only mode | New guard and policy, legacy factual answer, canonical other parts |
| Raw SPARQL | Existing capability now validated by the same read-only query guard |
| Graph tools | `resolve_entity`, `run_sparql`, row IDs, labels, truncation, typed observations |
| QA contract | Nine-section system prompt, schema card, tool list, `submit_response` contract |
| QA loop | Bounded steps, one tool call per turn, repeat-call guard, forced final submit, repair, deadline, deterministic fallback |
| QA validator | Part coverage, order, kind, evidence, values, safety types, clarification shape, redaction overlap |
| Mixed replies | Factual, general, capability, refusal, clarification, and boundary parts in verbatim order |
| Runtime modes | `AGENT_MODE=legacy`, `guard_only`, and `tools` |
| Session seam | Bounded turn list, safe in-scope user text only |
| Eval data | Three scope relabels, mixed cases keep their safe answer |
| Policy suite | Every scope and safety pair, aggregate action matrix |
| Adversarial suite | 31 multi-part cases, 30 policy branches, three repeats, probe separation |
| Serving | One-process vLLM launcher, shared endpoint health check, raw command print |
| Submission build | Copies serving requirements and asserts the launcher |

## 2. Main Files

| Path | Role |
|---|---|
| `agent/guard/schema.py` | Load and validate the guard data |
| `agent/guard/discriminator.py` | Discrimination prompt, relationship rules, forced tool call |
| `agent/guard/classifier.py` | Classification prompt on the fixed decomposition, forced tool call |
| `agent/guard/verdict.py` | Typed guard output and span validation |
| `agent/guard/policy.py` | Prompt-injection scope, relationship resolution, effective plan, aggregate action |
| `agent/guard/gate.py` | Normalise, discriminate, classify, validate, retry, plan, emit canonical labels |
| `agent/guard/labels.py` | Canonical trace and eval labels |
| `agent/guard/session.py` | Safe in-scope user text for the session seam |
| `agent/tools/sparql.py` | Query guard, observation, formatter, run tool |
| `agent/tools/resolve.py` | Exact, prefix, and contains entity lookup |
| `agent/tools/registry.py` | Tool lookup and execution |
| `agent/qa/prompts.py` | QA system and user prompts |
| `agent/qa/actions.py` | Tool schemas |
| `agent/qa/types.py` | Part and result types |
| `agent/qa/validator.py` | Part and grounding checks |
| `agent/qa/agent.py` | Bounded QA loop |
| `agent/qa/composer.py` | Deterministic fallback parts |
| `agent/handlers/guard_only.py` | Guard-only bridge |
| `agent/handlers/tool_agent.py` | Target runtime handler |
| `agent/llm/client.py` | OpenAI SDK client |
| `agent/llm/health.py` | Endpoint probe |
| `agent/serve.py` | vLLM launcher |
| `scripts/adversarial/build_policy_e2e.py` | Build the 41-case adversarial suite |
| `scripts/adversarial/run_policy_e2e.py` | Score action, decomposition, labels, relationships, reply, and branch coverage |

The old in-process model class moved to `agent/llm/legacy.py`.
The old `agent/llm.py` module had to move because the new package uses `agent/llm/`.
`scripts/try_llm.py` was updated to the new import.
The legacy class and its dependencies stay until Phase 5.

### 2.1 Two-stage guard impact map

| Component | Change | Test coverage |
|---|---|---|
| `agent/guard/verdict.py` | New `Span`, `Relationship`, `Discrimination`; two validators | `test_guard_verdict` |
| `agent/guard/discriminator.py` | New discrimination prompt and forced tool | `test_guard_discriminator` |
| `agent/guard/classifier.py` | Rewritten classification prompt on a fixed decomposition; exact label count in the tool schema | `test_guard_classifier` |
| `agent/guard/gate.py` | Two chained calls, per-stage retry, merged trace | `test_guard_gate` |
| `agent/guard/policy.py` | Prompt-injection scope, relationship resolution, effective plan | `test_policy`, `test_policy_matrix` |
| `agent/guard/labels.py` | Labels from the effective decision | `test_guard_gate` |
| `agent/guard/session.py` | Only answer-handled safe in-scope text enters the session | `test_runtime_modes` |
| `agent/guard/schema.py`, `agent/data/guardrails.json` | Role-play description, 240-char rationale, no `max_ambiguities` | `test_guard_schema` |
| `agent/guard/frames.py` | Deleted; the two-stage LLM owns decomposition | `test_guard_frames` deleted |
| `agent/qa/prompts.py` | Nine sections, effective labels, relationship fields, entity redaction | `test_qa_contract`, `test_qa_agent` |
| `agent/qa/types.py`, `actions.py`, `agent.py` | Removed the obsolete `assumption` field | `test_qa_contract`, `test_qa_agent` |
| `agent/qa/validator.py` | Effective redaction, including inherited unsafe children | `test_answer_validator` |
| `agent/qa/agent.py` | Repeat-call guard, forced final submit, 300-token step cap | `test_qa_agent` |
| `agent/qa/composer.py` | Distinct observations across answer parts | `test_composer` |
| `agent/handlers/guard_only.py`, `tool_agent.py` | Session text from the decision plan | `test_guard_only`, `test_runtime_modes` |
| `agent/config.py`, `agent/llm/factory.py`, `agent/llm/client.py` | Local endpoint settings and local client factory | `test_config`, `test_llm_client` |
| `agent/guard/verdict.py` | Resolved relationships require an explicit entity; null is missing-target only | `test_guard_verdict` |
| `evals/stage3_guardrails.jsonl` | Three relational cases | `test_eval_data` |
| `evals/adversarial/policy_e2e.jsonl` | 41 adversarial multi-part cases | `test_policy_e2e_data` |
| `scripts/adversarial/run_policy_e2e.py` | Branch-aware e2e runner and results | manual |
| Design records | `REPORT`, `IMPACT`, `PLAN`, `IMPLEMENTATION`, `POLICY_MAP`, `OPENROUTER_EVALS`, spec, tickets | review |

## 3. Verification

| Command | Result |
|---|---|
| `pytest -q` | 621 passed |
| `python -m compileall -q agent scripts tests` | clean |
| `agent.eval evals/stage1_sparql.jsonl` | 9 of 9 |
| `agent.eval evals/stage2_factual.jsonl` | 508 of 508 |
| `agent.eval evals/stage2_factual_negation.jsonl` | 9 of 9 |
| `agent.eval evals/stage3_guardrails.jsonl` in `guard_only` with no model | 0 of 47, expected |
| `agent.eval evals/stage1_sparql.jsonl --json ...` | 9 of 9, one result object per case |
| `scripts/scoreboard.py ...` | 9 of 9, 0 failed |
| `tests/test_eval.py`, `tests/test_scorecard.py` | `labels_any_of` accepts harmful or toxic |

The 0 of 47 run is a no-model run.
The guard suite needs an endpoint.
It is not a code failure.

## 4. Local Evaluation Status

The adversarial suite has 41 cases.
It declares 30 model-driven policy branches.
The suite and the branch manifest are implemented.
No local model measurement is recorded in this branch.

| Gate | Status |
|---|---|
| Adversarial suite implementation | complete |
| Branch coverage manifest | 30 branches |
| Local pass@1 at or above 95 percent | pending |
| Local three-repeat stability | pending |
| T4 memory fit | no T4 access |
| Local guard p95 below 2 seconds | no local endpoint |
| Local QA p95 below 20 seconds | no local endpoint |
| Held-out factual accuracy | the held-out set does not exist yet |
| Harmful refusal wording review | needs a human safety reviewer |
| Red-team split | the 40-case test split does not exist yet |
| Self-harm refusal wording | policy fixed; human wording review remains |

The T4 serving spike remains the first local empirical gate.
It decides vLLM one-process versus llama.cpp.
It also decides whether one shared model is sufficient for the guard and QA roles.

The interpretation policies are explicit:

- A gender-mismatched pronoun is a user assumption or typo and is non-ambiguous.
- A realism question about a depicted method is safe film analysis.
- A request for method steps is harmful.
- A quoted instruction is content, not executed injection.
- `harmful` and `toxic` overlap for hate speech; the eval accepts either.

The detailed suite report is `docs/design/adversarial/policy-e2e/REPORT.md`.

## 5. Behavioural Evidence

The fake-client tests cover the full path without a model server.

- A safe in-scope verbatim is answered.
- A safe out-of-scope verbatim gets a boundary part.
- An unsafe verbatim is refused and redacted.
- A mixed request keeps the answer and adds the refusal.
- A three-way mixed request keeps answer, boundary, and refusal.
- A missing semantic target beside an answer produces answer plus clarification.
- An ambiguous child inherits its parent's toxic label and is refused.
- An unambiguous child of an injection parent keeps its movie answer.
- Invalid discrimination or classification produces a clarification, not a refusal.
- The classifier returns exactly one own label per span, enforced by the tool schema.
- The classifier uses earlier labels only for reference resolution, not for inheritance.
- A harmless dependent child stays safe in its own label and inherits only in the policy.
- A gender-mismatched pronoun is non-ambiguous and carries no relationship.
- A quoted instruction is not prompt injection.
- A realism question about a depicted method is safe; a request for steps is harmful.
- A resolved relationship must name an explicit entity inside its target.
- A factual part must cite a `run_sparql` row.
- An invented number, QID, URL, or unknown row is rejected.
- A non-factual part cannot cite evidence.
- A refusal must address exactly its own safety types.
- A repeated QA tool call is blocked and the existing observation is reused.
- The final QA step forces `submit_response`.
- The deterministic fallback distinguishes multiple answer observations.
- A tool query cannot reuse four words from a redacted verbatim.
- The session stores no unsafe or out-of-scope text.
- Raw SPARQL still bypasses the guard.
- `AGENT_MODE=legacy` is the default.

## 6. Deviations

1. `agent/llm.py` became `agent/llm/legacy.py`.
   The name was needed for the new package.
   The legacy class and behaviour are unchanged.
2. The raw SPARQL capability stays in `agent/handlers/sparql.py`.
   It now calls the same `QueryGuard` in raw mode.
   A separate `agent/tools/raw_sparql.py` was not created.
   This keeps one detection and formatting path during the transition.
3. The runtime now declares `openai>=3.0`.
   `pydantic>=2.0` is explicit.
   The CUDA packages stay for the legacy in-process path until Phase 5.
4. The guard classifier prompt carries the 8 pair examples plus six multi-verbatim examples.
   The schema validates the 8 pairs.
   The multi-verbatim examples are prompt text, not schema rows.
5. The QA prompt is one system prompt, not one prompt per action.
   The action and plan are in the user prompt.
   This follows the nine-section contract in the report.
6. The guard is two chained model calls: discrimination, then classification.
   The discriminator owns decomposition and relationship mapping.
   The classifier labels a fixed decomposition independently.
   The policy resolves relationships and applies prompt-injection scope.
   The previous deterministic `agent/guard/frames.py` splitter is removed.
   The residual risk is documented in `POLICY_MAP.md`.
7. The old `overview.ambiguities` list and the QA `assumption` field are removed.
   Ambiguity is a per-span boolean with an optional relationship.
   A missing target is a clarification, not a non-blocking assumption.
8. A resolved relationship must carry an explicit entity.
   A null entity is valid only for `missing semantic target`.
   The whole-span dependency repeats the full target text.
9. The classification tool schema sets `minItems` and `maxItems` to the span count.
    The model omitted safe ambiguous children under prose-only instructions.
10. The classification prompt carries an ordered prior-label usage contract.
    Earlier labels are visible when later labels are written.
    They may resolve a reference, but they must not be copied or inherited.
11. A gender-mismatched pronoun is non-ambiguous.
    The mismatch is a user assumption or typo.
    Matching-gender pronouns remain ambiguous and inherit.
12. A realism question about a depicted method is safe.
    A request for instructions, quantities, detail, or encouragement is harmful.
13. A quoted instruction is content, not executed injection.
    Translation, quotation, and film-dialogue discussion are not prompt injection.
14. Evaluation accepts overlapping `harmful` and `toxic` outputs through `labels_any_of`.

## 7. Next Steps

1. Run the Phase 1 serving spike on the T4.
2. Run the 41-case policy suite on the local endpoint.
3. Review the self-harm refusal wording with a human reviewer.
4. Keep the harmful/toxic overlap acceptable through `labels_any_of`.
5. Improve the QA model path for multi-answer tool loops; the fallback is correct but the model path is not.
6. Build and freeze the held-out factual set.
7. Run the 40-case red-team test split.
8. Complete the harmful refusal wording review.
9. Only then consider Phase 5 cutover and deletion.
