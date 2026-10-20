# Answer bounding for negated lookups

State: post-S10 extension, 2026-10-20.
Supersedes the unbounded complement decision in Q1 of `03-known-types-spec.md`.
The runtime behavior is in `agent/sparql_builder.py`, `agent/handlers/factual.py`, and `agent/nlg.py`.

## Problem

A negated lookup such as "what films did Steven Spielberg not direct" returns the film complement.
The film universe has 12,245 entities, and the old code fetched up to `Settings.max_fetch_rows` = 10,000 rows.
It then serialized every row into one `and`-joined string.
The exact Spielberg reply was 201,036 characters.
The Nolan reply was 201,115 characters.
The previous `MAX_REPLY_CHARS` cut happened after the full reply existed.
That cut reduced the posted text, but it did not reduce query time, row memory, or string-building cost.
Speakeasy requests still timed out on slower machines.

## Decision

Bound the answer at two independent layers.

1. Query layer: `sb.COMPLEMENT_FETCH_LIMIT` = 1,000.
   The complement query ends with `LIMIT 1000`.
   This caps rows, memory, and the number of labels that enter Python.
2. Serialization layer: `nlg.ANSWER_LIMIT` = 50.
   `nlg.answer()` slices every list to 50 values.
   The bot's 4,000-character cap remains as a final safety net, but it should not be reached by a normal answer.

The complement handler ranks its bounded candidates by graph degree before serialization.
Graph degree is the existing project relevance rule in `Parser._rank`: films first, then the entity with the most triples.
The handler obtains all candidate degrees in one `VALUES` query.
It then sorts by descending degree, breaks ties by case-folded label, removes duplicate labels, and keeps 50.

## Runtime flow

1. `Preprocessor.analyze` marks the lookup as negated and resolves the entity.
2. `FactualHandler.handle` calls `sb.complement(...)`, whose query returns at most 1,000 rows.
3. `FactualHandler._rank_complement` collects candidate QIDs and labels.
4. `FactualHandler._degrees` issues one SPARQL query with a `VALUES` list of those QIDs.
5. `_rank_complement` sorts by degree and keeps `nlg.ANSWER_LIMIT` labels.
6. `nlg.answer` slices to 50 again and joins the values.
7. `SpeakeasyBot` applies the 4,000-character cap only if an abnormal reply still exceeds it.

## Relevance definition

The relevance score is the count of triples with the entity as subject.
This is the same score that `Parser._rank` already uses to choose between ambiguous entities.
It is a popularity proxy, not a semantic relevance model.
The project has no click data, embedding model, or popularity field, and the request forbids a runtime LLM.
Degree is deterministic, local, and cheap to compute for a bounded candidate set.

## Measurements

Measured on the local store with the final code.

| Query | Candidates | Serialized | Reply chars | Median | Max |
|---|---:|---:|---:|---:|---:|
| what films did Steven Spielberg not direct | 1,000 | 50 | 1,147 | 0.048 s | 0.060 s |
| Which films did Christopher Nolan not direct? | 1,000 | 50 | 1,140 | 0.047 s | 0.049 s |
| Who did not direct 'Inception'? | 1,000 | 50 | 919 | 0.034 s | 0.043 s |

Before the change, the Spielberg reply was 201,036 characters.
The new reply is about 175 times smaller.

## Test evidence

- `tests/test_sparql_builder.py`: the complement query ends with `LIMIT 1000`.
- `tests/test_nlg.py`: `nlg.answer` keeps exactly 50 values.
- `tests/test_factual.py`: a 61-film graph returns 50 values, the high-degree film is first, and the lowest-degree film is absent.
- `tests/test_factual.py`: a surname-only negation uses the famous director, not the wrong entity.
- `tests/test_preprocess.py`: lowercase names and uppercase `NOT` no longer block entity resolution.
- `tests/test_parser.py`: `Spielberg` resolves to `Q8877`, and a fuzzy window cannot join `did` to the surname.
- `evals/stage2_factual_negation.jsonl`: 9/9, with `The BFG` forbidden for every Spielberg case.
- `evals/stage2_factual.jsonl`: 508/508.
- `evals/stage1_sparql.jsonl`: 9/9.
- All ten adversarial types: 664/664.
- `pytest`: 154 passed.

## Dataset consequence

The runtime answer is now a ranked subset, not the full complement.
T1 expected values must therefore come from that subset.
`scripts/adversarial/build_datasets.py` mirrors the runtime ranking in `ranked_complement_labels`.
It fetches the same 1,000-candidate pool, computes the same degree scores, and picks expected values from the serialized 50.
It also removes any forbidden value that appears anywhere in the serialized answer.
`evals/adversarial/t1-negation.jsonl` was regenerated; all 121 cases pass.
`evals/stage1_sparql.jsonl` and `evals/stage2_factual.jsonl` were not edited.

## Tradeoffs and accepted risks

- The candidate pool is 1,000 rows, not the full 12,245-film universe.
  A famous film outside the first 1,000 rows cannot appear, even if its degree is high.
- The raw candidate order is store order.
  The implementation does not add an expensive global `GROUP BY` degree query to the first query.
- Degree is a proxy for relevance.
  A well-connected but obscure film can outrank a famous film with fewer graph triples.
- The 1,000-row query is a policy constant, not a per-request setting.
  Changing it changes answer composition and requires T1 regeneration.
- The 50-value serializer applies to every factual list answer, not only complements.
  Positive lookups are already limited to 200 rows, so the cut only affects unusually large lists.

## Rejected alternatives

- Keep the 4,000-character downstream cut only.
  It does not reduce query rows, memory, or string construction.
- Return the full complement and let the bot truncate.
  This caused the timeout risk the operator reported.
- Sort alphabetically and take 50.
  This returns mostly numeric and punctuation titles and is not useful relevance.
- Compute global degree for every film in a single `GROUP BY` query.
  Local probes measured about 0.34 seconds, but it scans the whole graph and loses the cheap query-level bound.
- Use a runtime LLM or embedding score.
  The project forbids runtime LLMs and new dependencies.

## Follow-up

The environment, technology, and interaction assumptions are recorded in `14-environment-assumptions.md`.
The store marker now checks the graph SHA-256, pyoxigraph version, Python minor version, OS, and machine.
The store build resolves dangling symlinks and falls back to a temporary store when the submission directory is read-only.
The stale submission artifact was rebuilt from the current `agent/` package.
The bounded reply shape is in the rebuilt submission artifact.
