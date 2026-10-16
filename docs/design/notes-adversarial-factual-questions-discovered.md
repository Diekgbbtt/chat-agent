# S4 - Discovered adversarial types (D1-D8)

State: S4. Scope: the seven phase contracts B1-B7 in `02-architecture-contracts.md`; T1-T5 are excluded.
Evidence: three probe rounds of many questions per process, modelled on `scripts/adversarial/s3_probe.py`; the probe scripts sit outside the repo, so each red line quotes the question, the observed reply and the entity QID for rerun with `agent.cli`.

## D1 - "How many" counts only film-class objects

- Contract under attack: B4 (phase 3 -> 4: "the predicate and direction fill the template correctly") plus B5 (phase 4 -> 5: "the rows have the expected type and shape"). The count template assumes the answer object is a film.
- Why it breaks: `sb.count` always appends `?x wdt:P31 wd:Q11424`, so only objects that are themselves films reach the count. Any other object class gives the count 0. The handler prints that 0 as a fact.
- Red examples (grounded):
  - `"How many awards did 'Inception' win?"` -> `The factual answer is: 0`. Probe: entity Q25188 (Inception, film); the true count of Q25188 P166 is 6.
  - `"How many awards has Meryl Streep won?"` -> `The factual answer is: 0`. Probe: entity Q873 (Meryl Streep, human); the true count of Q873 P166 is 35.
  - `"How many cast members does 'Inception' have?"` -> `The factual answer is: 0`. Probe: the true count of Q25188 P161 is 21, of which 0 are films.
  - Control (green): `"How many films did Christopher Nolan direct?"` -> `The factual answer is: 11`.
- Failing phase hypothesis: Phase 4 (query construction).
- Candidate gate phrase: "Count the relation over any object class; keep the film type filter only when the question asks for films."

## D2 - Multiple mentions in one message

- Contract under attack: B1 (source -> phase 1: "tokens, quotes, and casing carry the entity mention") and B2 (phase 1 -> 2: "the recognised mention is the intended entity"). The assumption is one mention and one question per message.
- Why it breaks: `_find_entity` returns the first quoted label, so a distractor before the target wins. The `_inside_longer_title` guard refuses the whole message when a recognised mention sits next to other capitalised words.
- Red examples (grounded):
  - `"I love 'Jaws'. Who directed 'Inception'?"` -> `The factual answer is: Steven Spielberg`. Probe: span=(8, 12) -> Q189505 (Jaws, film, P57 -> Q8877 Steven Spielberg); the asked entity Q25188 (Inception) is never used.
  - `"Who directed 'The Godfather'? Who directed 'Inception'?"` -> `The factual answer is: Francis Ford Coppola`. Probe: the second question is dropped; Q25188 P57 -> Q25191 (Christopher Nolan) is never queried.
  - `"I love Jaws. Who directed Inception?"` -> `I'm not sure which movie or person you mean...`. Probe: span=(0, 0), no candidates, although both titles exist in the lexicon.
- Failing phase hypothesis: Phase 1 (entity recognition).
- Candidate gate phrase: "Take the mention nearest the question word; a second mention or question asks for clarification, never a silent answer."

## D3 - Superlative word in trailing context

- Contract under attack: B3 (phase 2 -> 3: "the remaining words carry the relation phrase") and B4. The assumption is that a superlative word modifies the relation only.
- Why it breaks: `EARLIEST` and `LATEST` match any "first", "last" or "latest" left in the text after the entity span is blanked. The kind then overrides the lookup, and the film-only superlative template returns no row, so a valid lookup becomes `no_facts`.
- Red examples (grounded):
  - `"Who directed 'Batman Begins', the first film in the trilogy?"` -> `Sorry, my knowledge graph has no information about the director of Batman Begins.` Probe: entity Q166262, kind=earliest; control `"Who directed 'Batman Begins'?"` -> `Christopher Nolan`.
  - `"Who wrote the screenplay of 'The Godfather', the first film of the trilogy?"` -> `Sorry, my knowledge graph has no information about the screenwriter of The Godfather.` Probe: entity Q47703; control -> `Francis Ford Coppola and Mario Puzo`.
  - `"Who composed the music for 'Inception', the latest film I watched?"` -> `Sorry, my knowledge graph has no information about the composer of Inception.` Probe: entity Q25188; control -> `Hans Zimmer`.
  - Control (green): `"Who directed 'The Last Emperor'?"` -> `Bernardo Bertolucci`, because "last" sits inside the span.
- Failing phase hypothesis: Phase 3 (relation detection).
- Candidate gate phrase: "Let a superlative word set the kind only when it modifies the relation, never in trailing context."

## D4 - Mention character folding (diacritics, separators, NFC)

- Contract under attack: B1 -> B2, the normalisation seam before `Parser.parse`. The assumption is that the typed mention equals the label string.
- Why it breaks: exact lookup and the fuzzy pass both compare raw characters. Accent folding is absent, so "amelie" scores 0.8333 against "amélie", below the 0.85 cutoff, and T4 cannot reach it. Separator variants and NFD input fail the same way.
- Red examples (grounded):
  - `"who directed 'Amelie'?"` -> `I'm not sure which movie or person you mean...`. Probe: `lbl2ent['amelie'] = []`; control `"Who directed 'Amélie'?"` -> `Jean-Pierre Jeunet`, entity Q484048 (Amélie, film).
  - `"who directed 101 reykjavik?"` -> `Sorry, my knowledge graph has no information about the director of 101.` Probe: span=(13, 16) links Q113116290 (label "101"); control `"who directed '101 reykjavík'?"` -> `Baltasar Kormákur`, entity Q165525 (101 Reykjavík, film).
  - `"who directed 3 iron?"` -> no_entity reply; control `"who directed '3-Iron'?"` -> `Kim Ki-duk`, entity Q489818. `"who directed 50 50?"` -> no_entity reply; control `"who directed '50/50'?"` -> `Jonathan Levine`, entity Q859448.
  - `"who directed 8 1/2?"` -> `Sorry, my knowledge graph has no information about the director of 2.` Probe: entity Q26989920 (label "2"); control `"who directed '8½'?"` -> `Federico Fellini`, entity Q12018.
  - NFD control: `"who directed Ame\u0301lie?"` -> no_entity reply, because every lexicon label is NFC.
- Failing phase hypothesis: Phase 1 (entity recognition).
- Candidate gate phrase: "Fold the mention to NFC, then strip accents and fold separators, before any label lookup."

## D5 - Yes/no answer shape

- Contract under attack: B7 (phase 6 -> output: "the reply satisfies the expected strings") and B4. The assumption is that the question asks for an entity list.
- Why it breaks: no phase marks a yes/no question, and the film rule in `parse` forces direction "out". The reply then names the director of the mentioned film, so the question stays unanswered. A false premise reads like a confirmed answer.
- Red examples (grounded):
  - `"Did Steven Spielberg direct 'Inception'?"` -> `The factual answer is: Christopher Nolan`. Probe: entity Q25188, P57 out; the true answer is No.
  - `"Did Christopher Nolan direct 'Jaws'?"` -> `The factual answer is: Steven Spielberg`. Probe: entity Q189505 (Jaws, film), P57 out -> Q8877; the true answer is No.
  - `"Was 'Inception' directed by Steven Spielberg?"` -> `The factual answer is: Christopher Nolan`.
- Failing phase hypothesis: Phase 6 (answer generation).
- Candidate gate phrase: "A yes/no question returns Yes, No, or a defined refusal when the graph cannot check the claim."

## D6 - Date literal time part

- Contract under attack: B6 (phase 5 -> 6: "formatting preserves the values the eval checks"). The assumption is that date literals carry the suffix `T00:00:00Z`.
- Why it breaks: `nlg.format_term` strips only `T00:00:00Z`. The graph holds a second shape, `T00:00:00` without the Z, on 602 film release-date rows. The time part then leaks into the reply, while the golden case expects a plain date such as `2016-01-23`.
- Red examples (grounded):
  - `"When did 'The Blue Bird Vol. 2' come out?"` -> `The factual answer is: 1920-03-05T00:00:00`. Probe: entity Q8229794167428617, literal `1920-03-05T00:00:00`.
  - `"When was 'Tokyo Chorus II' released?"` -> `The factual answer is: 1934-11-15T00:00:00`. Probe: entity Q0666980522408053, literal `1934-11-15T00:00:00`.
  - Control (green): `"When did the movie 'Manchester by the Sea' come out?"` -> `The factual answer is: 2016-01-23`.
- Failing phase hypothesis: Phase 6 (answer generation).
- Candidate gate phrase: "Strip a `T00:00:00` time part with or without the Z before the reply."

## D7 - Glued tokens (missing spaces)

- Contract under attack: B1 (source -> phase 1: "`\w` tokens are the right word boundaries") and B3. The assumption is that words are separated by a space or punctuation.
- Why it breaks: the token scan and `phrase_pattern` need a neighbour space. A missing space glues the relation word to the question word or to the mention. Recognition can survive, but the relation phrase then disappears, or both sides of the match fail.
- Red examples (grounded):
  - `"Whodirected 'Inception'?"` -> `I found Inception, but I'm not sure what you'd like to know...`. Probe: entity Q25188 found, predicate None, error no_relation.
  - `"who directedinception?"` -> `I'm not sure which movie or person you mean...`. Probe: span=(0, 0), no candidates, error no_entity, although `inception` is a label.
  - Control (green): `"Who directed'Inception'?"` -> `The factual answer is: Christopher Nolan`, because the quote marks the boundary.
- Failing phase hypothesis: Phase 1 (entity recognition).
- Candidate gate phrase: "Re-split a glued token when a known relation word or a known label has no neighbour space."

## D8 - Relation paraphrases (nominalisation and idiom)

- Contract under attack: B3 (phase 2 -> 3: "the remaining words carry the relation phrase") and the B4 sender line "the relation map is complete".
- Why it breaks: `Parser.phrases` holds property labels plus a fixed synonym list in `data/relations.json`. Nominalisations ("directing") and idiomatic relations ("at the helm", "behind the camera") are absent. The parser then reports no_relation, although the relation is unambiguous.
- Red examples (grounded):
  - `"Who did the directing for 'Inception'?"` -> `I found Inception, but I'm not sure what you'd like to know...`. Probe: entity Q25188, predicate None, error no_relation.
  - `"Who was at the helm of 'Inception'?"` -> the same no_relation reply. Probe: entity Q25188, predicate None.
  - `"Who is behind the camera on 'Inception'?"` -> the same no_relation reply. Probe: entity Q25188, predicate None.
  - Controls (green): `"Who is the director of 'Inception'?"` -> `Christopher Nolan`; `"Which filmmaker made 'Inception'?"` -> `Christopher Nolan`; `"By whom was 'Inception' directed?"` -> `Christopher Nolan`; `"Who is the director of photography of 'Inception'?"` -> `Wally Pfister`.
- Failing phase hypothesis: Phase 3 (relation detection).
- Candidate gate phrase: "Map a relation nominalisation or idiom to a predicate before the no_relation reply."

---

## S4 gate verification (added by the orchestrator, 2026-10-16)

- Every cited QID was probed against the lexicon: all 16 exist with real labels (`docs/design/adversarial/eval/s4-verification.log`).
- All 16 red examples were re-run; every wrong reply reproduced exactly as written above (same log).
- D1 true counts confirmed by independent SPARQL: Q25188 P166 = 6, Q873 P166 = 35, Q25188 P161 = 21 (same log).
- Impact triage, 6 varied cases per type (`docs/design/adversarial/eval/s4-triage.log`): D2 6/6, D3 6/6, D5 6/6, D8 6/6, D1 5/6, D4 5/6, D7 4/6, D6 2/6.
- Operator cap (Q6: up to 5 new types by measured impact): full datasets go to D2, D3, D5, D8, D1.
- Deferred with reason (recorded, not deleted): D4, D6, D7 fall below the impact ranking; their evidence stays in this document for a future iteration.
