"""
Knowledge graph access through an on-disk pyoxigraph store.

The store is built once from graph.nt and then opened read-only in milliseconds.
pyoxigraph runs queries outside the GIL, so queries from several chatrooms run in parallel.
"""

import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pyoxigraph as ox

log = logging.getLogger("agent.kg")

PREFIXES = {
    "ddis": "http://ddis.ch/atai/",
    "wd": "http://www.wikidata.org/entity/",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "schema": "http://schema.org/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
BUILD_MARKER = ".build-complete"


class QueryError(Exception):
    pass


class QueryTimeout(Exception):
    pass


@dataclass(frozen=True)
class Term:
    kind: str  # "iri", "literal" or "bnode"
    value: str
    datatype: Optional[str] = None
    lang: Optional[str] = None


@dataclass
class SelectResult:
    variables: List[str]
    rows: List[Tuple[Optional[Term], ...]]
    truncated: bool = False


QueryResult = Union[SelectResult, bool]


def _term(t) -> Optional[Term]:
    if t is None:
        return None
    if isinstance(t, ox.NamedNode):
        return Term("iri", t.value)
    if isinstance(t, ox.Literal):
        return Term("literal", t.value, t.datatype.value if t.datatype else None, t.language)
    return Term("bnode", str(t.value))


def store_is_built(store_path) -> bool:
    return (Path(store_path) / BUILD_MARKER).exists()


def build_store(graph_path, store_path, force: bool = False) -> None:
    """Loads graph.nt into a store; builds into `<store>.partial` and renames when done."""
    store_path = Path(store_path)
    if store_is_built(store_path) and not force:
        return
    partial = store_path.with_name(store_path.name + ".partial")
    shutil.rmtree(partial, ignore_errors=True)
    log.info("Building store from %s ...", graph_path)
    start = time.time()
    store = ox.Store(str(partial))
    store.bulk_load(path=str(graph_path), format=ox.RdfFormat.N_TRIPLES, lenient=True)
    store.flush()
    store.optimize()
    del store
    (partial / BUILD_MARKER).write_text(str(graph_path), encoding="utf-8")
    shutil.rmtree(store_path, ignore_errors=True)
    partial.rename(store_path)
    log.info("Store built in %.0f s", time.time() - start)


class KnowledgeGraph:
    def __init__(self, store, query_timeout_s: float = 20.0, max_fetch_rows: int = 10_000, workers: int = 8):
        self.store = store
        self.query_timeout_s = query_timeout_s
        self.max_fetch_rows = max_fetch_rows
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="kg")

    @classmethod
    def open(cls, graph_path, store_path, **kwargs) -> "KnowledgeGraph":
        build_store(graph_path, store_path)
        return cls(ox.Store.read_only(str(store_path)), **kwargs)

    def _execute(self, sparql: str, max_rows: int) -> QueryResult:
        try:
            result = self.store.query(sparql, prefixes=PREFIXES)
        except SyntaxError as e:
            raise QueryError(str(e)) from e
        if isinstance(result, ox.QueryBoolean):
            return bool(result)
        if isinstance(result, ox.QuerySolutions):
            variables = [v.value for v in result.variables]
            rows = list(islice(result, max_rows + 1))
            return SelectResult(variables, [tuple(_term(r[v]) for v in variables) for r in rows[:max_rows]],
                                truncated=len(rows) > max_rows)
        triples = list(islice(result, max_rows + 1))  # CONSTRUCT / DESCRIBE
        return SelectResult(["subject", "predicate", "object"],
                            [(_term(t.subject), _term(t.predicate), _term(t.object)) for t in triples[:max_rows]],
                            truncated=len(triples) > max_rows)

    def query(self, sparql: str, timeout: Optional[float] = None, max_rows: Optional[int] = None) -> QueryResult:
        """Runs a query with the default prefixes; raises QueryError or QueryTimeout.

        A timed-out query keeps running in the background (Python can't cancel it).
        """
        timeout = self.query_timeout_s if timeout is None else timeout
        future = self._pool.submit(self._execute, sparql, max_rows or self.max_fetch_rows)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as e:
            raise QueryTimeout(f"query exceeded {timeout:.0f} s") from e

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
