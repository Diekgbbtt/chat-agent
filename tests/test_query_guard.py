"""Read-only query enforcement and labelled row observations."""

import pytest

from agent.kg import SelectResult, Term
from agent.lexicon import Lexicon
from agent.tools.sparql import QueryGuard, QueryRejected, ResultFormatter, RunSparqlTool


def test_agent_mode_accepts_select_and_ask():
    guard = QueryGuard()
    assert guard.validate("SELECT ?s WHERE { ?s ?p ?o }").startswith("SELECT")
    assert guard.validate("ASK { wd:Q1 wdt:P31 wd:Q11424 }").startswith("ASK")


def test_prefix_and_base_declarations_are_accepted():
    query = ("PREFIX wd: <http://www.wikidata.org/entity/>\n"
             "SELECT ?s WHERE { ?s ?p ?o }")
    assert QueryGuard().validate(query).startswith("PREFIX")


@pytest.mark.parametrize("clause", ["INSERT DATA", "DELETE WHERE", "DROP GRAPH", "CLEAR ALL",
                                    "LOAD <file>", "CREATE GRAPH", "ADD", "MOVE", "COPY"])
def test_writes_are_rejected(clause):
    with pytest.raises(QueryRejected):
        QueryGuard().validate(f"{clause} {{ <a> <b> <c> }}")


@pytest.mark.parametrize("clause", ["SERVICE <http://x>", "FROM <http://x>", "WITH <http://x>"])
def test_network_and_dataset_clauses_are_rejected(clause):
    with pytest.raises(QueryRejected):
        QueryGuard().validate(f"SELECT ?s {clause} WHERE {{ ?s ?p ?o }}")


def test_banned_words_inside_strings_and_comments_are_ignored():
    query = ('# SERVICE FROM\nSELECT ?s WHERE { ?s rdfs:label "DROP TABLE" }')
    assert QueryGuard().validate(query)


def test_agent_mode_rejects_construct_and_describe():
    for query in ("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "DESCRIBE <http://x>"):
        with pytest.raises(QueryRejected):
            QueryGuard().validate(query)


def test_raw_mode_allows_construct_and_describe():
    for query in ("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "DESCRIBE <http://x>"):
        assert QueryGuard().validate(query, mode="raw")


def test_query_length_is_capped():
    with pytest.raises(QueryRejected):
        QueryGuard().validate("SELECT ?s WHERE { ?s ?p ?o } # " + "x" * 4_000)


def test_empty_query_is_rejected():
    with pytest.raises(QueryRejected):
        QueryGuard().validate("   ")


def test_formatter_resolves_entity_and_property_labels(kg):
    lexicon = Lexicon(kg)
    result = kg.query("SELECT ?m ?d WHERE { ?m wdt:P57 ?d } ORDER BY ?m LIMIT 1")
    observation = ResultFormatter(lexicon).format(result)

    assert observation.error is None
    assert observation.truncated is False
    assert observation.rows[0]["m"] == "The Godfather"
    assert observation.rows[0]["d"] == "Francis Ford Coppola"
    assert observation.rows[0]["row_id"] == "r0"


def test_formatter_keeps_literals_and_unbound_values():
    lexicon = type("L", (), {"ent2lbl": {}, "prop2lbl": {}})()
    result = SelectResult(["date", "missing"], [
        (Term("literal", "2016-11-10T00:00:00Z"), None),
    ])
    row = ResultFormatter(lexicon).format(result).rows[0]

    assert row["date"] == "2016-11-10"
    assert row["missing"] is None


def test_formatter_formats_ask_as_one_row():
    observation = ResultFormatter(type("L", (), {"ent2lbl": {}, "prop2lbl": {}})()).format(True)

    assert observation.rows == ({"row_id": "r0", "boolean": True},)


def test_formatter_truncates_the_observation():
    lexicon = type("L", (), {"ent2lbl": {}, "prop2lbl": {}})()
    result = SelectResult(["value"], [(Term("literal", "x" * 50),) for _ in range(20)])

    observation = ResultFormatter(lexicon, max_chars=200).format(result)

    assert observation.truncated is True
    assert len(str(observation.rows)) < 400


def test_run_tool_returns_rows(kg):
    lexicon = Lexicon(kg)
    observation = RunSparqlTool(kg, lexicon).run(
        "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }")

    assert observation.error is None
    assert observation.rows[0]["d"] == "Francis Ford Coppola"


def test_run_tool_turns_bad_queries_into_observations(kg):
    observation = RunSparqlTool(kg, Lexicon(kg)).run("INSERT DATA { <a> <b> <c> }")

    assert observation.error
    assert observation.rows == ()
