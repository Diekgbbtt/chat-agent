import pytest

from agent.core import Trace
from agent.handlers.sparql import SparqlHandler, clean_query, looks_like_sparql

PREFIXES = """PREFIX ddis: <http://ddis.ch/atai/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


@pytest.mark.parametrize("text", [
    'SELECT ?x WHERE { ?x ?p ?o }',
    'select ?x where { ?x ?p ?o }',
    PREFIXES + 'SELECT ?x WHERE { ?x ?p ?o }',
    "'''\n" + PREFIXES + "SELECT ?x WHERE { ?x ?p ?o }\n'''",
    "```sparql\nSELECT ?x WHERE { ?x ?p ?o }\n```",
    "'''\nASK { ?x ?p ?o }\n‘’’",
    "# cast of a movie\nSELECT ?x WHERE { ?x ?p ?o }",
    'PREFIX wd: <http://www.wikidata.org/entity/> SELECT ?x WHERE { ?x ?p ?o }',
])
def test_recognises_sparql(text):
    assert looks_like_sparql(text)


@pytest.mark.parametrize("text", [
    "Who directed 'The Godfather'?",
    "Select a movie where Tom Hanks plays a pilot",
    "Where can I select which movie to watch?",
    "",
])
def test_rejects_natural_language(text):
    assert not looks_like_sparql(text)


def test_clean_query_strips_fences():
    assert clean_query("'''\nSELECT ?x WHERE {}\n'''") == "SELECT ?x WHERE {}"
    assert clean_query("```sparql\nASK {}\n```") == "ASK {}"


def answer(kg, query):
    return SparqlHandler(kg).handle(query, None, Trace())


def test_atomic_cafe_example(kg):
    reply = answer(kg, "'''\n" + PREFIXES + """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT ?answerLabel ?answerItem WHERE {
?movieItem rdfs:label "The Atomic Cafe" .
?movieItem wdt:P161 ?answerItem .
?answerItem rdfs:label ?answerLabel .
}
'''""")
    for name, qid in (("Lloyd Bentsen", "Q455401"), ("Harry S. Truman", "Q11613"), ("Paul Tibbets", "Q294555")):
        assert f"{name} | {qid}" in reply


def test_count_and_dates(kg):
    assert answer(kg, 'SELECT (COUNT(*) AS ?n) WHERE { ?m ddis:tag ?t }') == "3"
    assert answer(kg, 'SELECT ?d WHERE { wd:Q20382729 wdt:P577 ?d }') == "2016-11-10"


def test_ask_and_empty(kg):
    assert answer(kg, "ASK { wd:Q47703 wdt:P57 wd:Q56094 }") == "Yes."
    assert "no results" in answer(kg, 'SELECT ?x WHERE { ?x rdfs:label "nope" }')


def test_invalid_query_message(kg):
    assert "invalid" in answer(kg, "SELECT ?x WHERE { ?x ?y }")


def test_long_results_are_cut(kg):
    reply = answer(kg, "SELECT ?a ?b WHERE { ?a ?p ?o . ?b ?q ?r }")  # ~500 rows
    assert len(reply.splitlines()) == 26
    assert reply.splitlines()[-1].startswith("... and")
