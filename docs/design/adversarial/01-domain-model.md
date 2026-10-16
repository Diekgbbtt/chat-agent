# S1 - Domain model (grounded)

State: S1.
Worktree: `fix/adversarial-normalization`.
Every value below comes from the probe log `docs/design/adversarial/eval/s1-domain-probe.log`, produced by the commands in section 6.

## 1. Relation union (30 predicates)

Union of three sources:

| Source | Content | Size |
|---|---|---|
| A: `agent/data/relations.json` | hand-written synonym groups | 26 predicates |
| B: parsing all 508 inputs of `evals/stage2_factual.jsonl` with `Parser.parse` | predicates the golden path actually resolves | 27 distinct predicates, 506 parsed, 2 `no_entity` |
| C: templates in `agent/sparql_builder.py` | `wdt:P577` constant (`RELEASE_DATE`), `wdt:P31 wd:Q11424` type constraint in `count()` | 1 relation plus 1 class |

Union size: 30 predicates.
B-only predicates: `wdt:P106` (occupation), `wdt:P144` (based on), `wdt:P2142` (box office), `wdt:P2515` (costume designer).
A-only predicates: `wdt:P155` (prequel/follows), `wdt:P69` (educated at), `wdt:P840` (set in).

## 2. Per-relation facts (label, triple count, 2 grounded examples)

Examples are real triples from the KG, rendered as subject -> object with `rdfs:label` values where available.

| # | IRI (short) | Property label | Triples | Grounded example 1 | Grounded example 2 |
|---|---|---|---|---|---|
| 1 | ddis:tag | (no `@en` label) | 27,422 | He Died with a Felafel in His Hand -> absurd | The Naked Gun: From the Files of Police Squad! -> absurd |
| 2 | wdt:P19 | place of birth | 59,056 | Andurs Hava -> Greenland | Paco Ortega -> Úbeda |
| 3 | wdt:P26 | spouse | 9,210 | Sara MacDonald -> Noel Gallagher | Berthold Viertel -> Elisabeth Neumann-Viertel |
| 4 | wdt:P27 | country of citizenship | 86,522 | Fiona Glascott -> Ireland | Alan Glynn -> Ireland |
| 5 | wdt:P57 | director | 15,187 | Inception -> Christopher Nolan | Tukuma -> Palle Kjærulff-Schmidt |
| 6 | wdt:P58 | screenwriter | 19,964 | The Chronicles of Narnia -> Christopher Markus | Captain America: Civil War -> Christopher Markus |
| 7 | wdt:P69 | educated at | 40,549 | Stephen J. Dubner -> Contact | Mojtaba Javadi -> Tehran |
| 8 | wdt:P86 | composer | 13,317 | The Jackal -> Noel Gallagher | Savage Streets -> John D'Andrea |
| 9 | wdt:P106 | occupation | 251,858 | Anthony Quinn -> painter | Frida Kahlo -> painter |
| 10 | wdt:P136 | genre | 54,097 | Maverick -> Westerns on television | Django -> Westerns on television |
| 11 | wdt:P144 | based on | 5,194 | The BFG film poster -> The BFG | The BFG teaser poster -> The BFG |
| 12 | wdt:P155 | follows | 2,259 | The Way We Was -> One Fish, Two Fish, Blowfish, Blue Fish | Loaded Guns 2 -> Loaded Guns |
| 13 | wdt:P156 | followed by | 2,251 | interwar period -> World War II | World War I -> World War II |
| 14 | wdt:P161 | cast member | 167,536 | Captain America: The Winter Soldier -> Christopher Markus | Mr. Nobody -> Peter Gorissen |
| 15 | wdt:P162 | producer | 17,281 | Fly Me to the Moon -> Caroline Van Iseghem | Phantoms -> Dean Koontz |
| 16 | wdt:P166 | award received | 69,870 | Ovosodo -> David di Donatello for Best Sound | Fulgenzio Ceccon -> David di Donatello for Best Sound |
| 17 | wdt:P272 | production company | 12,911 | Mother of Mine -> Film i Skåne | Io capitano -> Tarantula Belgium |
| 18 | wdt:P344 | director of photography | 11,134 | The Killing -> Marcel Zyskind | The Road to Guantanamo -> Marcel Zyskind |
| 19 | wdt:P345 | IMDb ID | 95,907 | Chen Zhen -> ch0010348 | Billy Lo -> ch0024421 |
| 20 | wdt:P364 | original language of film or TV show | 15,530 | The Mummy -> Egyptian | Nairobi Half Life -> Gikuyu |
| 21 | wdt:P495 | country of origin | 21,995 | December Bride -> Ireland | The King's Choice -> Ireland |
| 22 | wdt:P577 | publication date | 19,543 | Inception -> 2010-07-08 | The Blue Bird Vol. 2 -> 1920-03-05T00:00:00 |
| 23 | wdt:P750 | distributed by | 20,147 | Ghost Story -> Confederazione italiana agricoltori | High Heels -> Filmauro |
| 24 | wdt:P840 | narrative location | 13,040 | Qivitoq -> Greenland | Zero Kelvin -> Greenland |
| 25 | wdt:P915 | filming location | 9,733 | Alatriste -> Úbeda | Kolya -> Sterneggovský palác |
| 26 | wdt:P1040 | film editor | 9,315 | Kameradschaft -> Jean Oser | Mushishi -> Sōichi Ueno |
| 27 | wdt:P1411 | nominated for | 36,391 | The Pussycat Dolls -> (Q1527196, unlabelled) | Post Malone -> (Q1527196, unlabelled) |
| 28 | wdt:P1657 | MPA film rating | 2,328 | Cactus Flower -> M | Psycho -> M |
| 29 | wdt:P2142 | box office | 3,347 | The Best of Me 2 -> 0.0137681365 | Doctor Zhivago Part 2 -> 0.024367101 |
| 30 | wdt:P2515 | costume designer | 2,401 | Undine -> Katharina Ost | The Caiman -> Linna Nerli Taviani |

Noise note, grounded in the log: the KG relations are not domain-restricted.
Example: `wdt:P136` also links persons ("Stanisław Lem -> Q188867" in the log section 2).
The templates therefore rely on the entity-linking step to pick the right subject class.

Date-format note, grounded in the log: `wdt:P577` literals appear both as plain dates ("2010-07-08") and with a time part ("1920-03-05T00:00:00").
`nlg.format_term` (`agent/nlg.py` line 23) strips only the suffix `T00:00:00Z`.

## 3. Entity types used by the pipeline

| Type | QID | Grounded count | Example QID | Example label |
|---|---|---|---|---|
| Film | wd:Q11424 | 12,245 (`SELECT (COUNT(DISTINCT ?f) ...)`) | Q25188 | Inception |
| Human | wd:Q5 | 85,854 | Q25191 | Christopher Nolan |
| "has a director" heuristic (`Lexicon.directed`) | not a type | 13,746 (`SELECT COUNT(DISTINCT ?m) WHERE ?m wdt:P57 ?d`) | Q25188 | Inception |

`Lexicon.is_film` = `Q11424 in types` OR entity in `directed` (`agent/lexicon.py` lines 43-44).
`Lexicon.is_human` = `Q5 in types` (line 47).
Total labels in the index: about 130k (`phases.md`, "Dataset facts").

## 4. Label ambiguity (grounded, feeds T2 and T5)

From probe section 7:

- `the godfather` -> 4 QIDs: `Q47703` (film), `Q3225260`, `Q1139696`, `Q243556`.
- `inception` -> 3 QIDs: `Q54888270`, `Q3797611`, `Q25188` - the actual Nolan film is LAST in insertion order; only `_rank` (films first) picks it.
- `the matrix` -> 3 QIDs: `Q33140061`, `Q13014087`, `Q83495`.
- `up` -> 2 QIDs: `Q174811`, `Q3825402`.

## 5. Direction conventions (grounded)

`sparql_builder` docstring: direction "out" = the entity is the subject, the answer is the object; direction "in" = the entity is the object, the answer is the subject.
`Parser.parse` (`agent/parser.py` lines 84-91) picks the first (predicate, entity) combination with facts in either direction; when both directions have facts, a film entity forces "out".

Live probe (log section 4):

```text
Who directed 'Inception'?  entity=Q25188 direction=out
    SPARQL: SELECT DISTINCT ?x ?label WHERE { <http://www.wikidata.org/entity/Q25188> <http://www.wikidata.org/prop/direct/P57> ?x . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200
    rows: ['Christopher Nolan']

Which films did Christopher Nolan direct?  entity=Q25191 direction=in
    SPARQL: SELECT DISTINCT ?x ?label WHERE { ?x <http://www.wikidata.org/prop/direct/P57> <http://www.wikidata.org/entity/Q25191> . OPTIONAL { ?x rdfs:label ?label } } LIMIT 200
    rows: ['Oppenheimer', 'Inception', 'Batman Begins', 'The Dark Knight trilogy', 'The Prestige', 'The Dark Knight Rises'] ...
```

Observed direction and kind usage from parsing the 508 golden inputs (log section 10), highlights:

- `wdt:P57`: out/lookup 41, in/lookup 19, in/count 13, in/earliest 12, in/latest 11.
- `wdt:P161`: out 25, in 19. `wdt:P58`: out 26, in 13. `wdt:P26`: in 12, out 1.
- All other predicates: out/lookup only.
- Kinds used: `lookup`, `count` (13 cases), `earliest` (12), `latest` (11).

## 6. Probe commands (reproduce)

```bash
cd /Users/diekgbbtt/.local/share/opencode/worktree/c6b606/fix/adversarial-normalization
/Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/probe_domain_model.py \
  2>&1 | tee docs/design/adversarial/eval/s1-domain-probe.log
```

Two follow-up heredoc probes (sections 6-8 and 9-11 of the log) ran the same way and appended with `tee -a`; their source is recorded in the log header comments of this document's sibling, `PLAN.md` gate log entry.

The mission's example probe verified too: `lex.label("Q25188")` = `'Inception'` (log section 3).

## 7. Coverage table

| Metric | Value |
|---|---|
| Relations in union | 30 |
| Relations with >= 2 grounded examples in this document | 30 |
| Code-relevant entity types | 2 (`wd:Q11424`, `wd:Q5`) plus 1 heuristic set (`directed`) |
| Films | 12,245 |
| Humans | 85,854 |
| Entities with a director | 13,746 |
| Golden inputs parsing to `no_entity` | 2: `greeting` ("hello"), `unknown-title` ("Who directed 'Qwzxv Plorbnik Unfilmable'?") - both already expect the `no_entity()` reply |

## 8. Implications for later states

1. T1 complement universe candidates: 12,245 films for "which films did X not direct"; 13,746 directed entities or 85,854 humans for "who did not direct Y" (exact choice is an S3 decision with grounded counts).
2. T2/T5 grounding: `the matrix` (3 candidates) and `up` (2 candidates) are the canonical ambiguous cases; `The Handmaiden` (Q20444585) is unique.
3. The 2 `no_entity` golden cases prove safe-failure replies are already part of the contract; adversarial safe-failure cases must reuse the same template text.
4. Date literals with `T00:00:00` exist; discovered-type work (S4) should probe date-shape noise per the checklist.
