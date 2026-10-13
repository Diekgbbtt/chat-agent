# Project Phases

Roadmap for the ATAI 2026 conversational agent. Deadlines are 08:00 Zurich time on the given day.

| Phase | Stage | Evaluation | Deadline | Grade |
|---|---|---|---|---|
| 0 | Foundation | – | 16.10.26 (internal) | – |
| 1 | Stage 2: Factual QA | online | 21.10.26 | 20% |
| 2 | Stage 3: LLM + guardrails | in-person | 11.11.26 | 20% |
| 3 | Stage 4: Recommendations | in-person | 25.11.26 | 30% |
| 4 | Stage 5: RAG + routing (final) | in-person | 09.12.26 or 16.12.26 | 30% |

## Constraints

- **No externally hosted LLMs.** Every model must run locally or on Nuvolos.
- **Nuvolos hardware:** Tesla T4 (16 GB VRAM, fp16 only, no bf16 or FlashAttention-2) and 28 GB RAM.
- **Online evaluation** runs `Project Submission N/main.py` with `/opt/conda/bin/python` (Python 3.13), so all dependencies must be installed there.
- **In-person evaluation:** the bot must serve several chatrooms concurrently and must never crash.
- **Speakeasy web UI:** messages containing `@` never reach the bot, and pasted multi-line text isn't sent. Test by hand with one-line inputs.
- **Report:** every library used must be declared.

## Dataset facts

- `graph.nt`: 2.4M triples, about 12k films (`wdt:P31 wd:Q11424`), and about 130k entity labels.
- **Entity labels** are plain strings (`rdfs:label "The Godfather"`) with no `@en`.
- **Property labels** are `@en` (`"director"@en`). 497 of the 502 predicates have one.
- **Labels are ambiguous.** For example, four entities are labelled "The Godfather". Entity linking must disambiguate them: prefer films, then the entity with more triples.
- **Other files:** `plots.csv`, `user_ratings.csv`, `item_ratings.csv` and `user_comments.csv` (used in Stage 4).

---

## Architecture

### Files

| File | Role | Used by the bot? |
|---|---|---|
| `agent/__main__.py` | Entry point for `python -m agent` and every submission's `main.py`. Wires everything together. | yes |
| `agent/config.py` | Reads `.env` files and environment variables into a `Settings` object (credentials, paths, workers, timeouts). Real environment variables win over `.env`. | yes |
| `agent/kg.py` | Knowledge graph. Opens `kg_store/` read-only (building it from `graph.nt` first if missing) and runs SPARQL with default prefixes, a timeout and a row cap. | yes |
| `agent/core.py` | `Agent`: one `Session` per chat room, input normalization, routing to the first handler whose `can_handle()` says yes. `answer(text, session_id)` is the single entry point. | yes |
| `agent/handlers/sparql.py` | Stage 1: recognizes raw SPARQL (also inside `'''` or ``` fences), runs it, and formats the rows. | yes |
| `agent/handlers/factual.py` | Stage 2: parses the question, runs the SPARQL template, answers "The factual answer is: …" (or "no entity / no relation / no facts"). | yes |
| `agent/lexicon.py` | Built once at startup (~6 s), as in tutorial 04a: `ent2lbl`, `lbl2ent` (lower-cased), property labels, instance-of types. | yes |
| `agent/parser.py` | Question → entity, predicate, direction, kind. Entity: quoted title, else longest label match (capitalised spans first), else fuzzy match. Predicate: property labels + `data/relations.json`. Same-named entities: films first, then most facts; the first combination with facts in the graph wins. | yes |
| `agent/data/relations.json` | Everyday words for properties ("directed" → P57, "starred" → P161, …). The only hand-written vocabulary. | yes |
| `agent/sparql_builder.py` | SPARQL templates: lookup, count, earliest/latest film by release date, fact checks. | yes |
| `agent/nlg.py` | Value formatting, "A, B, and C" joining, and the answer / error templates. | yes |
| `agent/speakeasy_bot.py` | Speakeasy connection: concurrency (thread pools, per-room locks), reply timeouts, fallback replies, post retries, reconnects, heartbeat. | yes |
| `agent/build_store.py` | One-time conversion of `graph.nt` into `kg_store/`. Optional, because `kg.py` builds the store on first start anyway. | no (tool) |
| `agent/cli.py` | Asks the agent questions without Speakeasy (single question, `--debug` trace, or interactive chat). | no (tool) |
| `agent/eval.py` | Runs the regression cases in `evals/*.jsonl` and reports accuracy and latency. | no (tool) |
| `scripts/build_submission.py` | Fills `Project Submission N/` with a launcher `main.py`, a copy of `agent/` and `requirements.txt`. | no (tool) |
| `tests/` | Unit tests against the tiny `tests/fixtures/mini.nt` graph (`python -m pytest -q`). | no |

`kg_store/` is the on-disk graph database the bot reads from in production too, not just in tests. It's git-ignored and must exist (or be built on first start) wherever the bot runs.

### Startup (`python -m agent`, runs once)

`__main__.py` → `main()` runs these steps in order:

1. **`config.load_settings()`** reads `.env` files and environment variables into `Settings`.
2. **`setup_logging()`** logs to the console and to `logs/<date>.N.log`. If the credentials are missing, it exits here.
3. **`KnowledgeGraph.open()`** (`kg.py`) opens `kg_store/` read-only, in about 0.01 s, and starts the query thread pool. If the store is missing, it builds it first (about 10 s).
4. **`build_agent(kg)`** (`core.py`) builds the lexicon (~6 s) and creates the `Agent` with the handlers `[SparqlHandler, FactualHandler]`.
5. **`SpeakeasyBot(agent.answer, …)`** (`speakeasy_bot.py`) creates the dispatch pool (4 × workers) and the compute pool (workers threads).
6. **`bot.run()`** starts the heartbeat thread, then loops: log in → register `on_message` → `start_listening()`. This blocks while connected. If the connection fails, it waits 1 s, 2 s, 4 s … (up to 60 s) and reconnects.

### What later stages change

Only the inner layer grows: new handlers in `agent/handlers/` (factual QA, guardrails, recommendations, RAG), registered in `Agent`'s handler list, and smarter routing in `core.py` than "first handler that says yes". `__main__.py`, `config.py`, `speakeasy_bot.py` and `kg.py` stay essentially unchanged.

---

## Phase 0: Foundation (now → 16.10)

Groundwork shared by every later stage.

- [x] **Package layout.** Move the logic into `agent/`:
  - `kg.py` (graph store and queries)
  - `speakeasy_bot.py` (concurrency, reconnects)
  - `core.py` (sessions and routing to handlers)
  - `handlers/` (one per capability)
  - `nlg.py` (answer formatting)
  - `cli.py`, `eval.py`, `build_store.py` (tools)
- [x] **Thin launchers.** Each `Project Submission N/main.py` only starts the bot. A build script copies `agent/` into that folder's `additional_files/`.
- [x] **Faster graph backend.** Switch to pyoxigraph (SPARQL-compliant, fast load and query, low RAM) (the rdflib fallback was removed on 13.10 to keep the code small).
- [x] **Concurrency.** Handle each message in a worker pool, so one slow room doesn't block the others.
- [x] **Robustness.** Put a timeout on every handler, catch and log all errors, reconnect after a crash, and make sure no input can kill the bot.
- [x] **Offline harness.** `python -m agent.cli "question"` answers a question without Speakeasy, and a regression file of evaluation questions reports accuracy.
- [x] **Stage 1 passthrough.** Raw SPARQL keeps working, including multi-line queries with `PREFIX` lines.
- [x] **`requirements.txt`** with pinned versions.
- [x] **Verify on the full graph.** `kg_store/` is built: 2,413,825 triples, built in 11 s, opens in 0.01 s. `python -m agent.eval` passes 9/9 Stage 1 cases (slowest 0.36 s).
- [ ] **Live Speakeasy test** of the new bot (`python -m agent`).
- [ ] **Verify on Nuvolos:** install `requirements.txt` into `/opt/conda/bin/python`, add a `.env`, and run `python scripts/build_submission.py 2`.

## Phase 1: Stage 2 Factual QA (due 21.10, aim for 19.10)

Turn single-hop natural-language questions into SPARQL and answer them from the graph (the tutorial 04a approach: label lookups + SPARQL).

- [x] **Entity linking** (`lexicon.py`, `parser.py`): quoted title, else longest label match (capitalised spans before lower-case ones), else fuzzy match (rapidfuzz) for typos. Same-named entities: films first, then the best-known one.
- [x] **Relation linking**: the graph's property labels plus `data/relations.json`, longest phrase first.
- [x] **Direction**: whichever direction has facts; if both, a film entity means the answer is the object.
- [x] **Kinds**: lookup, count ("how many"), earliest/latest film ("first", "latest", …).
- [x] **Answer**: "The factual answer is: A, B, and C" (sorted), first release date only, unlabelled entities left out.
- [x] **Simplified** (13.10): negation, yes/no, follow-ups, descriptions, "is X a Y", exclusions and the other conversation features were removed; they belong to Stage 3, where the LLM handles them better.
- [x] **Evaluation set** (`evals/stage2_factual.jsonl`, 48 cases, expected answers from hand-written SPARQL) + 9 Stage 1 cases: 57/57 pass.
- [x] **Unusual titles**: titles of common words (*Her*, *Being There*, *Or*), with punctuation (*Them!*, *Who Am I?*), lower-case one-word titles as a last resort; "a movie" = typed film or has a director (covers animated films).
- [x] **Partial titles**: if a match is only part of a longer capitalised title ("Don't Look Up" → "Up"), the bot says "not sure" instead of answering for the fragment.
- [x] **Unit tests**: 74 pass (`tests/`, fixtures `tests/fixtures/*.nt`).
- [x] **Python 3.13** (Nuvolos version): tests, eval and the built launcher all pass on 3.13.16.
- [ ] **Deploy and test** on Nuvolos with `/opt/conda/bin/python`.
- [ ] **Report** (≤ 2 pages, LaTeX template) and **4-slide presentation**, by 20.10. Libraries to declare: pyoxigraph, rapidfuzz, speakeasypy.

### Dataset notes found while building Stage 2

- Some well-known entities are missing on purpose (e.g. "Spirited Away", "Quentin Tarantino"); the only film labelled "Titanic" is the 1953 one.
- Many release dates are year-only, stored as `YYYY-01-01`.
- Birth and death dates (P569/P570), runtime and budget are not in the graph.
- Some entities have no label; answers leave them out.
- Some names are misspelled in the graph (e.g. "Steven Sodorborgh", "Gury Traesdela"); answers repeat the graph's spelling.
- Every entity has a short `schema:description`, used for "Who is X?" questions.

## Phase 2: Stage 3 LLM + Guardrails (11.11)

- [ ] **LLM.** An open-weight 7–8B instruct model, 4-bit quantized (AWQ/GPTQ, about 5–6 GB), on the T4 via vLLM or `transformers`. A 3–4B model in fp16 is the fallback.
- [ ] **Local testing.** The LLM interface can be swapped for a stub or a small CPU model, so the code can be tested without a GPU.
- [ ] **Guardrail classifier.** Llama Guard or a fine-tuned small classifier (tutorial 05 recipe), with labels `safe_in_scope` / `out_of_scope` / `toxic` / `unsafe` / `prompt_injection`.
- [ ] **Mixed requests.** Answer the safe part and refuse the unsafe part.
- [ ] **Facts stay from the graph.** The LLM only phrases answers, which raises the humanness rating, and acts as a fallback parser when the rules fail.
- [ ] **Short replies,** because generation on a T4 is slow.
- [ ] **Conversation features removed from Stage 2** (rebuild on the LLM): negation, yes/no questions ("Did X direct Y?"), follow-ups ("and who wrote it?"), "Who is X?" descriptions, "is X a Y", exclusions ("other than X").
- [ ] **Labelled test set** for each guardrail category.
- [ ] **Report and slides.**

## Phase 3: Stage 4 Recommendations (25.11)

- [ ] **Conversation memory per chatroom.** Track liked films, genre, mood, era and actors.
- [ ] **Clarification questions** until there are enough preferences to recommend from.
- [ ] **Hybrid recommender:**
  - content-based on graph features (director, genre, cast, costume designer, composer, award nominations);
  - item-item KNN over `user_ratings.csv` (tutorial 07);
  - plot embeddings from `plots.csv` to match mood;
  - `item_ratings.csv` as a quality prior.
- [ ] **Explanations** with each recommendation ("they share costume designer X").
- [ ] **Report and slides.**

## Phase 4: Stage 5 RAG + Routing (09.12 or 16.12)

- [ ] **Get the AI-ethics document collection** (AI Act, Magnifica Humanitas).
- [ ] **Chunking** by article or paragraph, keeping citation metadata.
- [ ] **Hybrid retrieval** (BM25 + dense embeddings), then reranking.
- [ ] **Grounded generation.** The LLM answers only from the retrieved text and cites it, e.g. "(Regulation, Article 6(3))".
- [ ] **Router.** Classifies each message as FACTUAL / REC / GUARDRAILS / RAG / SPARQL, trained on a labelled set built from all the evaluation examples.
- [ ] **Full regression run** across all stages.

## Throughout

- Grow the regression set with every stage, so earlier capabilities don't break.
- Draft the report section for each feature while it's still fresh.
- Keep `requirements.txt` and the Nuvolos base environment in sync.

## Open items

- [ ] Find where the pre-trained embeddings and the AI-ethics documents are on Nuvolos, or confirm they haven't been released yet.
