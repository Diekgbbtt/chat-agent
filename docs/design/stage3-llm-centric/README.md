# Stage 3 LLM-Centric Redesign

Status: design proposal, awaiting approval.
Date: 2026-10-28.

This folder contains three documents.

| Document | Purpose |
|---|---|
| `REPORT.md` | Current system grounding, target design, diagrams, per-verbatim plan and aggregate action, risk model, and reasoning workflows |
| `IMPACT.md` | Codebase impact assessment, reuse verdict, new and obsolete constructs, tests, and dependencies |
| `PLAN.md` | Strict rewrite plan with phases, gates, feedback loops, and stop rules |

The short version:

1. The guard classifier decomposes the message into verbatims and labels each on two independent axes: safety and scope.
2. Safety is assessed before scope for every verbatim. A per-verbatim plan handles each label combination.
3. A safety or scope boundary does not deplete utility. A mixed reply answers the safe verbatims and refuses the unsafe parts.
4. The QA model writes one cohesive reply as ordered parts, one per verbatim.
5. Two graph tools exist: `resolve_entity` and `run_sparql`. The schema card is a system prompt section, not a tool.
6. An invalid classification fails safe with an ambiguous description and one question, not a refusal.
7. The `Lexicon` stays as a dictionary and query-parameterisation helper.
8. The parser, preprocessor, template builder, rephrase step, and handler chain become obsolete.
9. The legacy path stays behind `AGENT_MODE` until the stratified gates pass.

Open the report first.
It documents the guard and QA reasoning workflows.
Use the plan for execution.
