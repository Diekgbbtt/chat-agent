# S7 - cluster index

State: S7.
Clusters come from the iteration-0 baseline.
Baseline logs and reports: `docs/design/adversarial/eval/iter0/`.
Red repro evidence: `docs/design/adversarial/eval/s7-repros.log`, captured by `scripts/adversarial/capture_repros.py`.
Diagnosis reports: `docs/design/adversarial/diagnosis/<cluster-id>.md`, one per cluster.
A cluster is one dataset type.
The failure shapes inside a type share the code seam that the fix will touch.
Ten clusters, ten diagnosis reports (G7 checks this count).

## Cluster table

| Cluster | Dataset | Baseline | Failures | Observed reply shapes | Decision anchors |
|---|---|---|---|---|---|
| c-t1-negation | `t1-negation.jsonl` | 8/64 | 56 | film-side complement answered with the positive filmography (38: 28 P57 + 10 P58); person-side complement answered with the film's actual director (18: 16 film cases + 2 combined) | Q1, Q8, Q9 |
| c-t2-subvention | `t2-subvention.jsonl` | 24/60 | 36 | crafted longer non-title resolved to the short title inside it and answered (24 replies hit the trap list); 12 replies return another value absent from the trap list | Q2, Q12 |
| c-t3-quote-shapes | `t3-quote-shapes.jsonl` | 37/57 | 20 | `no_entity` 12 (doubled quotes 6, unclosed or inner punctuation 6); `no_facts` 5; wrong link 2; wrong title 1 | Q12, Q10, Q15 |
| c-t4-typos | `t4-typos.jsonl` | 39/60 | 21 | `no_entity` 16; wrong link 2; wrong title 2; `no_facts` 1 | Q7, Q10, Q11 |
| c-t5-partial-titles | `t5-partial-titles.jsonl` | 20/51 | 31 | `no_entity` 16; `no_facts` 6; wrong title 6; wrong link 2; answered instead of clarifying 1 | Q15, Q10, Q2 |
| c-d1-counts | `d1-count-class.jsonl` | 6/63 | 57 | every non-P57 count replies "The factual answer is: 0"; the 6 P57 film-count controls pass | D1 rule, Q9 |
| c-d2-multi-mention | `d2-multiple-mentions.jsonl` | 10/65 | 55 | answers one of the two mentions (55); 10 unquoted two-sentence forms already return the clarification reply | Q16 |
| c-d3-trailing | `d3-trailing-superlative.jsonl` | 18/55 | 37 | `no_facts` for every title with trailing context; 18 pass (14 neutral contexts + 4 title controls) | D3 rule |
| c-d5-yes-no | `d5-yes-no.jsonl` | 0/62 | 62 | 51 name answers (film-to-director parse); 11 filmography answers (person-to-films parse); no Yes/No reply anywhere | Q13 |
| c-d8-paraphrases | `d8-relation-paraphrases.jsonl` | 10/70 | 60 | `no_relation` for all 60 paraphrase forms; the 10 existing-phrasing controls pass | Q14 |

## Red repro map

The repro log holds the section header `## <cluster-id>` for each cluster.
Representative cases per cluster:

- c-t1-negation: `t1-negation-001` (film side), `t1-negation-029` (writer side), `t1-negation-039` (person side), `t1-negation-057` (masking control, green).
- c-t2-subvention: `t2-subvention-001..003` (crafted longer non-titles).
- c-t3-quote-shapes: `t3-quote-shapes-001` (doubled), `-024` (inner period), `-054` (inner question mark), `-010` (wrong link).
- c-t4-typos: `t4-typos-003`, `-031` (no_entity), `-002` (wrong link), `-033` (wrong title).
- c-t5-partial-titles: `t5-partial-titles-001` (no_entity), `-006` (no_facts), `-035` (wrong title), `-007` (wrong link), `-045` (clarify).
- c-d1-counts: `d1-count-class-001`, `-002`, `-036` (awards, cast, countries).
- c-d2-multi-mention: `d2-multiple-mentions-001`, `-002`.
- c-d3-trailing: `d3-trailing-superlative-001`, `-002` (red), `-005` (green control).
- c-d5-yes-no: `d5-yes-no-001`, `-002` (true claims), `-003` (false claim).
- c-d8-paraphrases: `d8-relation-paraphrases-001..003` (nominalisation, helm, camera), `-061` (control).

## Per-cluster notes from the iteration-0 reports

### c-t1-negation
The masking controls pass.
The word "not" disappears between recognition and relation detection (see B3 in `02-architecture-contracts.md`).
The complement universe decision is Q9.
The film-side expected labels were harvested with the complement query shape the fix must reuse (10,000-row cap, see `05-dataset-manifest.md`).
Q8 requires masking of the entity mention before any negation detection.

### c-t2-subvention
The crafted mentions embed a real short title ("tarzan", "deep", "up").
The current linker trims the mention to the embedded title and answers it.
The wrong answer is confident: no safe failure fires.
Q2 fixes the contract: a mention that carries extra words around a title is not the title.
Q12 fixes quote normalisation as a neighbour concern.

### c-t3-quote-shapes
Doubled quotes and inner punctuation break the quoted-span pass and the fuzzy pass.
The 5 `no_facts` cases reach the relation phase with a lower-case fragment ("matrix", "pianist").
The 2 wrong-link cases and the 1 wrong-title case are linking failures, not quote failures.

### c-t4-typos
16 typos fall below every linking pass.
2 typos link to a wrong but confident node (`godfahter` -> Q5576354 "Lal and Siddique").
2 typos link to a wrong title in a matching family (`batman begns` -> the 1989 Batman).
Q7, Q10, Q11 fix the matching rules.

### c-t5-partial-titles
44 partial cases need resolution by prominence (Q15).
The passes are 6 full-title controls and 14 partials that happen to resolve.
The clarify case (`t5-partial-titles-045`, "twilight zone") has no film candidate in this KG.
The wrong-title cases resolve to same-shaped titles of other films ("usual suspects" -> Q1971726).

### c-d1-counts
Every non-P57 count replies "The factual answer is: 0".
The P57 control path is correct and must stay (film subjects, `wdt:P31 wd:Q11424` filter).
The D1 dataset fixes raw counts for the other relations.

### c-d2-multi-mention
One question holds two film mentions.
The handler answers the first or the second one.
Q16 fixes the contract: two mentions produce the clarification reply.
10 unquoted forms already pass because recognition fails safely.

### c-d3-trailing
Trailing context after a quoted title enters the entity span or the relation text.
The neutral contexts pass, so the seam is the trailing attachment itself, not the title.
The 4 title controls (`The Last Emperor`, `First Blood`) pass and must stay.

### c-d5-yes-no
Every claim is converted into a list question.
51 replies return the film's director name; 11 return the claimed person's filmography.
No reply uses the Yes/No shape.
Q13 fixes the reply shape: "The factual answer is: Yes" / "No".

### c-d8-paraphrases
All 60 paraphrase forms fall through relation detection into `no_relation`.
The 10 controls pass and must stay.
Q14 fixes the mapping: nominalisations and idioms rewrite to the canonical relation words.

## Report contract (G7)

Each `diagnosis/<cluster-id>.md` report contains these sections:

1. `## Red repro` - the exact command and the observed output, cited from `s7-repros.log` or from a recorded probe.
2. `## Failure shapes` - sub-shapes with counts that sum to the cluster failure count.
3. `## Ranked hypotheses` - each hypothesis with its test (probe or code reading) and a verdict.
4. `## Root cause` - one primary root cause, pinned to a phase and a boundary (B1-B7) from `02-architecture-contracts.md`, with code symbol and file:line.
5. `## Decision constraints` - the operator decisions that constrain the fix.
6. `## Suggested fix` - the concrete change direction, preferring the `agent/preprocess.py` seam (Q3).
7. `## Regression seam` - the exact cases and commands that will prove the fix, plus the golden cases at risk.
8. `## Risks and open questions`.

## Verification

Report count equals cluster count:

    ls docs/design/adversarial/diagnosis/*.md | wc -l   # -> 10
