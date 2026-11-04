# Stage 3 Implementation Report

Status: implementation landed; local adversarial suite ready; local model gate pending.
Date: 2026-11-04.
Branch: `fix/guard-qa-grounding-fixes`.
Worktree: `worktree/c6b606/guard-qa-grounding-fixes`.
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
| Guard schema | Data-driven scopes, three parent safety types, descriptions, fallbacks, 14 examples with complete scope and safety pair coverage |
| Normalizer | Trim, cap, quote repair, course-prefix removal; one canonical label key (NFKC, case fold, apostrophe variants, whitespace) |
| Guard discrimination | Forced `submit_discrimination`, exact spans, ambiguity flags, relationship targets, bounded entity length |
| Guard classification | Forced `submit_classification` on the fixed decomposition, exact label count enforced with `minItems` and `maxItems`, rendered label vocabulary |
| Guard validators | Discrimination spans, order, coverage, relationships, acyclic graph; classification labels, indices, rationales; one retry per stage |
| Policy | One handling per verbatim, aggregate action, redaction, utility invariant |
| Fallback | Canonical text for refusal, boundary, clarification, capability, general, unavailable answer |
| LLM mode | New guard, policy, and bounded QA tool loop |
| Raw SPARQL | Runs first in every mode; validated by the same read-only query guard and bypasses the LLM |
| Graph tools | `resolve_entity`, `discover`, `run_sparql`, row IDs, labels, truncation, typed observations |
| Entity resolution | Normalised exact, prefix, and contains lookup; optional type label or QID; labelled types; exact-first, type, degree ranking; actionable misses |
| Discovery | One `discover(kind, query, subject)` tool; relation labels and aliases; type labels; subject filter; direction, usage, samples; actionable misses |
| Schema card | Curated abstract film schema with four classes and film and person property groups; no instance QIDs |
| QA contract | Ten-section system prompt, film-centred schema card, resolve-first workflow with worked resolve and discovery examples, discovery mandate, three-attempt general answer, native tool-call contract |
| QA loop | Bounded graph steps, one native tool call per turn, required tool choice, separate submit repair budget, repeat-call guard, forced submit after graph budget exhaustion, protocol-error fallback, deadline, deterministic fallback |
| QA validator | Part coverage, order, kind, evidence, values, safety types, clarification shape, redaction overlap |
| Mixed replies | Factual, general, capability, refusal, clarification, and boundary parts in verbatim order |
| Runtime modes | `AGENT_MODE=legacy` and `llm` |
| Session seam | Bounded turn list, safe in-scope user text only |
| Eval data | Three scope relabels, mixed cases keep their safe answer |
| Policy suite | Every scope and safety pair, aggregate action matrix |
| Adversarial suite | 41 multi-part cases, 30 policy branches, three repeats, probe separation |
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
| `agent/tools/resolve.py` | Normalised label lookup, optional type filter, ranked candidates, actionable misses |
| `agent/tools/discover.py` | Relation and type discovery with aliases, subject filter, usage, and samples |
| `agent/tools/registry.py` | Tool lookup and execution for three graph tools |
| `agent/qa/prompts.py` | QA system and user prompts with the resolve-first workflow |
| `agent/qa/actions.py` | Tool schemas for resolve, discover, query, and submit |
| `agent/qa/schema_card.py` | Film-centred schema card rendering |
| `agent/qa/types.py` | Part and result types |
| `agent/qa/validator.py` | Part and grounding checks |
| `agent/qa/agent.py` | Bounded QA loop with separate graph and submit budgets |
| `agent/qa/composer.py` | Deterministic fallback parts |
| `agent/normalize.py` | Input normalisation and the canonical label key |
| `agent/data/movie_schema.json` | Curated abstract film schema card |
| `agent/handlers/llm_agent.py` | LLM runtime handler |
| `agent/llm/client.py` | OpenAI SDK client |
| `agent/llm/health.py` | Endpoint probe |
| `agent/serve.py` | vLLM launcher |
| `agent/observability.py` | Request-scoped JSONL logging, LLM payloads, trace records |
| `requirements.txt` | Agent runtime; no CUDA packages |
| `requirements-serve.txt` | vLLM only; vLLM pins torch and transformers |
| `requirements-legacy.txt` | Optional in-process model for `AGENT_MODE=legacy` |
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
| `agent/guard/discriminator.py` | New discrimination prompt and forced tool; bounded entity length | `test_guard_discriminator` |
| `agent/guard/classifier.py` | Rewritten classification prompt on a fixed decomposition; exact label count; rendered label vocabulary | `test_guard_classifier` |
| `agent/guard/gate.py` | Two chained calls, per-stage retry, merged trace | `test_guard_gate` |
| `agent/guard/policy.py` | Prompt-injection scope, relationship resolution, effective plan | `test_policy`, `test_policy_matrix` |
| `agent/guard/labels.py` | Labels from the effective decision | `test_guard_gate` |
| `agent/guard/session.py` | Only answer-handled safe in-scope text enters the session | `test_runtime_modes` |
| `agent/guard/schema.py`, `agent/data/guardrails.json` | 14 examples with complete scope and safety pair coverage; 240-char rationale, 300-char overview, 8 verbatims | `test_guard_schema` |
| `agent/guard/frames.py` | Deleted; the two-stage LLM owns decomposition | `test_guard_frames` deleted |
| `agent/qa/prompts.py` | Ten sections, resolve-first workflow, worked resolve and discovery examples, discovery mandate, three-attempt general answer, structured submit | `test_qa_contract`, `test_qa_agent` |
| `agent/qa/actions.py` | `discover` schema; type-filtered resolve; no resolve limit | `test_qa_contract` |
| `agent/qa/types.py`, `actions.py`, `agent.py` | Removed the obsolete `assumption` field | `test_qa_contract`, `test_qa_agent` |
| `agent/qa/validator.py` | Effective redaction, including inherited unsafe children; unchanged by this slice | `test_answer_validator` |
| `agent/qa/agent.py` | Repeat-call guard, separate submit repair budget, native tool-call contract, forced submit after graph budget exhaustion, 300-token step cap | `test_qa_agent`, `test_llm_integration` |
| `agent/qa/composer.py` | Distinct observations across answer parts | `test_composer` |
| `agent/qa/schema_card.py`, `agent/data/movie_schema.json` | Film-centred abstract schema card; grouped rendering; no instance QIDs | `test_qa_contract` |
| `agent/tools/resolve.py`, `agent/lexicon.py`, `agent/normalize.py` | Normalised lookup, optional type filter, strict `film` metadata, broader legacy movie test, actionable misses | `test_resolve`, `test_factual` |
| `agent/tools/discover.py` | One discovery tool for relation and type search | `test_discover` |
| `agent/parser.py`, `agent/preprocess.py` | Canonical label key; legacy movie-like resolution | `test_parser`, `test_preprocess`, `test_factual` |
| `agent/handlers/llm_agent.py` | Session text from the decision plan | `test_runtime_modes` |
| `agent/config.py`, `agent/llm/factory.py`, `agent/llm/client.py` | Local endpoint settings, `MAX_SUBMIT_REPAIRS`, `RESOLVE_FUZZY`, and local client factory | `test_config`, `test_llm_client` |
| `agent/guard/verdict.py` | Resolved relationships require an explicit entity; null is missing-target only | `test_guard_verdict` |
| `evals/stage3_guardrails.jsonl` | Three relational cases | `test_eval_data` |
| `evals/adversarial/policy_e2e.jsonl` | 41 adversarial multi-part cases | `test_policy_e2e_data` |
| `scripts/adversarial/run_policy_e2e.py` | Branch-aware e2e runner and results | manual |
| Design records | `REPORT`, `IMPACT`, `PLAN`, `IMPLEMENTATION`, `POLICY_MAP`, spec, tickets | review |

## 3. Verification

| Command | Result |
|---|---|
| `pytest -q` | 686 passed |
| `python -m compileall -q agent scripts tests` | clean |
| `agent.eval evals/stage1_sparql.jsonl` | 9 of 9 |
| `agent.eval evals/stage2_factual.jsonl` | 508 of 508 |
| `agent.eval evals/stage2_factual_negation.jsonl` | 9 of 9 |
| `agent.eval` on the three legacy suites together | 526 of 526 |
| `agent.eval evals/stage3_guardrails.jsonl` in `llm` with no model | 0 of 47, expected |
| `agent.eval evals/stage1_sparql.jsonl --json ...` | 9 of 9, one result object per case |
| `scripts/scoreboard.py ...` | 9 of 9, 0 failed |
| `tests/test_eval.py`, `tests/test_scorecard.py` | `labels_any_of` accepts harmful or toxic |

The 0 of 47 run is a no-model run.
The guard suite needs an endpoint.
It is not a code failure.

### 3.1 Real-graph smoke checks

The worktree has no `dataset/` directory.
The checks used the sibling graph and store at `/Users/diekgbbtt/atai-conversation-agent/dataset/graph.nt` and `/Users/diekgbbtt/atai-conversation-agent/kg_store`.

| Check | Result |
|---|---|
| `resolve_entity("Jaws", type="film")` | `Q189505` first |
| `resolve_entity("The Godfather")` | `Q47703` first; `Q3225260` is a film trilogy with `film=False` |
| `resolve_entity("Schindler’s List")` | `Q483941` for curly and straight apostrophes |
| `resolve_entity("Godfahter")` | actionable error by default; resolves with `RESOLVE_FUZZY=1` |
| `discover("relation", "composer")` | `P86` |
| `discover("relation", "genre", subject="Q11424")` | `P136` |
| `discover("type", "film")` | `Q11424` first; `Q24856` and `Q13593818` also returned |
| `discover("type", "human")` | `Q5` |

The graph has 2,413,825 triples, 12,245 films, 85,854 humans, 122,774 label keys, and 129,360 typed entities.

The legacy evaluation exposed one regression after strict `film` was introduced.
`Toy Story` is `P31 Q202866` (animated film), not `P31 Q11424`.
The legacy pipeline now uses `is_movie` (`P31 Q11424` or a director fact) for question resolution.
The QA resolver keeps strict `film` metadata and the strict `type="film"` filter.

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
| Live guard and QA prompt behaviour | no local endpoint |
| Held-out factual accuracy | the held-out set does not exist yet |
| Harmful refusal wording review | needs a human safety reviewer |
| Red-team split | the 40-case test split does not exist yet |
| Self-harm refusal wording | policy fixed; human wording review remains |

The T4 serving spike remains the first local empirical gate.
The design keeps one shared local model and one vLLM process for the guard and QA roles.
The spike must prove that the shared model fits 16 GB and meets both latency budgets.

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
- The prompt mandates resolution before every graph query, and the worked trajectory resolves Jaws before the SPARQL call.
- `discover` finds a relation from a label, an alias, or a property ID.
- `discover` finds a type from a label or QID, including `Q5`, whose node is absent from the graph.
- A subject filter reports relation direction, usage, and a retry hint when no relation matches.
- A type filter that excludes every exact-label candidate returns a retry hint instead of a different title.
- `film` is strict `P31 Q11424` in entity resolution metadata.
- An animated film without `P31 Q11424` stays answerable through the broader legacy movie test.
- Apostrophe variants and case differences resolve to the same entity.
- A resolution miss returns an actionable retry instruction; fuzzy fallback is opt-in.
- The final graph step forces `submit_response`.
- A content-only reply is a protocol error and uses the deterministic fallback.
- Submit repairs do not consume graph tool steps.
- The three-attempt general answer rule is prompt-only.
- The schema card carries no instance QIDs.
- The guard classifier renders every label with valid `safety` and `unsafe_types` vocabulary.
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
4. The guard classifier prompt carries all 14 label examples.
   Eight examples cover every scope and safety pair.
   Six calibration examples cover boundary cases.
   Every example uses `safety=safe|unsafe` plus `unsafe_types`.
   The schema allows several examples per pair and requires complete pair coverage.
5. The QA prompt has ten sections, not nine.
   The added `Workflow` section makes resolution a fixed step before SPARQL.
   It remains one system prompt, not one prompt per action.
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
15. The guard keeps three parent safety types and one shared local model.
    One vLLM process serves both roles.
    The six-type, two-model alternative was rejected.
16. Entity resolution is a fixed workflow step before `run_sparql`.
    The prompt carries a worked `discover -> resolve -> query` example.
17. `film` means strict `P31 Q11424` in `resolve_entity` metadata and the type filter.
    The legacy deterministic pipeline keeps a broader `is_movie` test (`P31 Q11424` or a director fact).
    This keeps animated films without `P31 Q11424` answerable.
18. A resolution miss is an actionable error by default.
    Bounded fuzzy fallback is opt-in through `RESOLVE_FUZZY=1`.
19. The graph tool budget and the submit repair budget are separate.
    `MAX_AGENT_STEPS=6` counts graph tools.
    `MAX_SUBMIT_REPAIRS=3` counts invalid submissions.
20. A content-only reply is a protocol error and uses the deterministic fallback.
    An exhausted graph budget forces `submit_response`.
21. The three-attempt `general_answer` rule is prompt-only.
    The runtime does not count attempts, so the loop stays simple and the deadline holds.
22. The QA validator is unchanged.
    Its known risks are recorded for later evals.
    A non-factual part can still state a graph fact.
    A refusal can still repeat method details.
23. The schema card is a curated abstract film schema, not a closed set of entity instances.
    Runtime resolution supplies the entities.
24. `discover` is one tool with a `kind` enum instead of separate relation and type tools.
    Relation search matches labels, aliases, and property IDs.
    Type search matches class labels and QIDs.

## 7. Next Steps

1. Run the Phase 1 serving spike on the T4 with one shared model and one vLLM process.
2. Run the 41-case policy suite on the local endpoint.
3. Run the new discovery and resolve-first QA trajectories on the local endpoint.
4. Review the self-harm refusal wording with a human reviewer.
5. Keep the harmful/toxic overlap acceptable through `labels_any_of`.
6. Improve the QA model path for multi-answer tool loops; the fallback is correct but the model path is not.
7. Add eval coverage for the two unchanged QA validator risks: non-factual graph facts and refusal method details.
8. Build and freeze the held-out factual set.
9. Run the 40-case red-team test split.
10. Complete the harmful refusal wording review.
11. Only then consider Phase 5 cutover and deletion.
