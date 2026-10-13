"""
SPARQL templates for single-hop questions.

direction "out": the entity is the subject, the answer is the object ("Who directed Alien?")
direction "in":  the entity is the object, the answer is the subject ("Which movies did Ridley Scott direct?")
"""

WD = "http://www.wikidata.org/entity/"
RELEASE_DATE = "http://www.wikidata.org/prop/direct/P577"
LIMIT = 200


def _triple(entity: str, predicate: str, direction: str) -> str:
    if direction == "out":
        return f"<{WD}{entity}> <{predicate}> ?x ."
    return f"?x <{predicate}> <{WD}{entity}> ."


def has_facts(entity: str, predicate: str, direction: str) -> str:
    return f"ASK {{ {_triple(entity, predicate, direction)} }}"


def degree(entity: str) -> str:
    return f"SELECT (COUNT(*) AS ?n) WHERE {{ <{WD}{entity}> ?p ?o }}"


def lookup(entity: str, predicate: str, direction: str) -> str:
    return (f"SELECT DISTINCT ?x ?label WHERE {{ {_triple(entity, predicate, direction)} "
            f"OPTIONAL {{ ?x rdfs:label ?label }} }} LIMIT {LIMIT}")


def count(entity: str, predicate: str, direction: str) -> str:
    return f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ {_triple(entity, predicate, direction)} ?x wdt:P31 wd:Q11424 }}"


def superlative(entity: str, predicate: str, direction: str, order: str) -> str:
    """The film with the earliest ("ASC") or latest ("DESC") release date."""
    aggregate = "MIN" if order == "ASC" else "MAX"
    return (f"SELECT ?x ?label ({aggregate}(?d) AS ?date) WHERE {{ {_triple(entity, predicate, direction)} "
            f"?x wdt:P31 wd:Q11424 ; <{RELEASE_DATE}> ?d . OPTIONAL {{ ?x rdfs:label ?label }} }} "
            f"GROUP BY ?x ?label ORDER BY {order}(?date) LIMIT 1")
