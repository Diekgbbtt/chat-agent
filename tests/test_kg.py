import hashlib
import json
import shutil
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


def test_marker_records_graph_hash_and_runtime(tmp_path):
    store = tmp_path / "store"
    build_store(MINI_GRAPH, store)
    marker = json.loads((store / BUILD_MARKER).read_text(encoding="utf-8"))
    assert marker["graph"]["sha256"] == hashlib.sha256(MINI_GRAPH.read_bytes()).hexdigest()
    assert marker["runtime"]["pyoxigraph"]
    assert marker["runtime"]["platform"]
    assert marker["runtime"]["machine"]
    assert store_is_built(store, MINI_GRAPH)


def test_store_survives_a_move_without_rebuild(tmp_path):
    store = tmp_path / "store"
    moved = tmp_path / "moved-store"
    build_store(MINI_GRAPH, store)
    built_at = (store / BUILD_MARKER).stat().st_mtime_ns
    store.rename(moved)
    assert store_is_built(moved, MINI_GRAPH)
    graph = KnowledgeGraph.open(MINI_GRAPH, moved)
    try:
        assert graph.query("ASK { wd:Q47703 ?p ?o }") is True
    finally:
        graph.close()
    assert (moved / BUILD_MARKER).stat().st_mtime_ns == built_at


def test_changed_graph_invalidates_the_store(tmp_path):
    store = tmp_path / "store"
    changed = tmp_path / "changed.nt"
    changed.write_text(MINI_GRAPH.read_text(encoding="utf-8")
                       + '\n<http://example.org/s> <http://example.org/p> "v" .\n',
                       encoding="utf-8")
    build_store(MINI_GRAPH, store)
    before = json.loads((store / BUILD_MARKER).read_text(encoding="utf-8"))["graph"]["sha256"]
    build_store(changed, store)
    after = json.loads((store / BUILD_MARKER).read_text(encoding="utf-8"))["graph"]["sha256"]
    assert before != after
    assert store_is_built(store, changed)


def test_legacy_or_incompatible_marker_invalidates_the_store(tmp_path):
    store = tmp_path / "store"
    build_store(MINI_GRAPH, store)
    marker_path = store / BUILD_MARKER
    marker_path.write_text("/old/absolute/path", encoding="utf-8")
    assert not store_is_built(store, MINI_GRAPH)
    build_store(MINI_GRAPH, store)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["runtime"]["pyoxigraph"] = "0.0.0"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    assert not store_is_built(store, MINI_GRAPH)
    build_store(MINI_GRAPH, store)
    assert store_is_built(store, MINI_GRAPH)


def test_dangling_store_symlink_is_rebuilt(tmp_path):
    target = tmp_path / "target-store"
    link = tmp_path / "store-link"
    build_store(MINI_GRAPH, target)
    link.symlink_to(target, target_is_directory=True)
    shutil.rmtree(target)
    assert link.is_symlink()
    build_store(MINI_GRAPH, link)
    assert link.exists()
    assert store_is_built(link, MINI_GRAPH)


def test_read_only_store_parent_falls_back_to_a_writable_store(tmp_path, monkeypatch):
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(0o500)
    fallback = tmp_path / "fallback-store"
    monkeypatch.setattr("agent.kg._fallback_store_path", lambda _: fallback)
    try:
        graph = KnowledgeGraph.open(MINI_GRAPH, readonly / "store")
        try:
            assert graph.query("ASK { wd:Q47703 ?p ?o }") is True
        finally:
            graph.close()
        assert store_is_built(fallback, MINI_GRAPH)
    finally:
        readonly.chmod(0o700)
