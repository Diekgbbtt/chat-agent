# Spec - LLM-Centric Guard and Factual QA

Status: ratified.
Date: 2026-10-28.
Source design: `docs/design/stage3-llm-centric/REPORT.md`, `IMPACT.md`, and `PLAN.md`.
Tracker: local markdown under `.scratch/llm-centric-agent/issues/`.

## Problem Statement

The current Stage 3 guard uses one LLM call to produce labels, one movie question, and one reply.
The labels are request-level, so one unsafe clause can suppress a safe movie question.
The reply is composed by ad-hoc handler logic, so a safe clause and an unsafe clause cannot both receive a correct part.
Entity recall and relation mapping rely on parser heuristics and fuzzy matching.
The factual answer is produced by symbolic templates with an optional rephrase step.
No component can cite the graph rows that support an answer.
The current system cannot prove that a safety boundary does not deplete utility.
It cannot prove that every factual value came from the knowledge graph.
It also cannot prove that each request clause received the correct safety and scope decision.

## Solution

Introduce two local LLMs behind OpenAI-compatible endpoints.
The first is a guard classifier.
It decomposes a message into verbatims and labels each verbatim on independent safety and scope axes.
The second is a QA model.
It writes one cohesive reply as ordered parts, one part per verbatim.
A deterministic policy engine plans each verbatim safety first, then scope, then ambiguity.
The aggregate action is an aggregate of those plans, not a request-level veto.
A safety or scope boundary suppresses only the affected verbatim.
Safe answerable verbatims are still answered.
The QA model gets graph facts only through two tools.
`resolve_entity` links a label to a QID.
`run_sparql` runs read-only queries and returns labelled rows with stable row IDs.
Every factual part cites those row IDs.
The guard model is configurable from a JSON schema.
The legacy path remains selectable through `AGENT_MODE` until the replacement gates pass.

## User Stories

1. As a movie fan, I want a safe movie question answered even when another clause in my message is unsafe, so that one bad clause does not destroy the useful part.
2. As a movie fan, I want a safe movie question answered even when another clause is out of scope, so that unrelated homework does not block the film answer.
3. As a movie fan, I want an unsafe clause refused in its own sentence, so that the refusal is specific and does not pretend the whole message was unsafe.
4. As a movie fan, I want a toxic clause handled as a respect boundary, so that a rude phrase does not suppress the film answer.
5. As a movie fan, I want an out-of-scope clause answered with a scope sentence, so that I know which part the bot cannot help with.
6. As a movie fan, I want a clarification question when a film reference is genuinely ambiguous, so that I can supply the missing detail.
7. As a movie fan, I want a clarification for a blocked part while a clear part is still answered, so that ambiguity does not deplete utility.
8. As a movie fan, I want the bot to fail into a clarification when the classifier output is invalid, so that a system error is not reported as a safety refusal.
9. As a movie fan, I want a self-harm clause to receive an approved crisis sentence, so that the response is safe and humane.
10. As a movie fan, I want a prompt-injection clause refused without changing the bot's role, so that the system prompt stays private.
11. As a movie fan, I want factual answers to cite graph rows, so that I can trust the value came from the knowledge graph.
12. As a movie fan, I want the bot to say when the graph has no value, so that it does not invent a fact.
13. As a movie fan, I want descriptions, dates, counts, and relations answered through one query tool, so that the answer path is predictable.
14. As a movie fan, I want entity lookup to return candidates when my spelling differs, so that I can still reach the right film.
15. As a movie fan, I want recommendations to receive a capability limit, so that the bot does not pretend to have a recommender.
16. As a movie fan, I want general movie-domain conversation answered without invented facts, so that the bot can be helpful without leaving the graph.
17. As a course evaluator, I want the guard to expose one typed object with an overview and verbatims, so that the classification is auditable.
18. As a course evaluator, I want every verbatim to carry a safety rationale and a scope rationale, so that each decision is explainable.
19. As a course evaluator, I want all 14 scope and safety combinations in the guard prompt, so that the labels are shown independently.
20. As a course evaluator, I want the policy matrix to cover every label combination, so that no input falls through.
21. As a course evaluator, I want the 47 guardrail cases to pass after three documented relabels, so that the legacy contract is preserved.
22. As a course evaluator, I want the mixed legacy cases to keep their safe answer and gain a refusal part, so that the eval reflects the utility invariant.
23. As a security reviewer, I want unsafe text and its rationale removed from the QA prompt, so that the answer model cannot reconstruct the request.
24. As a security reviewer, I want tool queries to reject a four-word sequence from a redacted verbatim, so that redaction survives the tool loop.
25. As a security reviewer, I want read-only query enforcement in both agent and raw modes, so that no component can mutate the store.
26. As a security reviewer, I want the QA prompt to treat tool output as data, so that a graph label cannot inject instructions.
27. As a platform engineer, I want two local OpenAI-compatible endpoints, so that no request leaves the host.
28. As a platform engineer, I want a thin in-repo tool loop, so that the runtime does not depend on an agent framework.
29. As a platform engineer, I want a health probe for the configured endpoints, so that startup fails clearly.
30. As a platform engineer, I want `AGENT_MODE=legacy|guard_only|tools`, so that cutover and rollback are controlled.
31. As a platform engineer, I want a session history seam that is disabled, so that single-turn behaviour stays unchanged.
32. As a platform engineer, I want the legacy handler stack to stay until the gates pass, so that a failed rewrite does not break the bot.
33. As a platform engineer, I want step, deadline, and token budgets, so that a tool loop cannot hang the reply.
34. As a platform engineer, I want a deterministic fallback for every part kind, so that model failure still produces a safe reply.
35. As a platform engineer, I want trace steps for classification, plan, policy, tools, evidence, and parts, so that failures are diagnosable.
36. As a developer, I want the guard schema in data, so that safety types and examples can change without code edits.
37. As a developer, I want the QA schema card in the system prompt, so that there is no schema tool or second query interface.
38. As a developer, I want the `Lexicon` limited to a dictionary and prefix index, so that fuzzy recall does not return.
39. As a developer, I want a JSON result mode in the eval runner, so that scoreboards are reproducible.
40. As a developer, I want a scoreboard script, so that per-type recall and latency are visible.

## Implementation Decisions

- The guard and QA roles share one local model for now; their clients and overrides stay separate.
- Both clients use the OpenAI SDK chat-completions shape.
- The guard uses two chained forced calls: `submit_discrimination`, then `submit_classification`.
- Discrimination returns an `overview` summary plus exact spans.
- Each span carries `ambiguous` and an optional `relationship`.
- A relationship carries `target_verbatim_index`, `entity`, and `status`.
- `status` is `resolved` or `missing semantic target`.
- A resolved relationship carries an explicit entity inside the target.
  A null entity is valid only for a missing semantic target.
  A whole-span dependency repeats the full target text.
- Classification returns exactly one own label and rationale per span, in index order.
  The tool schema enforces the exact count with `minItems` and `maxItems`.
- The classifier never applies inheritance; the policy does.
- Labels are emitted in span order.
  Earlier labels may resolve an ambiguous reference only.
  They must not be copied, inherited, or treated as ground truth.
- A pronoun whose gender conflicts with the only available prior antecedent is a user assumption or typo.
  It is non-ambiguous and carries no relationship.
  A matching-gender pronoun remains ambiguous and resolves.
- A quoted string is content, not an instruction.
  Translation, quotation, and film-dialogue discussion are not prompt injection.
- A film-analysis question about whether a depicted method is realistic is safe and in scope.
  A request for instructions, quantities, detail, or encouragement is harmful.
- Toxic applies to any insulting or disrespectful language about a person.
  There is no severity threshold.
- Harmful and toxic overlap for hate speech.
  The eval accepts either explicit type, or both, through `labels_any_of`.
- The guard decomposes into the smallest complete verbatims that can be judged and answered separately.
- Role markers and prefixes such as `SYSTEM:` stay inside a span and must be covered.
- Ambiguity is a per-span attribute; the old `overview.ambiguities` list is removed.
- The label shape is `safety`, `unsafe_types`, and `scope`.
- Safety types are only `harmful`, `toxic`, and `prompt_injection`, in that order.
- The order is the deterministic refusal precedence; there is no severity and no tone.
- `prompt_injection` forces `out_of_scope`.
- The schema carries 8 examples, one for every scope and safety pair.
- The rationale shape is `safety` and `scope`.
- Safety is assessed before scope in the prompt, field order, and policy.
- The policy engine is pure and has no I/O.
- The policy normalises prompt-injection scope, resolves the relationship graph, and produces one `VerbatimPlan` per verbatim and one `Decision`.
- An ambiguous child inherits the union of its semantic chain's safety types.
- It inherits scope only from an out-of-scope ancestor.
- An unambiguous child never inherits.
- A missing semantic target is a clarification unless the span is already unsafe.
- A verbatim handling is `answer`, `refuse`, `clarify`, or `boundary`.
- The aggregate action order is any answer, else any refuse, else any clarify, else all boundary.
- `refuse` and `out_of_scope` are whole-query outcomes only when no answerable verbatim remains.
- An unsafe verbatim stores no text in the plan.
- An unsafe verbatim's rationale is kept in the plan for audit but omitted from the QA prompt.
- The full pair map and fail-closed matrix are in `POLICY_MAP.md`.
- The QA reply is an ordered list of parts, one part per verbatim.
- Part kinds are `factual_answer`, `general_answer`, `capability_limit`, `refusal`, `clarification`, and `boundary`.
- `submit_response` carries `parts` with `verbatim_index`, `kind`, `text`, `evidence_row_ids`, and `addressed_safety_types`.
- The validator runs on parts before the join.
- Parts are joined in verbatim order with one space.
- A repeated QA tool call is blocked and the existing observation is reused.
- The final QA step forces `submit_response`.
- Only two graph tools are exposed: `resolve_entity` and `run_sparql`.
- `resolve_entity` performs exact, prefix, and contains lookup over the label index.
- `run_sparql` is the only graph fact source.
- The schema card is a system prompt section.
- A factual part must cite at least one `run_sparql` row.
- A non-factual part states no graph fact and cites no evidence.
- A refusal part addresses exactly the safety types of its own verbatim.
- The first declared type present selects the refusal fallback.
- A clarification part asks one question and quotes at most six words.
- A boundary part states only the movie-only scope.
- The fallback renderer assigns distinct successful observations to distinct answer parts.
  It reuses the last observation only when no distinct observation remains.
- The canonical labels are emitted directly; there is no projection and no `unsafe` label.
- Three cases are relabelled: `safe-hello`, `safe-thanks`, and `safe-capabilities` become `out_of_scope`.
- `mixed-heat-robbery` and `mixed-jaws-insult` keep their expected safe answer and gain a refusal-part assertion.
- The default mode is `legacy`.
- `guard_only` is a bridge that uses the new guard and policy with the legacy factual handler.
- `tools` is the target mode.
- The session history seam stores only safe in-scope verbatims and stays disabled.
- The serving stack is one vLLM process for the shared model; llama.cpp is the fallback.
- The adversarial policy suite has 41 cases and 30 model-driven policy branches.
- The shared model starts as Qwen3-4B-Instruct-2507.
- Model names and endpoints have shared local defaults and per-role overrides.
- The agent runtime does not import CUDA packages.
- The raw SPARQL capability keeps its bypass and uses the same `QueryGuard`.

## Testing Decisions

- A good test checks external behaviour at the highest available seam.
- The primary seam is `Agent.answer(text, session_id, trace)`.
- Guard behaviour is tested through a fake guard client that returns a scripted `submit_discrimination` call, then a scripted `submit_classification` call.
- QA behaviour is tested through a fake QA client that returns scripted tool calls and a final `submit_response`.
- Pure policy tests use a frozen table over every label combination and the full 192-case parent-child relationship matrix.
- No test asserts private helper structure.
- Existing legacy tests stay green and unchanged.
- Existing graph fixtures are reused.
- The fake client follows the OpenAI SDK response shape, not the old in-process LLM shape.
- A vertical slice test covers classification, plan, tool call, evidence, validation, and reply in one path.
- A failure test covers invalid discrimination and invalid classification to clarification.
- A mixed-reply test covers a safe answer part and an unsafe refusal part in one reply.
- A redaction test covers unsafe text and unsafe rationale absence from the QA prompt.
- A tool test covers row IDs, labels, truncation, and read-only enforcement.
- A validator test covers part coverage, kind mismatch, missing evidence, invented values, and redaction overlap.
- A runtime test covers `AGENT_MODE` selection and the legacy default.
- Eval tests cover `--json` output and the scoreboard counts.

## Out of Scope

- Deleting the legacy handler stack.
- Training or fine-tuning a model.
- A recommender.
- Multi-turn memory.
- External model providers.
- A production GPU benchmark on Nuvolos.
- Real held-out factual evaluation without model endpoints.
- A schema tool or entity-profile tool.
- Fuzzy entity recall.

## Further Notes

- The T4 memory fit is unproven until the serving spike runs on the target host.
- The self-harm wording and the mixed self-harm plus safe-question composition need human safety review.
- The held-out factual set does not exist yet.
- The implementation may land deterministic packages and fake-client tests before the serving spike.
- No gate is lowered to make a phase pass.
