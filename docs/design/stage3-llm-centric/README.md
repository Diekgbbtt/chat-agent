# Stage 3 LLM-Centric Redesign

Status: design ratified; deterministic runtime implemented; local adversarial gate pending; T4 gate blocked.
Date: 2026-11-02.

This folder contains the design documents, the implementation record, the policy map, and the local evaluation record.

| Document | Purpose |
|---|---|
| `REPORT.md` | Current system grounding, target design, diagrams, per-verbatim plan and aggregate action, risk model, and reasoning workflows |
| `IMPACT.md` | Codebase impact assessment, reuse verdict, new and obsolete constructs, tests, and dependencies |
| `PLAN.md` | Strict rewrite plan with phases, gates, feedback loops, and stop rules |
| `IMPLEMENTATION.md` | What landed, verification evidence, deviations, and the blocked model gates |
| `POLICY_MAP.md` | Two-stage guard, ambiguity and relationship rules, full pair map, fail-closed matrix, and residual risk |
| `../adversarial/policy-e2e/REPORT.md` | 41-case local adversarial policy-map suite and residuals |

The short version:

1. The guard runs two chained model calls: discrimination, then classification.
   Discrimination produces the smallest complete verbatims and their ambiguity relationships.
   Classification returns exactly one own label per span.
   The tool schema enforces the exact count.
2. Safety is assessed before scope for every verbatim. A per-verbatim plan handles each label combination.
3. A safety or scope boundary does not deplete utility. A mixed reply answers the safe verbatims and refuses the unsafe parts.
4. The policy resolves ambiguity relationships symbolically. An ambiguous child inherits the safety types of its unambiguous target.
5. The QA role writes one cohesive reply as ordered parts, one per verbatim.
6. The guard and QA roles share one local model for now; their clients and overrides stay separate.
7. Two graph tools exist: `resolve_entity` and `run_sparql`. The schema card is a system prompt section, not a tool.
8. An invalid discrimination or classification fails safe with a clarification after one retry.
9. The `Lexicon` stays as a dictionary and query-parameterisation helper.
10. The parser, preprocessor, template builder, rephrase step, and handler chain become obsolete.
11. The legacy path stays behind `AGENT_MODE` until the stratified gates pass.

Open the report first.
It documents the guard and QA reasoning workflows.
Use the plan for execution.
