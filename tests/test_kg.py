import time

import pytest

from agent.kg import BUILD_MARKER, KnowledgeGraph, QueryError, QueryTimeout, SelectResult, Term, build_store, store_is_built
from conftest import MINI_GRAPH


def test_select_with_default_prefixes(kg):
    result = kg.query('SELECT ?d WHERE { ?m rdfs:label "Arrival" . ?m wdt:P577 ?d }')
    assert isinstance(result, SelectResult)
    assert result.variables == ["d"]
    (term,), = result.rows
    assert term.kind == "literal"
    assert term.value == "2016-11-10"
    assert term.datatype.endswith("#date")


def test_explicit_prefixes_still_work(kg):
    result = kg.query('PREFIX wd: <http://www.wikidata.org/entity/> SELECT ?l WHERE { wd:Q47703 rdfs:label ?l }')
    assert result.rows == [(Term("literal", "The Godfather", "http://www.w3.org/2001/XMLSchema#string"),)]


def test_iri_and_language_terms(kg):
    result = kg.query('SELECT ?m ?t WHERE { ?m ddis:tag ?t } ORDER BY ?t LIMIT 1')
    movie, tag = result.rows[0]
    assert movie == Term("iri", "http://www.wikidata.org/entity/Q16635326")
    assert (tag.value, tag.lang) == ("cruelty", "en")


def test_unbound_optional_is_none(kg):
    result = kg.query('SELECT ?m ?d WHERE { ?m rdfs:label "Ex Machina" OPTIONAL { ?m wdt:P577 ?d } }')
    assert result.rows[0][1] is None


def test_ask(kg):
    assert kg.query("ASK { wd:Q47703 wdt:P57 wd:Q56094 }") is True
    assert kg.query("ASK { wd:Q47703 wdt:P57 wd:Q1 }") is False


def test_row_cap_marks_truncation(kg):
    result = kg.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }", max_rows=3)
    assert len(result.rows) == 3
    assert result.truncated


def test_invalid_query_raises_query_error(kg):
    with pytest.raises(QueryError):
        kg.query("SELECT ?x WHERE { ?x ?y }")


def test_slow_query_raises_timeout(kg, monkeypatch):
    def slow(sparql, max_rows):
        time.sleep(1)
        return True

    monkeypatch.setattr(kg, "_execute", slow)
    start = time.perf_counter()
    with pytest.raises(QueryTimeout):
        kg.query("ASK {}", timeout=0.1)
    assert time.perf_counter() - start < 0.5


def test_store_is_reused_after_first_build(tmp_path):
    store = tmp_path / "store"
    build_store(MINI_GRAPH, store)
    marker = store / BUILD_MARKER
    built_at = marker.stat().st_mtime_ns
    graph = KnowledgeGraph.open(MINI_GRAPH, store)
    assert graph.query("ASK { wd:Q47703 ?p ?o }") is True
    assert marker.stat().st_mtime_ns == built_at
    graph.close()


def test_leftover_partial_build_is_replaced(tmp_path):
    partial = tmp_path / "store.partial"
    partial.mkdir()
    (partial / "garbage").write_text("x")
    build_store(MINI_GRAPH, tmp_path / "store")
    assert store_is_built(tmp_path / "store")
    assert not partial.exists()
