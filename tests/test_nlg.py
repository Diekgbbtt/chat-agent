from agent.kg import Term
from agent.nlg import answer, format_term, join_and, short_iri


def test_join_and():
    assert join_and([]) == ""
    assert join_and(["A"]) == "A"
    assert join_and(["A", "B"]) == "A and B"
    assert join_and(["A", "B", "C"]) == "A, B, and C"
    assert answer(["A", "B"]) == "The factual answer is: A and B"


def test_short_iri():
    assert short_iri("http://www.wikidata.org/entity/Q47703") == "Q47703"
    assert short_iri("http://ddis.ch/atai/tag") == "ddis:tag"
    assert short_iri("http://schema.org/description") == "http://schema.org/description"


def test_format_term():
    assert format_term(None) == "-"
    assert format_term(Term("iri", "http://www.wikidata.org/entity/Q1")) == "Q1"
    assert format_term(Term("literal", "2016-01-23T00:00:00Z")) == "2016-01-23"
