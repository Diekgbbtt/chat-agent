#!/usr/bin/env python3
"""S5: build the adversarial eval datasets (evals/adversarial/*.jsonl) from the knowledge graph.

Conventions, shared with docs/design/adversarial/05-dataset-manifest.md:
- expected/forbidden: substrings the eval checks against the reply (case-insensitive).
- every expected value is harvested from the KG (or is the fixed nlg template text for safe failures);
- every forbidden value is checked against the expected reply composition before it is accepted;
- grounding = {"entity": QID, "relation": "wdt:P..", "check": "<SPARQL>", "assert": <kind>} with kinds
  expected_in_rows | forbidden_in_rows | expected_count | ask_yesno | no_film_rows.

Run: .venv/bin/python scripts/adversarial/build_datasets.py
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rapidfuzz import process as rf_process  # noqa: E402
from rapidfuzz.distance import OSA  # noqa: E402

from agent import nlg  # noqa: E402
from agent.cli import load_agent  # noqa: E402

WD = "http://www.wikidata.org/entity/"
OUT = ROOT / "evals" / "adversarial"
SEED = 20261016
rng = random.Random(SEED)

agent = load_agent()
HANDLER = next(h for h in agent.handlers if hasattr(h, "parser"))
KG, LEX, PARSER = HANDLER.kg, HANDLER.lex, HANDLER.parser

ANSWER_T = "the factual answer is: "
NO_ENTITY_T = nlg.no_entity()
NO_RELATION_T = "I'm not sure what you'd like to know"
NO_FACTS_T = "Sorry, my knowledge graph has no information about the"


def rows(query: str, cap: int | None = None, timeout: float = 120.0):
    res = KG.query(query, timeout=timeout) if cap is None else KG.query(query, max_rows=cap, timeout=timeout)
    return res.rows


def label(e: str) -> str:
    return LEX.ent2lbl.get(e, e)


_DEGREE: dict[str, int] = {}


def degree(e: str) -> int:
    if e not in _DEGREE:
        _DEGREE[e] = int(rows(f"SELECT (COUNT(*) AS ?n) WHERE {{ <{WD}{e}> ?p ?o }}")[0][0].value)
    return _DEGREE[e]


def strip_article(s: str) -> str:
    s = s.casefold().replace("\u2019", "'").strip()
    return re.sub(r"^(the|a|an)\s+", "", s)


def rank_entities(entities) -> list[str]:
    ents = list(dict.fromkeys(e for e in entities if e))
    if len(ents) == 1:
        return ents
    return sorted(ents, key=lambda e: (not LEX.is_film(e), -degree(e)))


def answer_values(entity: str, prop: str, direction: str = "out") -> list[str]:
    """The reply values of a lookup: labels of the objects (or subjects), like nlg.answer would show.

    The handler drops IRIs without a label, so this mirror drops them too.
    """
    triple = f"<{WD}{entity}> wdt:{prop} ?x ." if direction == "out" else f"?x wdt:{prop} <{WD}{entity}> ."
    rs = rows(f"SELECT DISTINCT ?x ?label WHERE {{ {triple} OPTIONAL {{ ?x rdfs:label ?label }} }}")
    return sorted({r[1].value for r in rs if r[1]}, key=str.casefold)


def safe_forbidden(forbidden, expected, haystacks=()) -> list[str]:
    """Forbidden strings that collide (casefold substring) with the expected reply composition."""
    hay = [e.casefold() for e in expected] + [h.casefold() for h in haystacks]
    return [f for f in forbidden if any(f.casefold() in h for h in hay)]


# --------------------------------------------------------------------------------------------------
# shared entity pools

FAMOUS_LABELS = [
    "Inception", "Interstellar", "The Godfather", "The Godfather Part II", "The Matrix",
    "The Matrix Reloaded", "Jaws", "The Handmaiden", "Titanic", "Batman Begins", "The Dark Knight",
    "The Prestige", "Parasite", "Whiplash", "The Departed", "The Pianist", "Schindler's List",
    "Forrest Gump", "The Terminator", "Oppenheimer", "The Silence of the Lambs", "Se7en",
    "The Shawshank Redemption", "Goodfellas", "Gladiator", "Alien", "The Shining", "Up", "Her",
    "La La Land", "Get Out", "The Grand Budapest Hotel", "Amélie", "Spirited Away", "Seven Samurai",
    "Back to the Future", "Die Hard", "Dunkirk", "Memento", "The Usual Suspects", "Basic Instinct",
    "Dancer in the Dark", "The Truman Show", "Pulp Fiction", "12 Angry Men",
]


def resolve_film(label_text: str) -> str | None:
    ids = LEX.lbl2ent.get(label_text.casefold().replace("\u2019", "'"), [])
    films = [e for e in ids if LEX.is_film(e)]
    if not films:
        return None
    return rank_entities(films)[0]


def film_pool() -> dict[str, tuple[str, list[str]]]:
    """curated label -> (entity, P57 answer values); only films with labelled directors."""
    pool = {}
    for lb in FAMOUS_LABELS:
        ent = resolve_film(lb)
        if not ent:
            continue
        vals = answer_values(ent, "P57")
        if vals:
            pool[lb] = (ent, vals)
    return pool


POOL = film_pool()


def top_directors(n=10) -> list[tuple[str, int]]:
    rs = rows("""SELECT ?d (COUNT(DISTINCT ?f) AS ?n) WHERE {
                  ?f wdt:P57 ?d . ?f wdt:P31 wd:Q11424 } GROUP BY ?d ORDER BY DESC(?n) LIMIT 30""")
    out = []
    for d, cnt in rs:
        q = d.value[len(WD):]
        if q in LEX.ent2lbl and int(cnt.value) >= 2:
            out.append((q, int(cnt.value)))
    return out[:n]


def top_writers(n=6) -> list[tuple[str, int]]:
    rs = rows("""SELECT ?w (COUNT(DISTINCT ?f) AS ?n) WHERE {
                  ?f wdt:P58 ?w . ?f wdt:P31 wd:Q11424 } GROUP BY ?w ORDER BY DESC(?n) LIMIT 30""")
    out = []
    for w, cnt in rs:
        q = w.value[len(WD):]
        if q in LEX.ent2lbl and int(cnt.value) >= 2:
            out.append((q, int(cnt.value)))
    return out[:n]


def films_of(q: str, prop: str = "P57") -> list[str]:
    rs = rows(f"SELECT DISTINCT ?f WHERE {{ ?f wdt:{prop} <{WD}{q}> }}")
    return [r[0].value[len(WD):] for r in rs]


# --------------------------------------------------------------------------------------------------
# builders


def build_t1() -> list[dict]:
    cases = []
    n = 0

    def add(input_, expected, forbidden, entity, relation, check, assert_="expected_in_rows"):
        nonlocal n
        n += 1
        bad = safe_forbidden(forbidden, expected, (ANSWER_T,))
        if bad:
            raise AssertionError(f"T1 forbidden collides: {bad} in {input_}")
        cases.append({"id": f"t1-negation-{n:03d}", "input": input_, "expected": expected,
                      "forbidden": forbidden,
                      "grounding": {"entity": entity, "relation": f"wdt:{relation}", "check": check,
                                    "assert": assert_}})

    # film side, P57: complement of "films directed by D"
    for di, (d, _cnt) in enumerate(top_directors(8)):
        q = (f"SELECT ?x ?label WHERE {{ ?x wdt:P31 wd:Q11424 . "
             f"FILTER NOT EXISTS {{ ?x wdt:P57 <{WD}{d}> }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = [r[1].value for r in rs if r[1]]
        early = [lb for lb in labels[:400] if len(lb) >= 4 and not lb.isdigit()][:2]
        if len(early) < 2:
            continue
        forb_pool = sorted((label(f) for f in films_of(d) if f in LEX.ent2lbl), key=len, reverse=True)
        forbidden = [f for f in forb_pool if not any(f.casefold() in lb.casefold() for lb in labels)]
        forbidden = forbidden[:2]
        dname = label(d)
        forms = [f"Which movies did {dname} not direct?",
                 f"Which films has {dname} not directed?",
                 f"Which movies were not directed by {dname}?"]
        if di < 4:
            forms.append(f"Which movies did {dname} never direct?")
        for form in forms:
            add(form, early, forbidden, d, "P57", q)

    # film side, P58: complement of "films written by W"
    for w, _cnt in top_writers(5):
        q = (f"SELECT ?x ?label WHERE {{ ?x wdt:P31 wd:Q11424 . "
             f"FILTER NOT EXISTS {{ ?x wdt:P58 <{WD}{w}> }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = [r[1].value for r in rs if r[1]]
        early = [lb for lb in labels[:400] if len(lb) >= 4 and not lb.isdigit()][:2]
        if len(early) < 2:
            continue
        wfilms = [label(f) for f in films_of(w, "P58") if f in LEX.ent2lbl]
        forbidden = [f for f in wfilms if not any(f.casefold() in lb.casefold() for lb in labels)][:2]
        wname = label(w)
        for form in (f"Which films did {wname} not write?", f"Which movies has {wname} not written?"):
            add(form, early, forbidden, w, "P58", q)

    # person side, P57: complement of "directors who directed F"
    for f, fvals in list(POOL.values())[:8]:
        q = (f"SELECT DISTINCT ?x ?label WHERE {{ ?f wdt:P57 ?x . "
             f"FILTER NOT EXISTS {{ <{WD}{f}> wdt:P57 ?x }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = {r[1].value for r in rs if r[1]}
        pool = [n2 for n2 in ("Alfred Hitchcock", "Steven Spielberg", "Christopher Nolan",
                              "Martin Scorsese", "Quentin Tarantino", "Ridley Scott") if n2 in labels]
        expected = pool[:2] if len(pool) >= 2 else [lb for lb in sorted(labels, key=str.casefold)
                                                   if len(lb) >= 5][:2]
        if len(expected) < 2:
            continue
        forbidden = [v for v in fvals if not any(v.casefold() in lb.casefold() for lb in labels)][:2]
        title = label(f)
        for form in (f"Who did not direct '{title}'?", f"Who has not directed '{title}'?"):
            add(form, expected, forbidden, f, "P57", q)

    # masking controls: negation words inside the title must not trigger T1
    masking = []
    for cand in ("No Country for Old Men", "Notting Hill", "North by Northwest", "Never Let Me Go",
                 "Notorious", "Noah", "Nocturnal Animals", "Not Another Teen Movie",
                 "Notes on a Scandal", "None but the Brave", "Nope"):
        ent = resolve_film(cand)
        if not ent:
            continue
        vals = answer_values(ent, "P57")
        if not vals:
            continue
        decoy = next((d for d in ("Alfred Hitchcock", "Steven Spielberg", "Christopher Nolan")
                      if not any(d.casefold() in v.casefold() for v in vals)), None)
        if not decoy:
            continue
        masking.append((cand, ent, vals, decoy))
    for cand, ent, vals, decoy in masking[:10]:
        add(f"Who directed '{cand}'?", vals, [decoy], ent, "P57",
            f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x OPTIONAL {{ ?x rdfs:label ?label }} }}")
    # combined: real negation outside a title that contains a negation word
    for cand, ent, vals, _decoy in masking[:2]:
        q = (f"SELECT DISTINCT ?x ?label WHERE {{ ?f wdt:P57 ?x . "
             f"FILTER NOT EXISTS {{ <{WD}{ent}> wdt:P57 ?x }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = {r[1].value for r in rs if r[1]}
        pool = [n2 for n2 in ("Alfred Hitchcock", "Steven Spielberg", "Christopher Nolan")
                if n2 in labels]
        expected = pool[:2] if len(pool) >= 2 else [lb for lb in sorted(labels, key=str.casefold)
                                                   if len(lb) >= 5][:2]
        if len(expected) < 2:
            continue
        forbidden = [v for v in vals if not any(v.casefold() in lb.casefold() for lb in labels)][:2]
        add(f"Who did not direct '{cand}'?", expected, forbidden, ent, "P57", q)

    # film side, new syntax: "What did D not direct?" / "What has D not directed?"
    # the reference template of the negation type: a director names the subject, films are the answer
    for di, (d, _cnt) in enumerate(top_directors(8)):
        q = (f"SELECT ?x ?label WHERE {{ ?x wdt:P31 wd:Q11424 . "
             f"FILTER NOT EXISTS {{ ?x wdt:P57 <{WD}{d}> }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = [r[1].value for r in rs if r[1]]
        early = [lb for lb in labels[:400] if len(lb) >= 4 and not lb.isdigit()][:2]
        if len(early) < 2:
            continue
        forb_pool = sorted((label(f) for f in films_of(d) if f in LEX.ent2lbl), key=len, reverse=True)
        forbidden = [f for f in forb_pool if not any(f.casefold() in lb.casefold() for lb in labels)][:2]
        dname = label(d)
        forms = [f"What did {dname} not direct?", f"What has {dname} not directed?"]
        if di < 3:
            forms += [f"What movies did {dname} not direct?", f"What films has {dname} not directed?"]
        for form in forms:
            add(form, early, forbidden, d, "P57", q)

    # person side, director noun: "Which directors did not direct 'F'?"
    for f, fvals in list(POOL.values())[:8]:
        q = (f"SELECT DISTINCT ?x ?label WHERE {{ ?f wdt:P57 ?x . "
             f"FILTER NOT EXISTS {{ <{WD}{f}> wdt:P57 ?x }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = {r[1].value for r in rs if r[1]}
        pool = [n2 for n2 in ("Alfred Hitchcock", "Steven Spielberg", "Christopher Nolan",
                              "Martin Scorsese", "Quentin Tarantino", "Ridley Scott") if n2 in labels]
        expected = pool[:2] if len(pool) >= 2 else [lb for lb in sorted(labels, key=str.casefold)
                                                   if len(lb) >= 5][:2]
        if len(expected) < 2:
            continue
        forbidden = [v for v in fvals if not any(v.casefold() in lb.casefold() for lb in labels)][:2]
        title = label(f)
        for form in (f"Which directors did not direct '{title}'?",
                     f"What directors have not directed '{title}'?"):
            add(form, expected, forbidden, f, "P57", q)

    # person side, several films: "Which directors did not direct 'A' or 'B'?" (neither film)
    pairs = [("Jaws", "Alien"), ("The Godfather", "Titanic"), ("Inception", "Parasite"),
             ("The Matrix", "Interstellar"), ("The Handmaiden", "Whiplash"),
             ("The Departed", "The Pianist")]
    for i, (a, b) in enumerate(pairs):
        if a not in POOL or b not in POOL:
            continue
        fa, fvals_a = POOL[a]
        fb, fvals_b = POOL[b]
        q = (f"SELECT DISTINCT ?x ?label WHERE {{ ?f wdt:P57 ?x . "
             f"FILTER NOT EXISTS {{ <{WD}{fa}> wdt:P57 ?x }} FILTER NOT EXISTS {{ <{WD}{fb}> wdt:P57 ?x }} "
             f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = {r[1].value for r in rs if r[1]}
        pool = [n2 for n2 in ("Alfred Hitchcock", "Steven Spielberg", "Christopher Nolan",
                              "Martin Scorsese", "Quentin Tarantino", "Ridley Scott") if n2 in labels]
        expected = pool[:2] if len(pool) >= 2 else [lb for lb in sorted(labels, key=str.casefold)
                                                   if len(lb) >= 5][:2]
        if len(expected) < 2:
            continue
        forbidden = [v for v in fvals_a + fvals_b
                     if not any(v.casefold() in lb.casefold() for lb in labels)][:2]
        forms = [f"Which directors did not direct '{a}' or '{b}'?"]
        if i < 3:
            forms.append(f"What directors have not directed '{a}' or '{b}'?")
        for form in forms:
            add(form, expected, forbidden, fa, "P57", q)

    # actor universe: the noun names the answer class (P161 cast members), the verb names the relation
    ACTOR_MARKERS = ["Meryl Streep", "Julia Roberts", "Gary Oldman", "Tom Hanks", "Diane Keaton",
                     "Robert De Niro", "Al Pacino", "Gene Hackman", "Morgan Freeman", "Robert Duvall",
                     "James Caan", "Leonardo DiCaprio", "Harrison Ford", "Kevin Costner"]
    for i, act_lb in enumerate(("Unforgiven", "Argo", "Annie Hall", "The Godfather", "Jaws")):
        ent = resolve_film(act_lb)
        if not ent:
            continue
        q = (f"SELECT DISTINCT ?x ?label WHERE {{ ?f wdt:P161 ?x . ?x wdt:P31 wd:Q5 . "
             f"FILTER NOT EXISTS {{ <{WD}{ent}> wdt:P57 ?x }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = [r[1].value for r in rs if r[1]]
        seen = set(labels)
        cast = set(answer_values(ent, "P161"))
        striking = ([m for m in ACTOR_MARKERS if m in seen and m in cast]
                    or [v for v in labels if v in cast][:1])
        marker = [m for m in ACTOR_MARKERS if m in seen and m not in cast]
        expected = list(dict.fromkeys(striking[:1] + marker[:1]))
        if len(expected) < 2:
            continue
        forbidden = answer_values(ent, "P57")[:2]
        title = label(ent)
        forms = [f"Which actors did not direct '{title}'?"]
        if i < 3:
            forms.append(f"What actors have not directed '{title}'?")
        for form in forms:
            add(form, expected, forbidden, ent, "P57", q)

    # credit-less person subject: the negation must not be dropped as "no facts"
    for lb, form in (("Marilyn Monroe", "What did {p} not direct?"),
                     ("Audrey Hepburn", "What has {p} not directed?")):
        ids = LEX.lbl2ent.get(lb.casefold(), [])
        person = next((e for e in rank_entities(ids) if LEX.is_human(e)), None)
        if not person or films_of(person):
            continue
        q = (f"SELECT ?x ?label WHERE {{ ?x wdt:P31 wd:Q11424 . "
             f"FILTER NOT EXISTS {{ ?x wdt:P57 <{WD}{person}> }} OPTIONAL {{ ?x rdfs:label ?label }} }}")
        rs = rows(q)
        labels = [r[1].value for r in rs if r[1]]
        early = [e for e in labels[:400] if len(e) >= 4 and not e.isdigit()][:2]
        if len(early) < 2:
            continue
        add(form.format(p=lb), early, ["no information"], person, "P57", q)

    return cases


def build_t2() -> list[dict]:
    cases, n = [], 0
    ALL = list(LEX.lbl2ent)

    def add(input_, expected, forbidden, entity, relation, check, assert_="forbidden_in_rows"):
        nonlocal n
        n += 1
        bad = safe_forbidden(forbidden, expected, (ANSWER_T, NO_ENTITY_T))
        if bad:
            raise AssertionError(f"T2 forbidden collides: {bad} in {input_}")
        cases.append({"id": f"t2-subvention-{n:03d}", "input": input_, "expected": expected,
                      "forbidden": forbidden,
                      "grounding": {"entity": entity, "relation": f"wdt:{relation}", "check": check,
                                    "assert": assert_}})

    fragments = []
    for lb, ids in LEX.lbl2ent.items():
        if len(lb) > 6 or " " in lb or not re.fullmatch(r"[a-z]+", lb):
            continue
        films = [e for e in ids if LEX.is_film(e)]
        if not films:
            continue
        ent = rank_entities(films)[0]
        vals = answer_values(ent, "P57")
        if vals and degree(ent) >= 15:
            fragments.append((lb, ent, vals, degree(ent)))
    seen = set()
    fragments = [f for f in sorted(fragments, key=lambda t: -t[3]) if not (f[0] in seen or seen.add(f[0]))]
    fragments = fragments[:12]

    carriers = ["looking {x}", "the {x} within", "{x} of the deep", "growing {x}", "long live the {x}",
                "{x} comes home", "a portrait of {x}", "the return of {x}", "waiting for {x}",
                "city of {x}", "remembering {x}", "dancing with {x}"]
    fuzzy = PARSER.fuzzy_labels
    for lb, ent, vals, _deg in fragments:
        crafted = []
        cands = ["don't look up", "looking up"] if lb == "up" else []
        cands += [c.format(x=lb) for c in carriers]
        for cand in cands:
            if cand in LEX.lbl2ent or cand in crafted:
                continue
            m = rf_process.extractOne(cand, fuzzy, scorer=OSA.normalized_similarity)
            if m and m[1] >= 0.80:
                continue
            crafted.append(cand)
            if len(crafted) == 3:
                break
        for i, y in enumerate(crafted):
            if i == 0:
                input_ = f"Who directed {y}?"
            elif i == 1:
                input_ = f"Who directed '{y[0].upper() + y[1:]}'?"
            else:
                sval = answer_values(ent, "P58")
                if sval:
                    input_ = f"Who wrote the screenplay for {y}?"
                else:
                    input_ = f"Who was the director of {y}?"
            fvals = answer_values(ent, "P58") if "wrote" in input_ else vals
            if not fvals:
                continue
            check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:"
                     f"{'P58' if 'wrote' in input_ else 'P57'} ?x OPTIONAL {{ ?x rdfs:label ?label }} }}")
            add(input_, [NO_ENTITY_T], fvals, ent, "P58" if "wrote" in input_ else "P57", check)

    for lb, ent, vals, _deg in fragments:
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        n += 1
        cases.append({"id": f"t2-subvention-{n:03d}", "input": f"Who directed '{label(ent)}'?",
                      "expected": vals, "forbidden": [],
                      "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                    "assert": "expected_in_rows"}})
        n += 1
        cases.append({"id": f"t2-subvention-{n:03d}",
                      "input": f"Tell me the director of '{label(ent)}'.", "expected": vals,
                      "forbidden": [],
                      "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                    "assert": "expected_in_rows"}})
    return cases


def build_t3() -> list[dict]:
    cases, n = [], 0
    targets = [("Inception", "P57"), ("The Godfather", "P57"), ("Interstellar", "P58"),
               ("The Handmaiden", "P58"), ("The Matrix", "P57"), ("Jaws", "P57"),
               ("Titanic", "P57"), ("Batman Begins", "P57"), ("Parasite", "P57"),
               ("Whiplash", "P86"), ("The Departed", "P57"), ("The Pianist", "P57")]
    red = ["''{T}''", "' {T} '", "'{T}.'", "'{T}?'"]
    green = ["{T}", "'{T}'", '"{T}"', "\u201c{T}\u201d", "'{T}", "'{T}' (the film)",
             "\u2018{T}\u2019"]
    for i, (lb, prop) in enumerate(targets):
        if lb not in POOL:
            continue
        ent, _ = POOL[lb]
        vals = answer_values(ent, prop)
        if not vals:
            continue
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:{prop} ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        question = {"P57": "Who directed {T}?", "P58": "Who wrote the screenplay for {T}?",
                    "P86": "Who composed the music for {T}?"}[prop]
        forbidden = []
        if lb in ("The Godfather", "The Godfather Part II"):
            forbidden = ["Lal and Siddique"]
        shapes = [red[i % 3], green[i % len(green)], green[(i + 2) % len(green)], green[4]]
        if i % 2 == 0:
            shapes.append(red[(i + 1) % 3])
        if i % 3 == 1:
            shapes.append(red[3])
        for shape in shapes:
            n += 1
            mention = shape.format(T=lb)
            input_ = question.format(T=mention)
            bad = safe_forbidden(forbidden, vals, (ANSWER_T,))
            if bad:
                raise AssertionError(f"T3 forbidden collides: {bad} in {input_}")
            cases.append({"id": f"t3-quote-shapes-{n:03d}", "input": input_, "expected": vals,
                          "forbidden": forbidden,
                          "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                        "assert": "expected_in_rows"}})
    # lowercase mention variants
    for lb, prop in (("Inception", "P57"), ("The Handmaiden", "P57"), ("Jaws", "P57")):
        if lb not in POOL:
            continue
        ent, _ = POOL[lb]
        vals = answer_values(ent, prop)
        if not vals:
            continue
        n += 1
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:{prop} ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        cases.append({"id": f"t3-quote-shapes-{n:03d}",
                      "input": f"who directed '{lb.casefold()}'?", "expected": vals, "forbidden": [],
                      "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                    "assert": "expected_in_rows"}})
    return cases


def family_scores(typo: str, limit: int = 40) -> list[tuple[str, float]]:
    fam: dict[str, float] = {}
    for choice, score, _ in rf_process.extract(typo, SEARCH_SPACE, scorer=OSA.normalized_similarity,
                                               limit=limit):
        f = strip_article(choice)
        if f not in fam or score > fam[f]:
            fam[f] = score
    return sorted(fam.items(), key=lambda kv: -kv[1])


def build_t4() -> list[dict]:
    cases, n = [], 0
    TYPOS = {
        "the godfather": ["godfahter", "godfatherr", "godfathre", "godfther", "godffather"],
        "the terminator": ["terminater", "terminatr", "termonator", "terminatoor", "terminnator"],
        "jaws": ["jazws", "jawss", "jaws!", "jwaws", "jawws"],
        "interstellar": ["intersteller", "interstallar", "interstellr", "interstelar", "intertsellar"],
        "inception": ["incepton", "inceptio", "incepsion", "inceptiom", "inceptionn"],
        "schindler's list": ["schindlers list", "schinlders list", "schindler's lsit", "shindler's list",
                             "schindler's liat"],
        "forrest gump": ["forrst gump", "forest gump", "forresst gump", "forrest gmp", "forrset gump"],
        "the matrix": ["the matirx", "the mtrix", "the matrx", "the matritx", "teh matrix"],
        "batman begins": ["batman begns", "batmen begins", "batman bigins", "batmon begins",
                          "batman beginss"],
        "the prestige": ["the prestge", "the prestiege", "the prestrige", "the perstige", "the prestig"],
        "parasite": ["parasit", "parsite", "paratise", "parasitte", "parasight"],
        "the departed": ["the deaprted", "the departd", "the deparred", "the deported",
                         "the departted"],
        "the pianist": ["the panist", "the pianst", "the pianis", "the peanist", "the piannist"],
    }
    chosen_targets = 0
    for lb, typos in TYPOS.items():
        fam = strip_article(lb)
        ids = FAMILIES.get(fam, [])
        films = rank_entities([e for e in ids if LEX.is_film(e)])
        if not films:
            continue
        ent = films[0]
        p57 = answer_values(ent, "P57")
        if not p57:
            continue
        made = 0
        for i, typo in enumerate(typos):
            if typo in LEX.lbl2ent:
                continue
            scores = family_scores(typo)
            if not scores or scores[0][0] != fam:
                continue
            top = scores[0][1]
            second = scores[1][1] if len(scores) > 1 else 0.0
            thr = 0.80 if len(fam) <= 6 else 0.85
            if top < thr or top - second < 0.05:
                continue
            prop = "P57"
            if i % 4 == 3 and answer_values(ent, "P58"):
                prop = "P58"
            vals = answer_values(ent, prop)
            if not vals:
                continue
            qword = {"P57": f"Who directed {typo}?", "P58": f"Who wrote the screenplay for {typo}?"}[prop]
            if i % 3 == 2:
                qword = qword.replace(f"{typo}", f"'{typo}'")
            forbidden = []
            m = rf_process.extractOne(typo, PARSER.fuzzy_labels, scorer=OSA.normalized_similarity,
                                      score_cutoff=0.85)
            if m:
                wrong_ent = rank_entities(LEX.lbl2ent[m[0]])[0]
                if wrong_ent != ent:
                    wvals = answer_values(wrong_ent, prop)
                    if wvals and not any(w.casefold() in v.casefold() for w in wvals for v in vals):
                        forbidden = wvals
            bad = safe_forbidden(forbidden, vals, (ANSWER_T,))
            if bad:
                forbidden = []
            n += 1
            check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:{prop} ?x "
                     f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
            cases.append({"id": f"t4-typos-{n:03d}", "input": qword, "expected": vals,
                          "forbidden": forbidden,
                          "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                        "assert": "expected_in_rows"}})
            made += 1
            if made >= 4:
                break
        if made >= 3:
            chosen_targets += 1
        if chosen_targets >= 12:
            break

    # safe failures: scrambles that match nothing
    safe_targets = [(lb, ent) for lb, (ent, vals) in list(POOL.items()) if vals][:12]
    made_safe = 0
    all_labels = ALL_LABELS
    for lb, ent in safe_targets:
        core = strip_article(lb)
        for _ in range(40):
            letters = list(re.sub(r"[^a-z ]", "", core))
            rng.shuffle(letters)
            cand = "".join(letters)
            if cand in LEX.lbl2ent or len(cand) < 4:
                continue
            best = rf_process.extractOne(cand, all_labels, scorer=OSA.normalized_similarity)
            if best and best[1] >= 0.70:
                continue
            vals = answer_values(ent, "P57")
            if not vals:
                continue
            n += 1
            check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                     f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
            cases.append({"id": f"t4-typos-{n:03d}", "input": f"Who directed '{cand}'?",
                          "expected": [NO_ENTITY_T], "forbidden": vals,
                          "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                        "assert": "forbidden_in_rows"}})
            made_safe += 1
            break
        if made_safe >= 8:
            break

    # controls: known working typos
    controls = [("Who directed the Godfahter?", "The Godfather", "P57", ["Lal and Siddique"]),
                ("Who wrote the screenplay for Intersteller?", "Interstellar", "P58", []),
                ("Who directed Schindlers List?", "Schindler's List", "P57", []),
                ("Who directed Forrst Gump?", "Forrest Gump", "P57", []),
                ("who directed 'the matrix'?", "The Matrix", "P57", [])]
    for input_, lb, prop, forbidden in controls:
        if lb not in POOL:
            continue
        ent, _ = POOL[lb]
        vals = answer_values(ent, prop)
        if not vals:
            continue
        bad = safe_forbidden(forbidden, vals, (ANSWER_T,))
        if bad:
            forbidden = []
        n += 1
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:{prop} ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        cases.append({"id": f"t4-typos-{n:03d}", "input": input_, "expected": vals,
                      "forbidden": forbidden,
                      "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                    "assert": "expected_in_rows"}})
    return cases


def prominence_candidates(mention: str) -> dict[str, str]:
    m = strip_article(mention)
    cands: dict[str, str] = {}
    for lb, ids in LEX.lbl2ent.items():
        s = strip_article(lb)
        if s == m or s.startswith(m + " "):
            for e in ids:
                cands.setdefault(e, lb)
    return cands


def resolve_mention(mention: str) -> str | None:
    cands = prominence_candidates(mention)
    films = [e for e in cands if LEX.is_film(e)]
    if not films:
        return None
    return rank_entities(films)[0]


def build_t5() -> list[dict]:
    cases, n = [], 0
    mentions = ["handmaiden", "matrix", "godfather", "inception", "interstellar", "terminator",
                "titanic", "prestige", "departed", "pianist", "dark knight",
                "shawshank redemption", "usual suspects", "silence of the lambs",
                "basic instinct", "dancer in the dark", "truman show"]
    mention_forbidden = {"godfather": ["Lal and Siddique"]}
    answer_mentions = []
    for m in mentions:
        ent = resolve_mention(m)
        if not ent:
            print(f"[t5] no film candidate for {m!r}; skipped from answer cases")
            continue
        vals = answer_values(ent, "P57")
        if not vals:
            continue
        answer_mentions.append((m, ent, vals))
    for i, (m, ent, vals) in enumerate(answer_mentions):
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        forbidden = mention_forbidden.get(m, [])
        bad = safe_forbidden(forbidden, vals, (ANSWER_T,))
        if bad:
            forbidden = []
        n += 1
        cases.append({"id": f"t5-partial-titles-{n:03d}", "input": f"who directed {m}?",
                      "expected": vals, "forbidden": forbidden,
                      "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                    "assert": "expected_in_rows"}})
        sval = answer_values(ent, "P58")
        if sval:
            n += 1
            scheck = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P58 ?x "
                      f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
            cases.append({"id": f"t5-partial-titles-{n:03d}",
                          "input": f"Who wrote the screenplay for {m}?", "expected": sval,
                          "forbidden": forbidden,
                          "grounding": {"entity": ent, "relation": "wdt:P58", "check": scheck,
                                        "assert": "expected_in_rows"}})
        else:
            n += 1
            cases.append({"id": f"t5-partial-titles-{n:03d}",
                          "input": f"Who was the director of {m}?", "expected": vals,
                          "forbidden": forbidden,
                          "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                        "assert": "expected_in_rows"}})
        if i < 10:
            n += 1
            cases.append({"id": f"t5-partial-titles-{n:03d}", "input": f"Who directed '{m}'?",
                          "expected": vals, "forbidden": forbidden,
                          "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                        "assert": "expected_in_rows"}})

    # clarification: no film candidate exists
    clarifies = []
    for cand in ("twilight zone", "simpsons", "the sopranos", "breaking bad", "frasier", "mad men",
                 "the wire", "friends"):
        if cand in LEX.lbl2ent:
            continue
        c = prominence_candidates(cand)
        if not c or any(LEX.is_film(e) for e in c):
            continue
        clarifies.append((cand, sorted(c, key=str.casefold)))
    for cand, ents in clarifies[:6]:
        values = " ".join(f"<{WD}{e}>" for e in ents[:10])
        check = (f"SELECT ?f WHERE {{ VALUES ?f {{ {values} }} {{ ?f wdt:P31 wd:Q11424 }} "
                 f"UNION {{ ?f wdt:P57 ?d }} }}")
        n += 1
        cases.append({"id": f"t5-partial-titles-{n:03d}", "input": f"Who directed {cand}?",
                      "expected": [NO_ENTITY_T], "forbidden": [ANSWER_T.strip()],
                      "grounding": {"entity": ents[0], "relation": "wdt:P57", "check": check,
                                    "assert": "no_film_rows"}})

    # controls: full-title forms
    for lb in ("The Handmaiden", "The Godfather", "The Terminator", "The Matrix", "The Departed",
               "The Prestige"):
        if lb not in POOL:
            continue
        ent, vals = POOL[lb]
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        n += 1
        cases.append({"id": f"t5-partial-titles-{n:03d}", "input": f"who directed {lb.casefold()}?",
                      "expected": vals, "forbidden": [],
                      "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                    "assert": "expected_in_rows"}})
    return cases


def build_d1() -> list[dict]:
    cases, n = [], 0
    films = [lb for lb in ("Inception", "The Godfather", "Interstellar", "Titanic", "Jaws",
                           "The Matrix", "The Dark Knight", "Parasite", "The Handmaiden",
                           "Whiplash", "Schindler's List", "The Prestige") if lb in POOL]
    humans = [h for h in ("Christopher Nolan", "Steven Spielberg", "Meryl Streep",
                          "Alfred Hitchcock", "Martin Scorsese", "Quentin Tarantino")
              if resolve_film(h) is None and LEX.lbl2ent.get(h.casefold())]

    def human_entity(h):
        return rank_entities(LEX.lbl2ent[h.casefold()])[0]

    def add(ent, prop, input_, count, variant="raw"):
        nonlocal n
        if count <= 0:
            return
        forbidden = [ANSWER_T.strip() + " 0"]
        expected = [str(count)]
        if safe_forbidden(forbidden, expected):
            raise AssertionError(f"D1 forbidden collides in {input_}")
        if variant == "films":
            if prop == "P57":
                check = (f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ ?x wdt:P57 <{WD}{ent}> . "
                         f"?x wdt:P31 wd:Q11424 }}")
            else:
                check = (f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ <{WD}{ent}> wdt:{prop} ?x . "
                         f"?x wdt:P31 wd:Q11424 }}")
        else:
            check = f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ <{WD}{ent}> wdt:{prop} ?x }}"
        n += 1
        cases.append({"id": f"d1-count-class-{n:03d}", "input": input_, "expected": expected,
                      "forbidden": forbidden,
                      "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                    "assert": "expected_count"}})

    for lb in films:
        ent, _ = POOL[lb]
        assigned = 0
        for prop, qs in (("P166", [f"How many awards did '{lb}' win?", f"How many awards has '{lb}' won?"]),
                         ("P161", [f"How many cast members does '{lb}' have?"]),
                         ("P136", [f"How many genres does '{lb}' have?"]),
                         ("P495", [f"How many countries of origin does '{lb}' have?"])):
            count = int(rows(f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ <{WD}{ent}> wdt:{prop} ?x }}")[0][0].value)
            if count and assigned < 4:
                add(ent, prop, qs[0], count)
                assigned += 1
    for h in humans:
        ent = human_entity(h)
        count = int(rows(f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ <{WD}{ent}> wdt:P166 ?x }}")[0][0].value)
        add(ent, "P166", f"How many awards has {h} won?", count)
        add(ent, "P166", f"How many awards did {h} receive?", count)
    for q, ok in top_directors(6):
        ent = q
        film_count = int(rows(f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ ?x wdt:P57 <{WD}{ent}> . "
                              f"?x wdt:P31 wd:Q11424 }}")[0][0].value)
        add(ent, "P57", f"How many films did {label(ent)} direct?", film_count, variant="films")
    return cases


def build_d2() -> list[dict]:
    cases, n = [], 0
    pairs = [("Jaws", "Inception"), ("The Godfather", "Inception"), ("Jaws", "Interstellar"),
             ("The Matrix", "The Godfather"), ("Up", "Jaws"), ("Titanic", "The Matrix"),
             ("Interstellar", "Batman Begins"), ("The Handmaiden", "Parasite"),
             ("Whiplash", "The Departed"), ("The Pianist", "Schindler's List"),
             ("Forrest Gump", "The Prestige"), ("The Terminator", "Jaws"),
             ("Oppenheimer", "Titanic")]
    forms = ["I love '{A}'. Who directed '{B}'?",
             "Who directed '{A}'? Who directed '{B}'?",
             "I love {A}. Who directed {B}?",
             "Someone told me {A} is great. Who directed {B}?"]
    for a, b in pairs:
        if a not in POOL or b not in POOL:
            continue
        ent_a, vals_a = POOL[a]
        ent_b, vals_b = POOL[b]
        forbidden = ["The factual answer is"] + vals_a + vals_b
        check = ("SELECT ?f ?x ?label WHERE { VALUES ?f "
                 f"{{ <{WD}{ent_a}> <{WD}{ent_b}> }} ?f wdt:P57 ?x OPTIONAL {{ ?x rdfs:label ?label }} }}")
        for form in forms:
            bad = safe_forbidden(forbidden, [NO_ENTITY_T])
            if bad:
                continue
            n += 1
            cases.append({"id": f"d2-multiple-mentions-{n:03d}",
                          "input": form.format(A=a, B=b), "expected": [NO_ENTITY_T],
                          "forbidden": forbidden,
                          "grounding": {"entity": ent_b, "entities": [ent_a, ent_b],
                                        "relation": "wdt:P57", "check": check,
                                        "assert": "forbidden_in_rows"}})
        p58a = answer_values(ent_a, "P58")
        if p58a:
            forbidden58 = ["The factual answer is"] + p58a + vals_b
            if not safe_forbidden(forbidden58, [NO_ENTITY_T]):
                n += 1
                cases.append({"id": f"d2-multiple-mentions-{n:03d}",
                              "input": f"Who wrote '{a}'? Also, who directed '{b}'?",
                              "expected": [NO_ENTITY_T], "forbidden": forbidden58,
                              "grounding": {"entity": ent_b, "entities": [ent_a, ent_b],
                                            "relation": "wdt:P58", "check": check,
                                            "assert": "forbidden_in_rows"}})
    return cases


def build_d3() -> list[dict]:
    cases, n = [], 0
    red_ctx = [", the first film in the trilogy", ", the latest film I watched",
               ", the last movie I saw", ", the newest one I own",
               ", the most recent film in the series", ", the first one he made"]
    green_ctx = [", my favourite film", ", which I recommend", ", the well-known one"]
    plan = [("Batman Begins", "P57", 4), ("The Godfather", "P58", 4), ("Inception", "P86", 4),
            ("Interstellar", "P57", 3), ("The Matrix", "P57", 2), ("Parasite", "P57", 2),
            ("Whiplash", "P57", 2), ("The Handmaiden", "P58", 2), ("The Departed", "P57", 2),
            ("Jaws", "P57", 2), ("The Dark Knight", "P57", 3), ("Schindler's List", "P57", 3),
            ("The Pianist", "P57", 2), ("The Prestige", "P57", 2)]
    for lb, prop, count in plan:
        if lb not in POOL:
            continue
        ent, _ = POOL[lb]
        vals = answer_values(ent, prop)
        if not vals:
            continue
        question = {"P57": "Who directed '{T}'", "P58": "Who wrote the screenplay of '{T}'",
                    "P86": "Who composed the music for '{T}'"}[prop]
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:{prop} ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        for ctx in red_ctx[:count]:
            n += 1
            cases.append({"id": f"d3-trailing-superlative-{n:03d}",
                          "input": question.format(T=lb) + ctx + "?", "expected": vals,
                          "forbidden": ["no information"],
                          "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                        "assert": "expected_in_rows"}})
        for ctx in green_ctx[:1]:
            n += 1
            cases.append({"id": f"d3-trailing-superlative-{n:03d}",
                          "input": question.format(T=lb) + ctx + "?", "expected": vals,
                          "forbidden": ["no information"],
                          "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                        "assert": "expected_in_rows"}})
    for lb in ("The Last Emperor", "The Last Samurai", "First Blood", "The Last of the Mohicans"):
        ent = resolve_film(lb)
        if not ent:
            continue
        vals = answer_values(ent, "P57")
        if not vals:
            continue
        n += 1
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        cases.append({"id": f"d3-trailing-superlative-{n:03d}", "input": f"Who directed '{lb}'?",
                      "expected": vals, "forbidden": [],
                      "grounding": {"entity": ent, "relation": "wdt:P57", "check": check,
                                    "assert": "expected_in_rows"}})
    return cases


def build_d5() -> list[dict]:
    cases, n = [], 0
    directors = [q for q, _c in top_directors(20)]
    films = [(lb, ent) for lb, (ent, _vals) in list(POOL.items())[:14]]
    for i, (lb, ent) in enumerate(films):
        rs = rows(f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                  f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        real_pairs = sorted(((r[1].value, r[0].value[len(WD):]) for r in rs if r[1]),
                            key=lambda p: p[0].casefold())
        if not real_pairs:
            continue
        real_names = [p[0] for p in real_pairs]
        real_qids = {p[1] for p in real_pairs}
        wrong_q = next((directors[(k + i) % len(directors)] for k in range(len(directors))
                        if directors[(k + i) % len(directors)] not in real_qids), None)
        if not wrong_q:
            continue
        wrong_name = label(wrong_q)
        forbidden = real_names + [wrong_name]

        def add(input_, expected, person, prop):
            nonlocal n
            bad = safe_forbidden(forbidden, [ANSWER_T + expected])
            if bad:
                return
            check = f"ASK {{ <{WD}{ent}> wdt:{prop} <{WD}{person}> }}"
            n += 1
            cases.append({"id": f"d5-yes-no-{n:03d}", "input": input_,
                          "expected": [ANSWER_T + expected], "forbidden": forbidden,
                          "grounding": {"entity": person, "entities": [ent, person],
                                        "relation": f"wdt:{prop}", "check": check,
                                        "assert": "ask_yesno"}})

        add(f"Did {real_names[0]} direct {lb}?", "Yes", real_pairs[0][1], "P57")
        add(f"Did {real_names[0]} direct '{lb}'?", "Yes", real_pairs[0][1], "P57")
        add(f"Did {wrong_name} direct '{lb}'?", "No", wrong_q, "P57")
        add(f"Was '{lb}' directed by {wrong_name}?", "No", wrong_q, "P57")

    # P58 pairs
    for lb, (ent, _vals) in list(POOL.items())[:6]:
        rs = rows(f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P58 ?x "
                  f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        pairs = sorted(((r[1].value, r[0].value[len(WD):]) for r in rs if r[1]),
                       key=lambda p: p[0].casefold())
        if not pairs:
            continue
        wname, wq = pairs[0]
        forbidden = [p[0] for p in pairs]
        if safe_forbidden(forbidden, [ANSWER_T + "Yes"]):
            continue
        n += 1
        check = f"ASK {{ <{WD}{ent}> wdt:P58 <{WD}{wq}> }}"
        cases.append({"id": f"d5-yes-no-{n:03d}", "input": f"Was '{lb}' written by {wname}?",
                      "expected": [ANSWER_T + "Yes"], "forbidden": forbidden,
                      "grounding": {"entity": wq, "entities": [ent, wq], "relation": "wdt:P58",
                                    "check": check, "assert": "ask_yesno"}})
    return cases


def build_d8() -> list[dict]:
    cases, n = [], 0
    entities = [(lb, ent) for lb, (ent, _v) in list(POOL.items())[:12]]
    for lb, ent in entities:
        p57 = answer_values(ent, "P57")
        if not p57:
            continue
        check57 = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P57 ?x "
                   f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        for form in (f"Who did the directing for '{lb}'?",
                     f"Who was at the helm of '{lb}'?",
                     f"Who is behind the camera on '{lb}'?"):
            n += 1
            cases.append({"id": f"d8-relation-paraphrases-{n:03d}", "input": form, "expected": p57,
                          "forbidden": [NO_RELATION_T],
                          "grounding": {"entity": ent, "relation": "wdt:P57", "check": check57,
                                        "assert": "expected_in_rows"}})
        p58 = answer_values(ent, "P58")
        if p58:
            scheck = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P58 ?x "
                      f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
            n += 1
            cases.append({"id": f"d8-relation-paraphrases-{n:03d}",
                          "input": f"Who did the writing for '{lb}'?", "expected": p58,
                          "forbidden": [NO_RELATION_T],
                          "grounding": {"entity": ent, "relation": "wdt:P58", "check": scheck,
                                        "assert": "expected_in_rows"}})
        p86 = answer_values(ent, "P86")
        if p86:
            mcheck = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:P86 ?x "
                      f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
            n += 1
            cases.append({"id": f"d8-relation-paraphrases-{n:03d}",
                          "input": f"Who did the composing for '{lb}'?", "expected": p86,
                          "forbidden": [NO_RELATION_T],
                          "grounding": {"entity": ent, "relation": "wdt:P86", "check": mcheck,
                                        "assert": "expected_in_rows"}})
    controls = [("Who is the director of '{T}'?", "P57"), ("Which filmmaker made '{T}'?", "P57"),
                ("By whom was '{T}' directed?", "P57"), ("Who wrote the screenplay for '{T}'?", "P58"),
                ("Who composed the music for '{T}'?", "P86")]
    for i, (form, prop) in enumerate(controls * 3):
        lb = ["Inception", "The Godfather", "Interstellar", "The Matrix", "Jaws",
              "The Handmaiden", "Parasite", "Whiplash", "The Departed", "The Pianist"][i % 10]
        if lb not in POOL:
            continue
        ent, _ = POOL[lb]
        vals = answer_values(ent, prop)
        if not vals:
            continue
        check = (f"SELECT DISTINCT ?x ?label WHERE {{ <{WD}{ent}> wdt:{prop} ?x "
                 f"OPTIONAL {{ ?x rdfs:label ?label }} }}")
        n += 1
        cases.append({"id": f"d8-relation-paraphrases-{n:03d}", "input": form.format(T=lb),
                      "expected": vals, "forbidden": [NO_RELATION_T],
                      "grounding": {"entity": ent, "relation": f"wdt:{prop}", "check": check,
                                    "assert": "expected_in_rows"}})
        if n >= 74:
            break
    return cases


# --------------------------------------------------------------------------------------------------
FAMILIES: dict[str, list[str]] = {}
for _lb, _ids in LEX.lbl2ent.items():
    FAMILIES.setdefault(strip_article(_lb), []).extend(_ids)
SEARCH_SPACE = sorted(set(list(LEX.lbl2ent) + list(FAMILIES)))
ALL_LABELS = list(LEX.lbl2ent)


def dedupe(cases: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in cases:
        if c["input"] in seen:
            continue
        seen.add(c["input"])
        out.append(c)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    builders = {
        "t1-negation": build_t1,
        "t2-subvention": build_t2,
        "t3-quote-shapes": build_t3,
        "t4-typos": build_t4,
        "t5-partial-titles": build_t5,
        "d1-count-class": build_d1,
        "d2-multiple-mentions": build_d2,
        "d3-trailing-superlative": build_d3,
        "d5-yes-no": build_d5,
        "d8-relation-paraphrases": build_d8,
    }
    summary = []
    for name, builder in builders.items():
        cases = dedupe(builder())
        path = OUT / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for c in cases:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
        ents, rels = set(), set()
        for c in cases:
            g = c.get("grounding") or {}
            if g.get("entity"):
                ents.add(g["entity"])
            for e in g.get("entities", []):
                ents.add(e)
            if g.get("relation"):
                rels.add(g["relation"])
        summary.append({"file": path.name, "cases": len(cases), "entities": len(ents),
                        "relations": sorted(rels)})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
