"""Turning graph values into text."""

from typing import Iterable, List, Optional

from agent.kg import Term

SHORT_PREFIXES = {"http://www.wikidata.org/entity/": "", "http://www.wikidata.org/prop/direct/": "",
                  "http://ddis.ch/atai/": "ddis:"}


def short_iri(iri: str) -> str:
    for prefix, short in SHORT_PREFIXES.items():
        if iri.startswith(prefix):
            return short + iri[len(prefix):]
    return iri


def format_term(term: Optional[Term]) -> str:
    if term is None:
        return "-"
    if term.kind == "iri":
        return short_iri(term.value)
    return term.value.removesuffix("T00:00:00Z")


def join_and(items: Iterable[str]) -> str:
    """["a"] -> "a", ["a", "b"] -> "a and b", ["a", "b", "c"] -> "a, b, and c"."""
    items = list(items)
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def answer(values: List[str]) -> str:
    return f"The factual answer is: {join_and(values)}"


def no_entity() -> str:
    return "I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"


def no_relation(entity: str) -> str:
    return f"I found {entity}, but I'm not sure what you'd like to know. You can ask about its director, cast, genre, ..."


def no_facts(relation: str, entity: str) -> str:
    return f"Sorry, my knowledge graph has no information about the {relation} of {entity}."
