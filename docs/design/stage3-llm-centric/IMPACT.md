# Codebase Impact Assessment

Status: design proposal.
Date: 2026-10-28.
This document maps the current software constructs to the target design.
It is the precise delta between the current codebase and the target in `REPORT.md`.
The rewrite sequence is in `PLAN.md`.

## 1. How to read the decisions

| Decision | Meaning |
|---|---|
| Keep | The construct stays with no behavioural change. |
| Adapt | The construct stays, but its interface or owner changes. |
| Rewrite | The construct keeps its public role but gets a new implementation. |
| Reuse as data | The code is removed as runtime logic, but its content becomes prompt data, test data, or documentation. |
| Obsolete | The construct is removed after the cutover. |
| New | The construct does not exist today. |

The target keeps the environment adapters.
It removes the symbolic decision stack.
It replaces the single shared in-process LLM with a guard role and a QA role over a shared local model.
It replaces the handler chain with one runtime and one bounded tool loop.

## 2. Construct inventory

### 2.1 Transport and process lifecycle

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `main` | `agent/__main__.py` | 54 | Load settings, open graph, build agent, start bot | Adapt | Add model health check and `AGENT_MODE`; keep shutdown order |
| `setup_logging` | `agent/__main__.py` | 12 | Speakeasy logger | Keep | No change |
| `SpeakeasyBot` | `agent/speakeasy_bot.py` | 173 | Dispatch, compute, room locks, reconnect, heartbeat | Keep | Transport is orthogonal to the redesign |
| `_compute_reply` | `agent/speakeasy_bot.py` | 93-108 | Timeout and error fallback | Keep | Tune `reply_timeout_s` after the latency spike |
| `_post` | `agent/speakeasy_bot.py` | 110-119 | Post retry | Keep | No change |
| `build_store` | `agent/build_store.py` | 29 | One-time store build | Keep | No change |

### 2.2 Core orchestration

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `Session` | `agent/core.py` | 20-24 | Room identifier and empty state dict | Adapt | Add bounded turn list and sanitised recording |
| `Trace` | `agent/core.py` | 26-33 | `(step, detail)` list | Adapt | Keep shape; add guard, policy, tool, evidence, fallback steps |
| `Agent` | `agent/core.py` | 36-60 | Session map and first-handler routing | Obsolete | Replaced by `AgentRuntime`; the handler chain disappears |
| `Agent.answer` | `agent/core.py` | 50-60 | Trim, empty check, handler loop | Rewrite | The signature and eval contract stay; the body becomes the guard and policy flow in `AgentRuntime.answer` |
| `build_agent` | `agent/core.py` | 63-70 | Handler list selection | Obsolete | Replaced by `build_runtime` |
| `EMPTY_REPLY` | `agent/core.py` | 17 | Empty input reply | Keep | No change |
| `MAX_INPUT_CHARS` | `agent/core.py` | 16 | 5,000 character cap | Keep | No change |

### 2.3 Safety and guardrails

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `LABELS` | `agent/guardrails.py` | 11 | Five hardcoded labels | Reuse as data | Seed the canonical label vocabulary used by the 47-case eval; not a policy input |
| `SYSTEM_PROMPT` | `agent/guardrails.py` | 16-38 | One prompt for labels, span, and reply | Obsolete | Replaced by a generated two-axis classification prompt |
| `EXAMPLES` | `agent/guardrails.py` | 41-59 | Five worked examples | Reuse as data | Seed adversarial cases and prompt style; the new prompt carries the 8 pair examples |
| `Verdict` | `agent/guardrails.py` | 62-66 | Labels, movie question, reply | Adapt | Split into `Discrimination`, `Verdict`, and `Decision`; ambiguity becomes a per-span relationship |
| `_parse` | `agent/guardrails.py` | 69-78 | JSON extraction and label filter | Obsolete | Replaced by a forced tool call and a verbatim validator |
| `_messages` | `agent/guardrails.py` | 81-85 | Prompt assembly | Obsolete | Replaced by the `GuardDiscriminator` and `GuardClassifier` prompt builders |
| `Guardrails.check` | `agent/guardrails.py` | 92-101 | LLM call and fail-open fallback | Obsolete | Replaced by `GuardGate.classify` with a fail-safe clarification |
| `MAX_REPLY_CHARS` | `agent/guardrails.py` | 13 | Refusal length bound | Adapt | Move to `AnswerValidator` |
| `EMERGENCY_REPLY` | `agent/guardrails.py` | 14 | Fixed refusal | Reuse as data | One canonical fallback sentence in the policy data |

### 2.4 Factual pipeline

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `Preprocessor` | `agent/preprocess.py` | 567 | Quote repair, clause stripping, mention scan, negation, claims, rewriting | Obsolete | The LLM handles meaning; keep only the quote and prefix helpers |
| `Plan` | `agent/preprocess.py` | 84-92 | Preprocessing result | Obsolete | Replaced by `AgentState` and `Decision` |
| `Claim` | `agent/preprocess.py` | 77-81 | Yes or no claim | Obsolete | The LLM writes an `ASK` query |
| `Resolution` | `agent/preprocess.py` | 95-99 | Entity candidates | Obsolete | `resolve_entity` returns candidates |
| `_Mention` | `agent/preprocess.py` | 102-108 | Mention span | Obsolete | No mention scanner |
| `Preprocessor.analyze` | `agent/preprocess.py` | 132-160 | Full normalisation pipeline | Obsolete | No semantic preprocessing |
| `_normalise_quotes` | `agent/preprocess.py` | 172-199 | Curly quote repair | Adapt | Move a small version to `normalize.py` |
| `_quoted_spans` | `agent/preprocess.py` | 244-267 | Quoted title scan | Obsolete | `resolve_entity` handles lookup |
| `_scan` | `agent/preprocess.py` | 290-337 | Mention scan | Obsolete | No mention scanner |
| `_detect_claim` | `agent/preprocess.py` | 508-531 | Claim regex | Obsolete | The LLM handles yes or no questions |
| `_rewrite` | `agent/preprocess.py` | 535-555 | Quote the best mention | Obsolete | No text rewriting |
| `Parser` | `agent/parser.py` | 201 | Entity, predicate, direction, kind | Obsolete | Replaced by LLM tool use and `Lexicon` lookups |
| `Question` | `agent/parser.py` | 36-43 | Parsed question | Obsolete | Replaced by the QA prompt and tool observations |
| `Parser.parse` | `agent/parser.py` | 79-109 | Four-step parse | Obsolete | The QA LLM writes the query |
| `_find_entity` | `agent/parser.py` | 116-170 | Quoted, capitalised, lower-case, fuzzy recall | Obsolete | `resolve_entity` does exact, prefix, and contains lookup |
| `_find_predicates` | `agent/parser.py` | 111-114 | Phrase map | Obsolete | The schema card and prompt examples do relation mapping |
| `_rank` | `agent/parser.py` | 195-201 | Film first, then degree | Obsolete | The tool returns metadata; the LLM decides |
| `_surname_candidates` | `agent/parser.py` | 188-193 | Surname heuristic | Obsolete | The LLM can try the full name or surname |
| `STOPWORDS` | `agent/parser.py` | 24-25 | Word list | Reuse as data | May move to `normalize.py` or disappear |
| `APPROACH_PREFIX` | `agent/parser.py` | 30 | Course prefix regex | Adapt | Move to `normalize.py` |
| `sparql_builder` | `agent/sparql_builder.py` | 97 | Runtime query templates | Reuse as data | Convert to prompt examples and eval ground truth |
| `lookup` | `agent/sparql_builder.py` | 41-43 | Lookup template | Reuse as data | Prompt example |
| `count` | `agent/sparql_builder.py` | 46-50 | Count template | Reuse as data | Prompt example |
| `complement` | `agent/sparql_builder.py` | 67-77 | Negation template | Reuse as data | Prompt example |
| `claim` | `agent/sparql_builder.py` | 87-89 | Ask template | Reuse as data | Prompt example |
| `superlative` | `agent/sparql_builder.py` | 92-97 | Earliest or latest template | Reuse as data | Prompt example |
| `FactualHandler` | `agent/handlers/factual.py` | 107 | Plan, query, rows, answer | Obsolete | Replaced by `ResponseAgent` and tools |
| `FactualHandler.handle` | `agent/handlers/factual.py` | 22-76 | Branching on kind and error | Obsolete | The LLM chooses the query; the renderer formats rows |
| `_rank_complement` | `agent/handlers/factual.py` | 78-100 | Degree-ranked complement | Obsolete | The tool can return degree; the LLM decides |
| `GuardedHandler` | `agent/handlers/guarded.py` | 39 | Guard plus factual plus rephrase | Obsolete | Replaced by `AgentRuntime`, `PolicyEngine`, and `ResponseAgent` |
| `rephrase` | `agent/rephrase.py` | 30 | Second LLM call and substring check | Obsolete | The QA LLM writes the answer; `AnswerValidator` keeps the check |
| `MAX_VALUES` | `agent/rephrase.py` | 8 | Rephrase bound | Adapt | Move to `AnswerValidator` |
| `MAX_EXTRA_CHARS` | `agent/rephrase.py` | 9 | Rephrase length bound | Adapt | Move to `AnswerValidator` |

### 2.5 Knowledge graph and vocabulary

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `KnowledgeGraph` | `agent/kg.py` | 173-228 | Store, query pool, timeout, row cap | Keep | It becomes the backend of `run_sparql` |
| `KnowledgeGraph.query` | `agent/kg.py` | 215-225 | Query with timeout | Keep | Add no behaviour; the tool wraps it |
| `SelectResult` | `agent/kg.py` | 56-60 | Columns, rows, truncation | Keep | Used by `ResultFormatter` |
| `Term` | `agent/kg.py` | 48-53 | Typed term | Keep | Used by `ResultFormatter` |
| `PREFIXES` | `agent/kg.py` | 27-34 | Default prefixes | Keep | The QA prompt uses the same prefixes |
| `Lexicon` | `agent/lexicon.py` | 17-47 | Label, property, type index | Adapt | Keep as dictionary; add a prefix index; no fuzzy |
| `Lexicon.ent2lbl` | `agent/lexicon.py` | 19 | QID to label | Keep | Used by the entity resolver and formatter |
| `Lexicon.lbl2ent` | `agent/lexicon.py` | 20 | Label to QIDs | Keep | Used by exact and prefix search |
| `Lexicon.prop2lbl` | `agent/lexicon.py` | 21 | Predicate to label | Keep | Used by the formatter and schema card |
| `Lexicon.types` | `agent/lexicon.py` | 22 | Entity to classes | Keep | Used to show types and film or human metadata |
| `Lexicon.directed` | `agent/lexicon.py` | 23 | Entities with a director | Keep | Used as a film signal |
| `Lexicon.is_film` | `agent/lexicon.py` | 43-44 | Film test | Keep | Presentation metadata, not a decision |
| `Lexicon.is_human` | `agent/lexicon.py` | 46-47 | Human test | Keep | Presentation metadata |
| `relations.json` | `agent/data/relations.json` | data | Hand-written relation synonyms | Reuse as data | Move to prompt examples or test fixtures; remove from runtime |

### 2.6 Text output

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `format_term` | `agent/nlg.py` | 19-24 | Format an RDF term | Keep | Used by the result formatter |
| `short_iri` | `agent/nlg.py` | 12-16 | Shorten an IRI | Keep | Used by the raw SPARQL capability |
| `join_and` | `agent/nlg.py` | 27-29 | Join values with "and" | Keep | Used by the fallback renderer |
| `answer` | `agent/nlg.py` | 32-34 | Template answer | Obsolete | Replaced by `qa/renderer.py` |
| `no_entity` | `agent/nlg.py` | 37-38 | Unknown entity text | Obsolete | The QA model writes the clarification; the schema holds the fallback |
| `no_relation` | `agent/nlg.py` | 41-42 | Unknown relation text | Obsolete | The QA model writes the scope or no-facts reply; the schema holds the fallback |
| `no_facts` | `agent/nlg.py` | 45-46 | Missing facts text | Obsolete | The QA model writes the no-facts reply; the schema holds the fallback |

### 2.7 LLM runtime

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `LLM` | `agent/llm.py` | 10-27 | In-process transformers model | Obsolete | Replaced by `LLMClient` over the OpenAI SDK |
| `LLM.__init__` | `agent/llm.py` | 11-19 | Model load and lock | Obsolete | Model serving moves to vLLM or llama.cpp |
| `LLM.chat` | `agent/llm.py` | 21-27 | Chat template and generate | Obsolete | Replaced by `chat.completions.create` |
| `load_llm` | `agent/cli.py` | 24-28 | Lazy model load | Obsolete | Replaced by `load_clients` |

### 2.8 Configuration and tools

| Construct | Path | Lines | Current role | Target decision | Notes |
|---|---|---|---|---|---|
| `Settings` | `agent/config.py` | 80-95 | Runtime settings | Adapt | Add model endpoints, schema path, agent mode, budgets, history flag |
| `load_settings` | `agent/config.py` | 98-115 | Environment and `.env` load | Adapt | Add the new keys; keep the existing precedence |
| `load_dotenv` | `agent/config.py` | 45-53 | `.env` support | Keep | No change |
| `parse_dotenv` | `agent/config.py` | 21-37 | `.env` parser | Keep | No change |
| `cli` | `agent/cli.py` | 62 | Offline chat and debug | Adapt | Load two clients; add `--mode` and the `llm` runtime |
| `eval` | `agent/eval.py` | 60 | JSONL regression runner | Adapt | Add suites, modes, per-label metrics, and latency report |
| `passes` | `agent/eval.py` | 25-30 | Expected, forbidden, labels | Adapt | Add `labels_any_of` for inherently overlapping types; exact labels stay the default |
| `SparqlHandler` | `agent/handlers/sparql.py` | 48-73 | Raw SPARQL capability | Adapt | Move to `RawSparqlCapability`; reuse the same tool and query guard |
| `looks_like_sparql` | `agent/handlers/sparql.py` | 29-31 | Query detection | Keep | Move to the raw capability |
| `clean_query` | `agent/handlers/sparql.py` | 20-26 | Fence removal | Keep | Move to `tools/sparql.py`; shared by the query guard and raw capability |
| `format_result` | `agent/handlers/sparql.py` | 34-45 | Row formatting | Keep | Move to the raw capability |

## 3. Reuse verdict

This section answers the critical reuse question.
It separates components that can carry one concern with high reliability from components that only look reusable.

### 3.1 Reuse unchanged

These components have one concern, a small interface, and a strong test or production record.

| Component | Concern | Evidence | Target use |
|---|---|---|---|
| `KnowledgeGraph` | Data access | pyoxigraph store, timeout, row cap, 174 tests | Backend of `run_sparql` |
| `SpeakeasyBot` | Transport | Dispatch, locks, reconnect, timeout tests | Unchanged |
| `build_store` | Store build | Build marker and fingerprint | Unchanged |
| `Settings` loader | Configuration | `.env` precedence tests | Extended, same pattern |
| `nlg` formatting | Value formatting | Unit tests, eval output | Result formatter and fallback |
| Raw SPARQL utilities | Query detection and formatting | Stage 1 eval 9/9 | Raw capability |

### 3.2 Reuse with adaptation

These components keep a valuable core but must change owner or interface.

| Component | Keep | Change | Risk |
|---|---|---|---|
| `Lexicon` | Label, property, and type indexes | Add a prefix index; remove fuzzy consumers | Low |
| `Trace` | `(step, detail)` contract | Add typed steps and metrics | Low |
| `Session` | Room identity | Add bounded sanitised history | Medium |
| `eval` | JSONL cases and expected/forbidden check | Add suites, modes, and metrics | Low |
| `cli` | Offline chat and debug output | Load two clients and show policy steps | Low |
| `__main__` | Startup and shutdown order | Add health check and mode selection | Medium |
| `SparqlHandler` | Detection, cleaning, formatting | Move behind `RawSparqlCapability` and `QueryGuard` | Low |

### 3.3 Reuse as data or prompt

These constructs are valuable knowledge, but they must not remain runtime decision logic.

| Source | What to keep | Where it goes | Why |
|---|---|---|---|
| `sparql_builder` templates | Correct predicate IDs, direction, count, superlative, and complement shapes | `qa/schema_card.py` and eval fixtures | Tested query shapes become few-shot examples |
| `guardrails` label definitions | Label names and descriptions | `agent/data/guardrails.json` | The schema becomes configurable |
| `guardrails` examples | Five worked cases | Classifier prompt fixtures | They cover mixed and toxic cases |
| `relations.json` | Everyday relation words | Prompt examples or test fixtures | The LLM can map words to property labels |
| Adversarial JSONL sets | Ten attack families | Regression suite | They test the new agent on the same inputs |
| `nlg` error texts | User-facing fallback wording | `agent/data/guardrails.json` and `qa/renderer.py` | Consistent failure messages |

### 3.4 Obsolete

These constructs have a concern that the LLM now owns, or a heuristic that the new contracts replace.

| Construct | Reason |
|---|---|
| `Preprocessor` | The LLM handles quote shapes, negation, claims, and mentions |
| `Parser` | Entity and relation decisions move to the LLM and tools |
| `FactualHandler` | Query construction moves to the LLM |
| `GuardedHandler` | The runtime and policy engine replace the ad hoc composition |
| `rephrase` | The QA LLM writes the answer; the validator keeps the grounding check |
| Old `Guardrails` prompt and parser | The forced tool call and schema validator replace them |
| `LLM` in-process loader | The OpenAI client and local servers replace it |
| `relations.json` runtime use | The schema card and property labels replace it |

The removal order matters.
Remove `GuardedHandler` before `FactualHandler`.
Remove `FactualHandler` before `Parser` and `Preprocessor`.
Remove `Parser` before `relations.json`.
Remove `LLM` after the new clients pass the guard and QA gates.
Each removal must keep the unit suite green.

## 4. New constructs

### 4.1 Guard package

| Construct | Responsibility | Interface |
|---|---|---|
| `GuardrailSchema` | Load scope values, safety types, descriptions, fallback texts, limits, and 8 pair examples | `load_schema(path)` |
| `GuardDiscriminator` | Decompose the message, detect ambiguity, and map semantic targets; force `submit_discrimination` | `discriminate(text) -> RawDiscrimination` |
| `GuardClassifier` | Label a fixed decomposition independently on safety and scope; force `submit_classification`; enforce exact label count with `minItems` and `maxItems` | `classify(text, discrimination) -> RawClassification` |
| `RawClassification` | Parsed overview and verbatims before validation | Frozen dataclass |
| `DiscriminationValidator` | Check exact spans, order, coverage, ambiguity flags, relationship targets, entities, and acyclic graph; retry once | `validate_discrimination(raw, text, schema) -> Discrimination` |
| `ClassificationValidator` | Check one label per span, index order, safety and scope values, rationale bounds; retry once | `validate_classification(raw, discrimination, schema) -> Verdict` |
| `Verdict` | Valid flag, overview, verbatims, per-span ambiguity and relationship, validation error | Frozen dataclass |
| `Verbatim` | Exact text, label, and two rationales | Frozen dataclass |
| `PolicyEngine` | Normalize prompt-injection scope, resolve the relationship graph, plan one effective label per verbatim, then aggregate | `decide(verdict) -> Decision` |
| `VerbatimPlan` | Index, effective label, rationale, handling, text or redaction, ambiguity, relationship | Frozen dataclass |
| `Decision` | Action, tools permission, verbatim plan, overview, safety types, fallback mode | Frozen dataclass |
| `FallbackText` | Select canonical text for a refusal, clarification, boundary, capability, or unavailable answer | `text_for(decision, part) -> str` |

### 4.2 QA package

| Construct | Responsibility | Interface |
|---|---|---|
| `ResponseAgent` | One part per verbatim, factual tool loop, part selection, budget, repair, join | `respond(verdict, decision) -> AgentResult` |
| `PromptBuilder` | Decision prompt, overview, verbatim plan, policy block, and schema card | `build(decision, verdict, history) -> messages` |
| `ResponsePart` | Enum for `factual_answer`, `general_answer`, `capability_limit`, `refusal`, `clarification`, `boundary` | Enum values |
| `SchemaCard` | Curated RDF schema and few-shot SPARQL examples | `render() -> str` |
| `AgentState` | Overview, decision, observations, evidence, errors, step count | Mutable dataclass |
| `AgentResult` | Ordered parts, joined text, evidence, fallback reason | Frozen dataclass |
| `AnswerValidator` | Part coverage, kind, safety type, evidence, value, length, and content checks | `validate(response, state) -> Validation` |
| `Validation` | Pass flag and the first failure reason | Frozen dataclass |
| `RowRenderer` | Deterministic row-to-text fallback | `render(result) -> str` |
| `Composer` | Fallback parts in verbatim order; distinct observations across answer parts | `compose(decision, state) -> AgentResult` |

### 4.3 Tool package

| Construct | Responsibility | Interface |
|---|---|---|
| `Tool` | Protocol for one environment action | `name`, `schema`, `run(args)` |
| `ToolResult` | Raw backend result before formatting | Frozen dataclass |
| `ToolObservation` | Formatted result, row IDs, truncation, error | Frozen dataclass |
| `ToolRegistry` | Name lookup, argument validation, timeout | `execute(call, state) -> ToolObservation` |
| `ResolveEntityTool` | Exact, prefix, contains label lookup | `run(query, limit)` |
| `RunSparqlTool` | Read-only query execution and formatting; the only graph fact source | `run(query)` |
| `QueryGuard` | Read-only query shape validation | `validate(query) -> Result` |
| `ResultFormatter` | Labels, row IDs, typed values, truncation | `format(result) -> Observation` |
| `RawSparqlCapability` | Stage 1 passthrough | `looks_like(text)`, `run(text)` |

### 4.4 LLM package

| Construct | Responsibility | Interface |
|---|---|---|
| `LLMClient` | OpenAI SDK wrapper, retries, timeouts, extra body, response format, normalisation | `chat(messages, tools, tool_choice, ...) -> LLMResponse` |
| `LLMResponse` | Content, tool calls, finish reason, usage | Frozen dataclass |
| `ToolCall` | ID, name, JSON arguments | Frozen dataclass |
| `load_clients` | Build guard and QA clients from settings | `load_clients(settings) -> Clients` |
| `Clients` | Guard and QA client pair | Frozen dataclass |
| `HealthCheck` | Probe each configured endpoint once at startup | `check(clients) -> Health` |
| `Health` | Per-endpoint status and latency | Frozen dataclass |
| `agent/serve.py` | Start the local model server | `start(settings)` |

### 4.5 Data files

| File | Content | Owner |
|---|---|---|
| `agent/data/guardrails.json` | Scope values, three parent safety types with descriptions and fallbacks, limits, 8 pair examples | Guard |
| `agent/data/movie_schema.json` | Core classes, properties, value shapes, examples | QA prompt |
| `config` environment keys | Shared local endpoint and model, role overrides, budgets, mode | Config |

## 5. File-by-file target map

```text
agent/
├── __main__.py                 adapt    startup, health, mode
├── config.py                   adapt    new keys, same loader
├── core.py                     rewrite  AgentRuntime, Trace, Session
├── normalize.py                new      trim, cap, quotes, course prefix
├── kg.py                       keep     store and query execution
├── lexicon.py                  adapt    dictionary and prefix index
├── nlg.py                      adapt    value formatting only
├── speakeasy_bot.py            keep     transport
├── build_store.py              keep     store build
├── serve.py                    new      vLLM or llama.cpp launcher
├── cli.py                      adapt    two clients, mode, debug
├── eval.py                     adapt    suites, modes, metrics
├── guard/
│   ├── schema.py               new      two-axis guard schema
│   ├── verdict.py              new      discrimination, verbatim, label, rationale, relationship validation
│   ├── discriminator.py        new      two-stage guard: discrimination prompt and tool
│   ├── classifier.py           new      two-stage guard: classification prompt and tool
│   ├── policy.py               new      relationship resolution, plan, aggregate action
│   └── fallback.py             new      canonical response text
├── qa/
│   ├── agent.py                new      per-verbatim response agent
│   ├── prompts.py              new      decision prompts
│   ├── schema_card.py          new      RDF schema card and examples
│   ├── state.py                new      state and observations
│   ├── actions.py              new      OpenAI tool schemas
│   ├── validator.py            new      part, grounding, and content checks
│   ├── composer.py             new      fallback composition only
│   └── renderer.py             new      deterministic fallback
├── tools/
│   ├── base.py                 new      Tool protocol and registry
│   ├── resolve.py              new      entity linking
│   ├── sparql.py               new      query guard, run, format
│   └── raw_sparql.py           new      Stage 1 capability
├── llm/
│   ├── client.py               new      OpenAI SDK wrapper
│   └── health.py               new      endpoint probe
└── data/
    ├── guardrails.json         new      scope and safety schema
    └── movie_schema.json       new      schema card data

removed after cutover:
agent/parser.py
agent/preprocess.py
agent/rephrase.py
agent/sparql_builder.py
agent/guardrails.py
agent/llm.py
agent/handlers/
agent/data/relations.json
```

The `handlers/` package disappears.
Its one useful capability, raw SPARQL, moves to `agent/tools/raw_sparql.py`.

## 6. Test impact

### 6.1 Tests that stay

| File | Reason |
|---|---|
| `tests/test_bot.py` | Transport behaviour is unchanged |
| `tests/test_kg.py` | Store and query behaviour is unchanged |
| `tests/test_config.py` | Loader behaviour stays; add new key tests |
| `tests/test_nlg.py` | Formatting helpers stay |
| `tests/conftest.py` | Graph fixtures stay; add fake client fixtures |
| `tests/fixtures/*.nt` | Graph fixtures stay |

### 6.2 Tests that are rewritten

| File | Current coverage | Target coverage |
|---|---|---|
| `tests/test_guardrails.py` | Scripted LLM verdicts | Guard schema, decomposition, typed overview and verbatim labels, validation, fail-safe clarification |
| `tests/test_factual.py` | Template answers | Response parts, per-verbatim plan, tool loop answers, evidence, fallback renderer |
| `tests/test_sparql_handler.py` | Raw SPARQL | Raw capability and query guard |
| `tests/test_core.py` | Handler routing | Runtime routing, aggregate action, `AGENT_MODE`; session and trace tests stay |

### 6.3 Tests that are removed

| File | Reason |
|---|---|
| `tests/test_parser.py` | Parser is obsolete |
| `tests/test_preprocess.py` | Preprocessor is obsolete |
| `tests/test_sparql_builder.py` | Runtime templates become prompt examples |
| Most of `tests/test_factual.py` | Template-specific cases move to eval data |

### 6.4 New tests

| Test area | Cases |
|---|---|
| Guard schema | Load, two scopes, three parent safety types, 8 pair examples, invalid schema, no allow label |
| Discrimination contract | Forced tool call, smallest complete spans, exact spans, coverage gap, separator words, ambiguity flag, resolved target, missing target, entity in target, target range, self-target, cycle, retry, clarification |
| Classification contract | Forced tool call, one label per span, index order, unknown type, multiple types, prompt-injection scope rule, rationale bounds, retry, clarification |
| Policy map | Per-verbatim effective label, parent-child inheritance, scope inheritance, prompt-injection scope, missing target, full 192-case matrix, aggregate action table, utility invariant, tool permission |
| Tool contracts | Entity exact, prefix, contains, missing, limit; `run_sparql` rows; no schema tool exists |
| Query guard | SELECT, ASK, updates, SERVICE, DESCRIBE, strings that contain banned words, length |
| Result formatter | IRI label resolution, dates, numbers, truncation, row IDs |
| Agent loop | Part kinds, one part per verbatim, mixed reply, factual tool calls, observation, submit, repair, step budget, deadline, repeated call, no graph call in a non-factual part |
| Answer validator | Part coverage, part kind, graph call in a non-factual part, cited row, missing row, invented number, invented label, URL, code fence, clarify shape, clarify quote length, redacted-text overlap |
| Refusal and clarify | Per-verbatim safety types, type coverage, no graph fact, length, crisis line, one question, fallback, no graph tools |
| Composer | Fallback only, ordered parts, distinct observations, answer plus boundary plus refusal, empty, length |
| Session seam | Sanitised recording, reset, history disabled |
| E2E | 47 projected guardrail cases after the three compatibility edits, per-verbatim plan cases, mixed-reply matrix, held-out factual set, adversarial sets |

## 7. Dependency impact

### 7.1 Agent runtime

| Dependency | Current | Target | Reason |
|---|---|---|---|
| `pyoxigraph` | yes | yes | Graph store |
| `speakeasypy` | yes | yes | Transport |
| `openai` | no | yes | Native tool constructs and local endpoints |
| `pydantic` | transitive | explicit | Tool argument validation |
| `rapidfuzz` | yes | no | Fuzzy recall moves to the LLM |
| `torch` | yes | no | Moves to the model server |
| `transformers` | yes | no | Moves to the model server |
| `accelerate` | yes | no | Moves to the model server |

### 7.2 Model serving

| Dependency | Purpose |
|---|---|
| `vllm` | OpenAI-compatible server, tool parser, batching |

`vllm` pins the `torch` and `transformers` versions it supports.
`requirements-serve.txt` lists only `vllm`; separate pins can resolve to a conflicting pair.
The serving environment does not need `accelerate` or `bitsandbytes`.

### 7.3 Legacy in-process model

`requirements-legacy.txt` keeps the old in-process model available.
It holds `torch`, `transformers`, `accelerate`, and `bitsandbytes`.
Only `AGENT_MODE=legacy` with `LLM_MODEL` set imports that stack.
The default `LLM_MODEL` is empty, so a base install starts the deterministic legacy path.
Do not install this file in the same environment as vLLM.

The agent dependencies live in `requirements.txt`.
The serving dependencies live in `requirements-serve.txt`.
The submission build copies both files.
It documents the serving setup next to the launcher.

### 7.4 Dependency risks

1. vLLM and torch versions must match on Nuvolos.
   Install vLLM without separate torch pins and let its metadata select the pair.
2. The chosen checkpoint may not have a quantized variant.
   The launcher serves the full-precision model.
   For 4-bit legacy loading, install `requirements-legacy.txt`.
3. llama.cpp may not support the exact tool-call format.
   The agent uses the OpenAI message shape; the server must parse it.
4. The OpenAI SDK must tolerate the local server's response shape.
   Contract tests cover the normalisation layer.

## 8. Impact metrics

| Metric | Current | Target | How to measure |
|---|---|---|---|
| Agent Python lines | 2,132 | about 2,400 to 2,700 | `wc -l agent/**/*.py` |
| Symbolic decision lines | 1,040 | 0 | `preprocess`, `parser`, `sparql_builder`, `factual`, `guarded`, `rephrase` |
| Guard files | 1 | 5 | `agent/guard/` |
| QA files | 1 handler | 8 | `agent/qa/` |
| Tool files | 1 handler | 4 | `agent/tools/` |
| LLM instances | 1 | 2 | Config and clients |
| Unit tests | 174 | at least 220 | `pytest -q` |
| Eval suites | 3 stage suites | 9 suites | `evals/` plus `evals/adversarial/policy_e2e.jsonl` |
| Runtime dependencies | 6 | 4 | `requirements.txt` |
| Internet calls | 0 | 0 | Audit |

The line estimates are planning targets.
The cutover records the real counts.

## 9. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The 4B model writes wrong SPARQL | High | Wrong but grounded answers | Held-out eval, repair loop, row citation, fallback renderer |
| The guard model misses unsafe input | Medium | Safety failure | Per-type recall gate, verbatim coverage, per-verbatim plan, red-team set |
| The discriminator merges or drops a clause | Medium | Safety failure | Exact-span coverage, gap retry, clarify on failure, adversarial decomposition cases |
| The response agent complies with an injection | Medium | Safety failure | Graph tools only for a factual answer part, validator fact checks, redacted unsafe text, tool-query overlap check, fallback texts |
| The discriminator or classifier returns invalid output | Medium | Safe but unhelpful reply | One retry per stage, then a clarification with no graph tools and no facts |
| A mixed reply answers or quotes an unsafe verbatim | Medium | Safety failure | Redacted unsafe text, one refusal part per unsafe verbatim, per-part validator, tool-query overlap check |
| A mixed reply suppresses a safe verbatim | Medium | Utility loss | Utility invariant, per-verbatim plan, mixed-reply matrix gate |
| A wrong relationship target propagates the wrong safety type | Medium | Safety or utility failure | Entity-in-target validation, acyclic graph, fail-closed map, 192-case matrix, relationship tracing |
| A wrong pronoun target hides a missing antecedent | Medium | Safety failure | Gender-mismatch policy, entity-in-target check, acyclic graph, relationship probes |
| A procedural self-harm realism question passes as analysis | Medium | Safety failure | Explicit realism-versus-instruction policy, step-request case, harmful examples |
| A guard miss on an unsafe request reaches clarify with raw text | Low | Safety failure | 100 percent safety recall gate, verbatim coverage, red-team set, clarify prompt and validator cap any quote at six words |
| The QA model repeats tools and exhausts its budget | Medium | Utility loss | Repeat-call guard, forced final submit, distinct-observation fallback |
| No schema tool blocks predicate discovery | Medium | Wrong query or retry | Schema card, one predicate-discovery SPARQL example, repair loop |
| The shared model and KV cache do not fit on the T4 | Medium | Deployment failure | Memory fraction, 4096 context, quantization if needed, llama.cpp fallback, serving spike |
| Tool calls are unreliable on the local server | Medium | Loop failure | Forced guard tools, JSON schema, one repair, fallback |
| The agent is too slow for 25 seconds | High | Timeout replies | Step budget, token caps, 4-bit, vLLM, latency gate, timeout tuning |
| The new factual path is worse than legacy | High | Regression | Legacy flag, held-out set, per-type scoreboard, no cutover until gate |
| The eval set leaks into prompt tuning | Medium | False confidence | Split dev and test, freeze test, report per-type recall |
| The graph contains adversarial labels | Low | Prompt injection via tool output | Treat tool output as data, escape, validator, no tool instructions |
| Nuvolos installation fails | Medium | Deployment failure | Pin serving stack, document llama.cpp fallback, smoke test |
| Raw SPARQL bypasses safety | Low | Scope or safety leak | Read-only store, query guard, documented trust boundary |
| The session seam leaks unsafe text | Low | Safety failure | Store only safe in-scope verbatims, history disabled |

## 10. Cutover checklist

1. Freeze the legacy baseline logs.
2. Confirm the per-verbatim plan matrix and the aggregate action matrix.
3. Confirm the 47-case canonical labels and the three compatibility edits.
4. Confirm that invalid classification yields a clarification, not a refusal.
5. Confirm that a mixed reply answers every safe answerable verbatim and refuses every unsafe verbatim.
   The safe part must still be answered.
   Unsafe text must not enter a tool query.
6. Confirm that only `resolve_entity` and `run_sparql` are exposed as graph tools.
7. Confirm the held-out factual comparison.
8. Confirm zero unsupported values.
9. Confirm the latency gate.
10. Confirm the adversarial scoreboard.
11. Remove `GuardedHandler`.
12. Remove `FactualHandler`.
13. Remove `Parser` and `Preprocessor`.
14. Remove `sparql_builder` runtime use.
15. Remove `rephrase`.
16. Remove the old guard prompt.
17. Remove the in-process LLM loader.
18. Remove `rapidfuzz` and the serving stack from the agent requirements.
19. Update `README.md` and `phases.md`.
20. Rebuild every submission folder.
21. Run the Nuvolos smoke test.
22. Record the real line and test counts.
23. Archive the legacy eval logs.
