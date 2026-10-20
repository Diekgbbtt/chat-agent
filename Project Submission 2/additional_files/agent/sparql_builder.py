"""
SPARQL templates for single-hop questions.

direction "out": the entity is the subject, the answer is the object ("Who directed Alien?")
direction "in":  the entity is the object, the answer is the subject ("Which movies did Ridley Scott direct?")
"""

from typing import Optional, Sequence

WD = "http://www.wikidata.org/entity/"
RELEASE_DATE = "http://www.wikidata.org/prop/direct/P577"
DIRECTOR = "http://www.wikidata.org/prop/direct/P57"
SCREENWRITER = "http://www.wikidata.org/prop/direct/P58"
COMPOSER = "http://www.wikidata.org/prop/direct/P86"
FILM_CREDITS = {DIRECTOR, SCREENWRITER, COMPOSER}
LIMIT = 200
COMPLEMENT_FETCH_LIMIT = 1_000


def _triple(entity: str, predicate: str, direction: str) -> str:
    if direction == "out":
        return f"<{WD}{entity}> <{predicate}> ?x ."
    return f"?x <{predicate}> <{WD}{entity}> ."


def has_facts(entity: str, predicate: str, direction: str) -> str:
    return f"ASK {{ {_triple(entity, predicate, direction)} }}"


def degree(entity: str) -> str:
    return f"SELECT (COUNT(*) AS ?n) WHERE {{ <{WD}{entity}> ?p ?o }}"


def degrees(entities: Sequence[str]) -> str:
    """Graph degree for a bounded candidate set, in one query."""
    values = " ".join(f"<{WD}{entity}>" for entity in entities)
    return (f"SELECT ?x (COUNT(*) AS ?n) WHERE {{ VALUES ?x {{ {values} }} "
            f"?x ?p ?o }} GROUP BY ?x")


def lookup(entity: str, predicate: str, direction: str) -> str:
    return (f"SELECT DISTINCT ?x ?label WHERE {{ {_triple(entity, predicate, direction)} "
            f"OPTIONAL {{ ?x rdfs:label ?label }} }} LIMIT {LIMIT}")


def count(entity: str, predicate: str, direction: str) -> str:
    """Count the relation values; "how many films did X direct" only counts films."""
    film_filter = " ?x wdt:P31 wd:Q11424" if direction == "in" and predicate in FILM_CREDITS else ""
    return (f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ {_triple(entity, predicate, direction)}"
            f"{film_filter} }}")


def _complement_where(entity: str, predicate: str, direction: str, universe: Optional[str],
                      others: Sequence[str]) -> str:
    """The graph pattern of the complement; shared by the list and the count so they never disagree."""
    if direction == "in":
        return f"?x wdt:P31 wd:Q11424 . FILTER NOT EXISTS {{ ?x <{predicate}> <{WD}{entity}> }}"
    if universe == "actor" and predicate == DIRECTOR:
        base = "?f wdt:P161 ?x . ?x wdt:P31 wd:Q5 ."
    else:
        base = f"?f <{predicate}> ?x ."
    filters = " ".join(f"FILTER NOT EXISTS {{ <{WD}{film}> <{predicate}> ?x }}"
                       for film in (entity, *others))
    return f"{base} {filters}"


def complement(entity: str, predicate: str, direction: str, universe: Optional[str] = None,
               others: Sequence[str] = ()) -> str:
    """The relation's domain minus the values linked to the entity ("movies not directed by X").

    universe "actor" scopes person answers to cast members (P161), the default is everyone who holds
    the credit; `others` lists further films whose holders the person answers must exclude too.
    """
    where = _complement_where(entity, predicate, direction, universe, others)
    select = "?x ?label" if direction == "in" else "DISTINCT ?x ?label"
    return (f"SELECT {select} WHERE {{ {where} "
            f"OPTIONAL {{ ?x rdfs:label ?label }} }} LIMIT {COMPLEMENT_FETCH_LIMIT}")


def complement_count(entity: str, predicate: str, direction: str, universe: Optional[str] = None,
                     others: Sequence[str] = ()) -> str:
    """Size of the complement ("how many movies did X not direct"); unbounded, unlike the list."""
    where = _complement_where(entity, predicate, direction, universe, others)
    return f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ {where} }}"


def claim(film: str, predicate: str, person: str) -> str:
    """ASK whether the film has the credit to the person ("Did X direct Y?")."""
    return f"ASK {{ <{WD}{film}> <{predicate}> <{WD}{person}> }}"


def superlative(entity: str, predicate: str, direction: str, order: str) -> str:
    """The film with the earliest ("ASC") or latest ("DESC") release date."""
    aggregate = "MIN" if order == "ASC" else "MAX"
    return (f"SELECT ?x ?label ({aggregate}(?d) AS ?date) WHERE {{ {_triple(entity, predicate, direction)} "
            f"?x wdt:P31 wd:Q11424 ; <{RELEASE_DATE}> ?d . OPTIONAL {{ ?x rdfs:label ?label }} }} "
            f"GROUP BY ?x ?label ORDER BY {order}(?date) LIMIT 1")
