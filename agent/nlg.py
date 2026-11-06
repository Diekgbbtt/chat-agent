"""Turning graph values into text."""

from typing import Iterable, List, Optional

from agent.kg import Term

SHORT_PREFIXES = {"http://www.wikidata.org/entity/": "", "http://www.wikidata.org/prop/direct/": "",
                  "http://ddis.ch/atai/": "ddis:"}
ANSWER_LIMIT = 50


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
    """["a"] -> "a", ["a", "b"] -> "a and b", ["a", "b", "c"] -> "a and b and c"."""
    return " and ".join(items)


def answer(values: List[str], limit: int = ANSWER_LIMIT) -> str:
    """Serializes at most `limit` values; the caller orders them by relevance."""
    return f"The factual answer is: {join_and(values[:limit])}"


def no_entity() -> str:
    return "I'm not sure which movie or person you mean. Could you put the title in quotes, e.g. Who directed 'Jaws'?"


def no_relation(entity: str) -> str:
    return f"I found {entity}, but I'm not sure what you'd like to know. You can ask about its director, cast, genre, ..."


def no_facts(relation: str, entity: str) -> str:
    return f"Sorry, my knowledge graph has no information about the {relation} of {entity}."


def no_match() -> str:
    return "Sorry, my knowledge graph has no matching information."


def unknown_entity(name: str) -> str:
    return f"Sorry, I couldn't find {name} in my knowledge graph."


def no_property() -> str:
    return "Sorry, my knowledge graph doesn't have that kind of information."


def capabilities() -> str:
    return "Hi! I can answer questions about movies, e.g. who directed or starred in a film, or when it came out."


def not_understood() -> str:
    return "Sorry, I didn't quite get that. Could you rephrase your question?"
