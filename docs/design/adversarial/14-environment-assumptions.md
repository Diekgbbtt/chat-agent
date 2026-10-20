# Environment, technology, and interaction assumptions

State: 2026-10-21.
Scope: the Speakeasy-hosted chatbot, the Nuvolos evaluation machine, the local development machine, the graph store, and the submission artifact.
Purpose: state every assumption behind a successful run, show which assumptions are proven, and separate the confirmed failure causes from the unproven machine-stack hypothesis.
The report does not claim a single root cause for the other-system crash.
No traceback, Speakeasy log, or environment fingerprint from that machine was available.

## Formal model

Let `E` be an execution environment.
The tuple `E = (os, arch, python, packages, fs, net, limits)` records the operating system, CPU architecture, Python version, installed packages, filesystem, network, and resource limits.

Let `A` be the submission artifact.
Let `G` be the graph file.
Let `S` be the store directory.
Let `B` be the Speakeasy service.
Let `U` be the user.

The main predicates are defined below.

```
exists(p)          p is a readable path
is_file(p)         p is a regular file
is_dir(p)          p is a directory
is_link(p)         p is a symbolic link
writable(p)        the current user may create and remove entries in p
same_fs(p, q)      p and q are on one filesystem
python_ok(E)       Python major/minor is at least 3.11
deps_ok(A, E)      every requirement of A is installed in E
graph_ok(G)        G is a regular, readable N-Triples file
runtime_fp(E)      (python minor, pyoxigraph version, OS, machine, store format)
graph_fp(G)        (size, SHA-256)
store_ok(S, G, E)  marker(S) is valid for graph_fp(G) and runtime_fp(E)
artifact_same(A1, A2)  the agent files in A1 and A2 have equal content hashes
reply_ok(msg)      msg is posted before the reply deadline and is within the transport limit
```

`store_ok` is the formal version of the marker check.

```
store_ok(S, G, E) :=
    exists(S / ".build-complete")
    and marker_version(S) = 1
    and marker.graph.sha256 = graph_fp(G).sha256
    and marker.graph.size = graph_fp(G).size
    and marker.runtime = runtime_fp(E)
    and can_open_read_only(S, E)
```

The safe-run condition is a conjunction.

```
safe(E, A, G, S, B, U) :=
    python_ok(E)
    and deps_ok(A, E)
    and graph_ok(G)
    and store_ok(S, G, E)
    and artifact_same(A, A_expected)
    and reply_ok(B, U)
```

An assumption is a predicate that must hold for `safe` to hold.
The agent may fail, hang, or answer incorrectly when an assumption is false.

## Assumption inventory

| ID | Assumption | Formal condition | Status |
|---|---|---|---|
| E1 | The machine is a supported POSIX-like system. | `os(E) in {Linux, Darwin}` | Local macOS validated; remote Linux assumed. |
| E2 | The CPU architecture matches the installed binaries. | `arch(E)` matches `pyoxigraph` wheel and store | Local arm64 validated; remote x86_64 unverified. |
| E3 | Python is 3.11 or newer. | `python_ok(E)` | Local 3.13.8 validated; remote base Python unverified. |
| E4 | The base Python has the required packages. | `deps_ok(A, E)` | Local validated; remote install unverified. |
| E5 | The graph file is readable. | `graph_ok(G)` | Local validated; remote Nuvolos mount unverified. |
| E6 | The store parent is writable, or a writable temporary fallback exists. | `writable(parent(S)) or writable(tempdir(E))` | Local validated; fallback now covers a read-only submission directory. |
| E7 | The store can be read after the first build. | `can_open_read_only(S, E)` | Local validated; remote unverified. |
| E8 | The machine has enough disk space for graph, store, and partial store. | `free_disk(E) > size(G) + 2 * size(S)` | Local 17.5 GB free; remote unverified. |
| E9 | The process has enough memory for the graph and lexicon. | `available_memory(E) > 315 MB + headroom` | Local observed about 315 MB RSS; remote limit unverified. |
| E10 | The process can create symlinks and rename directories. | `supports_symlink(fs(E)) and supports_rename(fs(E))` | Local validated; remote POSIX assumed. |
| E11 | The working directory and package layout are stable. | `cwd(E) is defined and A/additional_files/agent exists` | Local validated; launcher inserts `additional_files`. |
| T1 | The store format matches the pyoxigraph version. | `marker.runtime.pyoxigraph = pyoxigraph_version(E)` | New marker check; local validated. |
| T2 | The store was built from the current graph content. | `marker.graph.sha256 = graph_fp(G).sha256` | New marker check; local validated. |
| T3 | The store is portable across directory moves. | `store_ok(S, G, E)` does not depend on `marker.graph.path` | New test; local validated. |
| T4 | The OS and architecture match the store. | `marker.runtime.platform = os(E)` and `marker.runtime.machine = arch(E)` | New marker check; local validated. |
| T5 | The Python minor version matches the store runtime. | `marker.runtime.python = python_minor(E)` | New marker check; local validated. |
| T6 | Queries are bounded in rows and time. | `rows <= 10_000 and query_time <= 20 s` | Local validated; remote clock and load unverified. |
| T7 | List answers are bounded before serialization. | `values <= 50 and reply_chars <= 4_000` | Local validated; old artifact violated this. |
| T8 | The lexicon load completes within its caps. | `labels <= 10_000_000 and load_time <= 300 s` | Local validated; remote cold cache unverified. |
| I1 | Speakeasy launches `main.py` with base Python. | `argv(E) = /opt/conda/bin/python main.py` | Documented by the course; remote unverified. |
| I2 | Credentials reach the process. | `BOT_USERNAME and BOT_PASSWORD are set` | Local configuration validated; remote secret unverified. |
| I3 | The process can reach the Speakeasy host. | `dns(E, host) and tls(E, host) and http(E, host)` | Local network path not exercised; remote unverified. |
| I4 | The callback returns before the SSE loop stalls. | `on_message` enqueues and returns | Code validated by unit tests. |
| I5 | A reply is posted within the timeout. | `reply_time <= 25 s and reply_chars <= 4_000` | Local validated; remote load unverified. |
| I6 | The Speakeasy client version matches the service. | `speakeasypy == git commit 4419d9c...` | Local import validated; remote service unverified. |
| I7 | Room order is preserved. | one lock per `room_id` | Code validated by unit tests. |
| I8 | Logs are writable. | `writable(log_dir(E))` | Local validated; remote unverified. |
| A1 | The remote artifact equals the current source artifact. | `artifact_same(A_remote, A_local)` | Stale artifact was confirmed before the rebuild. |
| A2 | The artifact contains the current parser and preprocessor. | `preprocess.py and parser.py` are present and current | Rebuilt on this branch. |
| A3 | The artifact does not contain local absolute paths. | no required absolute path except the documented Nuvolos fallback | Code inspected. |
| A4 | The artifact does not ship a dataset or store. | `A` contains code and requirements only | Submission inspected. |

Status meanings:

- `validated` means a local command or test proves the condition on this machine.
- `unverified` means the condition is plausible but has no evidence from the other machine.
- `confirmed broken` means the condition failed in an earlier artifact or code path.
- `new check` means the condition is now enforced by the store marker.

## Environment in plain prose

The bot assumes a POSIX-like machine with a writable working area.
The online course environment uses `/opt/conda/bin/python` as the base interpreter.
The code also works on macOS during development.
The graph file is read from `GRAPH_PATH`.
If `GRAPH_PATH` is unset, the code looks for `dataset/graph.nt` under the package root.
If that local file is absent, the code falls back to `/space_mounts/atai-hs26/dataset/graph.nt`.
The submission does not include the dataset.
The submission does not include a prebuilt store.
The first run therefore builds a store in `kg_store/`, unless `KG_STORE_PATH` points elsewhere.

The build writes to `<store>.partial` first.
It then renames the partial directory into place.
This requires free space for the old store and the new partial store at the same time.
The graph is about 289 MiB.
The completed store is about 298 MiB.
The local free space at audit time was 17.5 GB.
The remote free space is unknown.

The process loads graph labels into memory.
The observed resident set size was about 315 MB.
The lexicon load has a 300 second cap and a 10 million row cap.
A slow or memory-limited machine can fail before the bot listens for messages.

The filesystem must support symbolic links and directory renames.
A `kg_store` symbolic link can point to a shared store.
A dangling link previously caused a `NotADirectoryError` at the final rename.
The new build path resolves links, including dangling links, before it builds.
A read-only submission directory previously caused a `PermissionError` on `<store>.partial`.
The open path now retries at a per-store temporary directory and logs a warning.
The fallback is used only for permission-class errors.
If the fallback is also unwritable, the error propagates.

The marker is layout independent.
The marker records the graph size and SHA-256.
The marker records the Python minor version, pyoxigraph version, OS, machine, and store format.
The marker also records the graph path, but validation does not require that path.
A store can therefore move to another directory when the graph content and runtime match.
The local hash check cost about 0.15 seconds for the 303 MB graph.
The hash is computed on every store open.
The cost is small compared with the lexicon load.

## Technology in plain prose

The knowledge graph is a pyoxigraph store.
The current version is `pyoxigraph==0.5.11`.
The store is a binary RocksDB directory.
The code does not assume that a store built on one OS, architecture, or pyoxigraph version opens on another.
The marker now rejects a store when any of those runtime fields differ.
A rejected store is rebuilt from the graph.
The code prefers a rebuild over an unsafe reuse.

Entity matching uses `rapidfuzz==3.14.6`.
That release requires Python 3.11 or newer.
A Python 3.10 base environment can fail at install time or import time.
The 3.10 failure is one plausible machine-stack drift cause.

The Speakeasy client is a git dependency at commit `4419d9c6563633b864eecee05db4b84c93f30a60`.
The `requests` package is transitive and unpinned.
An incompatible client or HTTP stack can fail during login or event delivery.
The local environment uses `speakeasypy 1.0.0` and `requests 2.34.2`.
The remote versions are unverified.

SPARQL queries use a 20 second timeout.
A query that times out keeps running in a background thread.
The default row cap is 10,000.
Complement queries now use `LIMIT 1000`.
Factual list answers now serialize at most 50 values.
The bot has a 4,000 character fallback cut.
The fallback is a final guard, not the primary bound.

The old complement reply was 201,036 characters for Steven Spielberg.
The old reply materialized up to 10,000 rows and joined them into one string.
The new reply is 1,147 characters and 50 values.
The local median answer time is about 0.05 seconds.
The old path could exceed the 25 second Speakeasy reply budget on a slower machine.
This is a confirmed code-level timeout cause.
It does not prove that the other machine timed out for this reason, but it is the strongest supported cause.

## Interaction in plain prose

Speakeasy delivers messages through a server-sent event stream.
The client calls the registered callback from that stream loop.
The callback logs the message and submits work to a dispatch pool.
The callback must return quickly.
A slow callback would stall every room on the stream.

The dispatch pool holds one lock per room.
Messages in one room stay ordered.
Messages in different rooms run in parallel.
A compute pool runs the answer function.
If the answer exceeds `REPLY_TIMEOUT_S`, which defaults to 25 seconds, the user receives a timeout reply.
If the answer raises an exception, the user receives an error reply.
A failed post is retried once after one second.
A failed stream connection is retried with exponential backoff.

The bot assumes that `room.post_messages(reply)` accepts a normal text reply.
It assumes that the reply is shorter than the transport limit.
It assumes that the service keeps the session alive while the client reconnects.
It assumes that the credentials are valid for the whole evaluation window.
It assumes that the remote clock and network allow TLS and HTTP requests to `speakeasy.ifi.uzh.ch`.

The bot reads configuration from environment variables.
It also reads `.env` files from the current directory, the project root, and the submission folder.
This fallback exists because the online launcher does not inherit the developer shell profile.
A missing `.env` or missing exported variables causes a clean exit with status 2.
That exit is visible in the launch log but not to chat users.

## Crash analysis

The other-system failure has no captured traceback.
The failure is therefore underdetermined.
The evidence supports a multi-cause model, not a single proven root cause.

### Confirmed causes

1. The previous submission artifact was stale.
   The current preprocessor and parser fixes were not in the deployed artifact.
   This was confirmed by the submission audit.
   The artifact has been rebuilt on this branch.

2. The old complement path was unbounded at the query layer.
   It fetched up to 10,000 rows and produced a 201,036 character reply.
   The reply exceeded the 4,000 character cap only after the full string existed.
   A slow machine could exceed the 25 second reply timeout.
   The new path fetches at most 1,000 rows and serializes 50 values.

3. Lowercase names and uppercase `NOT` were not resolved.
   The old preprocessor and parser returned `no_entity` for those forms.
   The edge-negation trimming and case handling now resolve them.

4. The surname form `Spielberg` was resolved by a bad fuzzy window.
   The parser tested `extractOne("spielberg")` and got no match.
   It then tested the window `"did spielberg"` and matched `"david spielberg"` at 0.867.
   The graph returned the David Spielberg entity `Q1866328`.
   That entity has no directing credit in the graph, so the handler fell back to the wrong direction.
   The top-50 bound hid `E.T.` but still allowed `The BFG`, which Steven Spielberg directed.
   The test now forbids `The BFG` and resolves the surname to Steven Spielberg `Q8877`.
   The fix has two parts.
   Fuzzy windows may not start or end with question or negation words.
   A capitalized single-word surname is ranked among human labels by graph degree.

5. The old store marker contained only an absolute graph path.
   It did not record graph content, pyoxigraph version, OS, architecture, or Python version.
   A stale or foreign store could be accepted as valid.
   The marker now records all of those fields.
   A mismatched store is rebuilt.

6. A dangling `kg_store` symlink could crash the final rename.
   The build removed the old path with `shutil.rmtree`.
   `shutil.rmtree` does not remove a dangling symlink.
   The rename then failed with `NotADirectoryError`.
   The build path now resolves the symlink target before validation and build.
   A regression test covers the dangling-link case.

7. A read-only submission directory could crash the store build.
   The build needs to create `<store>.partial` and rename it.
   A read-only parent raised `PermissionError` or a wrapped `OSError`.
   `KnowledgeGraph.open` now retries at a per-store temporary directory and logs a warning.
   A regression test covers the read-only parent case.

8. Two bot processes were connected to one live Speakeasy room.
   The room showed two replies to a single question under one bot alias.
   One process ran the old behavior.
   The other process ran the current behavior.
   The Alien question is the clearest case.
   The first reply was `Ridley Scott`.
   The second reply was the 50-value complement that excludes Ridley Scott.
   The Spielberg filmography question also split.
   One reply was the correct list.
   The other reply was `Sorry, my knowledge graph has no information about the director of David Spielberg.`
   The negated Spielberg question split in the same way.
   One reply was the positive filmography with `The BFG`.
   The other reply was the bounded complement that starts with `Lost in Translation`.
   This duplicate deployment is a confirmed cause of the observed wrong live answer.
   A rebuilt artifact alone does not stop the old process.
   The operator must stop every old process before evaluation.

9. The live pre-patch process treated a contraction inside an unknown title as negation.
   The live answer to `who directed don't look up?` was a complement list that included `Ridley Scott`.
   The local cause was a fuzzy match from `look up` to the film `Lock Up`.
   The quoted form `'Don't Look Up'` had a second cause.
   The apostrophe in `Don't` paired with the closing quote.
   That pairing made the parser see the human `Don`.
   The current fix rejects the fuzzy match and treats a known fragment inside a quoted title as subvention.
   `Don't Look Up` is absent from the graph, so the correct grounded behavior is a clarification.
   The fix does not invent Adam McKay, and it does not answer for `Don`, `Lock Up`, or `Up`.

### Live check, 2026-10-21

A signed-in Speakeasy room was observed after the operator reported the Ridley Scott answer.
The room had one human alias and two bot responders under the alias `affectionate_nash_42`.

| Question | Live replies | Reading |
|---|---|---|
| `Who did not direct 'Alien'?` | `Ridley Scott`, then the 50-value complement | Stale process plus current process. |
| `Which movies did Spielberg direct?` | Correct filmography and a `David Spielberg` no-facts reply | Stale process resolves the wrong person. |
| `Which movies did Steven Spielberg not direct?` | Positive filmography and a bounded complement | Stale process ignores negation. |
| `Who directed Jaws?` | `Steven Spielberg` twice | Both processes answer this case correctly. |
| `Did Ridley Scott direct Jaws?` | `No` | The claim path works in the current process. |
| `Who directed 'Never Let Me Go'?` | `Mark Romanek` twice | Both processes answer this case correctly. |
| `who directed don't look up?` | A complement list that included `Ridley Scott` | Pre-patch process; the local fix now clarifies. |

The live latency for the bounded complement was about 0.3 seconds.
This is below the 25 second timeout, but it does not prove the remote load or the other machine's disk speed.

The live room proves that a second bot process is active.
It does not prove which filesystem or Python stack that process uses.
It also does not prove that the old process is the only remaining risk.
The filesystem and machine-stack drift concern therefore remains open.

### Unproven hypotheses

The filesystem and machine-stack drift hypothesis is plausible.
It is not proven.
The following conditions could produce a crash on the other machine and not locally.

- The remote `kg_store` is a dangling symlink.
- The remote submission directory is read-only.
- The remote `GRAPH_PATH` is absent or unreadable.
- The remote process runs Python 3.10 or older.
- The remote pyoxigraph version differs from 0.5.11.
- The remote OS or architecture differs from the machine that built the store.
- The remote store was copied from another machine and has a stale marker.
- The remote environment lacks the git dependency or has an incompatible `requests`.
- The remote service rejects login, the event stream, or the post request.
- The remote machine is slower, has less memory, or has a cold disk cache.

The report cannot rank these causes without the remote traceback and environment fingerprint.

### Fault tree

```
remote failure
├─ artifact drift [confirmed before rebuild]
│  ├─ stale agent copy
│  ├─ missing current preprocessor and parser
│  └─ old unbounded complement path
├─ duplicate deployment [confirmed live]
│  ├─ old bot process still connected
│  ├─ both processes share one bot alias
│  └─ old process returns positive or wrong-person answers
├─ filesystem and store drift [mechanism confirmed; remote occurrence unknown]
│  ├─ dangling kg_store symlink -> NotADirectoryError at rename
│  ├─ read-only parent -> temporary fallback or PermissionError
│  ├─ stale marker -> foreign store accepted before this fix
│  └─ moved store -> absolute-path marker mismatch before this fix
├─ machine-stack drift [unproven]
│  ├─ Python < 3.11 -> rapidfuzz install or import failure
│  ├─ pyoxigraph/OS/architecture mismatch -> store open failure
│  ├─ missing git dependency -> import failure
│  └─ incompatible requests -> login or post failure
├─ interaction drift [partly confirmed]
│  ├─ 201k reply and 10k rows -> 25 s timeout
│  ├─ slow callback -> SSE loop stall
│  └─ network, TLS, or post failure
└─ data drift [unproven]
   ├─ graph missing at the Nuvolos mount
   └─ graph changed without a store rebuild
```

### Critical evaluation

The duplicate live process is the confirmed cause of the reported wrong answer.
Artifact drift was the confirmed cause before the rebuild.
The two causes interact because the duplicate process is probably an old artifact.
The unbounded reply is a confirmed code-level cause of latency.
The surname bug is a confirmed code-level cause of wrong answers.
The store marker and dangling-link bugs are confirmed code-level failure modes.
The other-system occurrence of those failure modes is not confirmed.

The filesystem and stack drift hypothesis remains useful.
It explains why the same source can pass locally and fail remotely.
It also predicts which tests will discriminate between causes.
It does not identify the actual remote cause.

The new store validation reduces silent misuse.
It cannot make a missing graph appear.
It cannot make Python 3.10 satisfy a 3.11 dependency.
It cannot guarantee that a copied store opens on a different OS or architecture.
The read-only fallback writes the store under the system temporary directory.
That fallback needs free space and a writable temporary directory.
It also rebuilds on a cold machine, so it does not avoid the first-build delay.

The marker check has a cost.
The local SHA-256 check takes about 0.15 seconds on a warm cache.
A cold or networked filesystem can take longer.
That cost is accepted because a wrong store is worse than a short startup delay.

The marker check has a limit.
It compares content hashes and runtime fields.
It does not prove that the store's internal pages are sound.
A corrupted store with a valid marker can still fail on open.
The code does not add a full store integrity scan.

The answer bound has a tradeoff.
The complement query keeps the first 1,000 candidates in store order.
A famous film outside that pool cannot appear, even if its graph degree is high.
Graph degree is a popularity proxy, not a semantic relevance score.
The answer is deterministic and local, but the candidate pool is not the full film universe.

The surname ranking has a tradeoff.
It selects the human with the most graph triples among labels that end with the surname.
For `Spielberg`, that is Steven Spielberg.
For a less famous person with the same surname, degree may not match the user's intent.
The alternative was a fuzzy window that joined `"did"` to the surname and chose David Spielberg.
The ranked surname rule is more predictable than that fuzzy match.

The report cannot prove the absence of a remote failure.
It only shows that the local code now satisfies the tested assumptions.
A remote run with the rebuilt artifact and a captured fingerprint is still required.

## Discriminating tests

Run these tests on the other machine before changing code.
Record the output with the timestamp and the full environment fingerprint.

### 1. Artifact identity

```bash
cd "<submission folder>"
/opt/conda/bin/python - <<'PY'
from pathlib import Path
import hashlib
for name in ("preprocess.py", "parser.py", "kg.py", "nlg.py"):
    p = Path("additional_files/agent") / name
    print(name, p.exists(), hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "-")
PY
```

If `preprocess.py` is missing, the artifact is stale.
If a hash differs from the local build, the artifact drifted.

### 2. Runtime fingerprint

```bash
/opt/conda/bin/python - <<'PY'
import importlib.metadata as md
import platform, sys
print("python", sys.version)
print("platform", platform.platform())
print("machine", platform.machine())
for pkg in ("pyoxigraph", "rapidfuzz", "speakeasypy", "requests"):
    try:
        print(pkg, md.version(pkg))
    except Exception as exc:
        print(pkg, "MISSING", exc)
PY
```

If Python is below 3.11, the stack is outside the supported range.
If pyoxigraph is not 0.5.11, the store marker will reject the old store.
If `speakeasypy` is missing, the bot cannot start.

### 3. Graph and store fingerprint

```bash
cd "<submission folder>"
PYTHONPATH=additional_files /opt/conda/bin/python - <<'PY'
import json
from pathlib import Path
from agent.config import load_settings
from agent.kg import BUILD_MARKER, store_is_built
s = load_settings()
print("graph", s.graph_path, Path(s.graph_path).exists())
print("store", s.store_path, Path(s.store_path).is_symlink())
print("valid", store_is_built(s.store_path, s.graph_path))
marker = Path(s.store_path).resolve() / BUILD_MARKER
print(marker.read_text() if marker.exists() else "NO MARKER")
PY
```

If `valid` is false, the next start rebuilds the store.
If the graph path is missing, the bot cannot build.

### 4. Forced rebuild in a temporary store

```bash
cd "<submission folder>"
TMP_STORE=/tmp/agent-store-check
rm -rf "$TMP_STORE" "$TMP_STORE.partial"
KG_STORE_PATH="$TMP_STORE" PYTHONPATH=additional_files /opt/conda/bin/python -m agent.cli "Who directed Jaws?"
```

If this succeeds, the graph, the runtime, and the store builder are sound.
If it fails, the traceback identifies the failing layer.

### 5. Exact bounded answer

```bash
cd "<submission folder>"
PYTHONPATH=additional_files /opt/conda/bin/python -m agent.cli --debug "what films did Spielberg not direct"
```

The debug output must show `entity='Q8877'` and `direction='in'`.
The answer must be about 1.1 KB and must not contain `The BFG` or `E.T. the Extra-Terrestrial`.
A larger answer means the old artifact or the old bounding path is still deployed.

### 6. Speakeasy end-to-end

Send the same question through the real Speakeasy room.
Record the time from send to post and the server log for the room.
A successful post rules out login, network, and post-path failures for that request.
A timeout with a short local CLI answer points to the remote runtime or service, not the answer logic.

### 7. Log and traceback capture

```bash
cd "<submission folder>"
ls -la additional_files/logs
tail -n 200 additional_files/logs/*.log
```

The log should show startup, the store decision, login, message receipt, answer time, and post result.
A missing startup log points to an import or launch failure before the bot listens.

### 8. Fault isolation matrix

| Observation | Supported cause | Next test |
|---|---|---|
| Artifact hash differs | artifact drift | Rebuild and redeploy. |
| Python < 3.11 | stack drift | Install the pinned requirements in base Python. |
| `valid` false with readable graph | store drift | Force a rebuild on the target machine. |
| `valid` false with missing graph | data drift | Fix `GRAPH_PATH` or mount the dataset. |
| Permission error on `.partial` | filesystem drift | Use a writable `KG_STORE_PATH`. |
| Short CLI answer but long Speakeasy answer | stale artifact or service path | Recheck artifact hash and room logs. |
| CLI answer slow | query or store load | Profile the query and disk. |
| Login failure | credentials or network | Check `BOT_USERNAME`, `BOT_PASSWORD`, DNS, and TLS. |

## Recommendations

Stop every old bot process and every old Speakeasy session before deployment.
Confirm that one question produces one reply.
Deploy the rebuilt submission artifact.
Run the fingerprint and forced-rebuild tests on the target machine before the evaluation window.
Use `/opt/conda/bin/python` for every check.
Set `KG_STORE_PATH` to a writable directory when the submission directory may be read-only.
Keep `GRAPH_PATH` explicit when the Nuvolos mount is not guaranteed.
Do not copy a store across OS, architecture, or pyoxigraph versions.
Rebuild on the target instead.
Keep the 1,000-row complement limit and the 50-value serializer.
Keep the 4,000 character fallback as a guard.
Do not treat `Don't Look Up` as a supported title.
The graph does not contain it, so the safe answer is a clarification.
Capture the startup fingerprint and the first failing traceback if a remote failure recurs.

## Evidence appendix

Local code and test evidence at this revision.

- `pytest`: 159 passed.
- Stage 1: 9/9.
- Stage 2 factual: 508/508.
- Stage 2 factual negation: 9/9.
- Ten adversarial types: 664/664.
- Dataset check: 10 files checked, datasets OK.
- Steven Spielberg complement: 1,147 characters, 50 values, median 0.05 seconds.
- Christopher Nolan complement: 1,140 characters, 50 values.
- Inception complement: 919 characters, 50 values.
- Local graph: 303,306,568 bytes, SHA-256 `11073431030bde60d971f0e5b2c1f9c1e7f7ca2a91519bfe1bb7229cdc6b5c6a`.
- Local store: pyoxigraph 0.5.11, Python 3.13, Darwin arm64, marker version 1.
- Local store hash check: about 0.15 seconds.
- Live Speakeasy: two bot responders under one alias.
- Live Alien answer: stale `Ridley Scott` plus current 50-value complement.
- Live bounded complement latency: about 0.3 seconds.
- Local unquoted, single-quoted, and double-quoted `Don't Look Up`: clarification, no `Don`, `Lock Up`, or `Up` answer.

The local environment is not the remote environment.
The local results prove the code paths under the local assumptions.
They do not prove the remote filesystem, machine stack, network, or service state.
