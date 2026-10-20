"""
Knowledge graph access through an on-disk pyoxigraph store.

The store is built once from graph.nt and then opened read-only in milliseconds.
pyoxigraph runs queries outside the GIL, so queries from several chatrooms run in parallel.
"""

import errno
import hashlib
import json
import logging
import platform
import shutil
import sys
import tempfile
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
MARKER_VERSION = 1
STORE_FORMAT = "pyoxigraph-rocksdb"


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


def _resolved(path) -> Path:
    """Follow symlinks, including dangling ones, without requiring the target to exist."""
    return Path(path).expanduser().resolve(strict=False)


def _fallback_store_path(store_path: Path) -> Path:
    """A per-store temporary location for read-only submission directories."""
    digest = hashlib.sha256(str(store_path).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "atai-agent-store" / digest / "kg_store"


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_fingerprint() -> dict:
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pyoxigraph": getattr(ox, "__version__", "unknown"),
        "platform": platform.system(),
        "machine": platform.machine(),
        "store_format": STORE_FORMAT,
    }


def _graph_fingerprint(graph_path) -> dict:
    path = Path(graph_path)
    stat = path.stat()
    return {"path": str(path.expanduser().resolve(strict=False)),
            "size": stat.st_size, "sha256": _sha256(path)}


def _marker_matches_graph(marker: dict, graph_path) -> bool:
    graph = marker.get("graph")
    if not isinstance(graph, dict):
        return False
    try:
        actual = _graph_fingerprint(graph_path)
    except OSError:
        return False
    return graph.get("size") == actual["size"] and graph.get("sha256") == actual["sha256"]


def store_is_built(store_path, graph_path=None) -> bool:
    """Validate marker, graph content, and runtime, not the store's absolute location."""
    store = _resolved(store_path)
    try:
        marker = json.loads((store / BUILD_MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    if not isinstance(marker, dict):
        return False
    if marker.get("marker_version") != MARKER_VERSION:
        return False
    if marker.get("runtime") != _runtime_fingerprint():
        return False
    if graph_path is not None and not _marker_matches_graph(marker, graph_path):
        return False
    return True


def build_store(graph_path, store_path, force: bool = False) -> None:
    """Loads graph.nt into a store; builds into `<store>.partial` and renames when done."""
    store_path = _resolved(store_path)
    graph_path = Path(graph_path).expanduser().resolve(strict=False)
    if store_is_built(store_path, graph_path) and not force:
        return
    store_path.parent.mkdir(parents=True, exist_ok=True)
    partial = store_path.with_name(store_path.name + ".partial")
    _remove_path(partial)
    log.info("Building store from %s ...", graph_path)
    start = time.time()
    store = ox.Store(str(partial))
    store.bulk_load(path=str(graph_path), format=ox.RdfFormat.N_TRIPLES, lenient=True)
    store.flush()
    store.optimize()
    del store
    marker = {"marker_version": MARKER_VERSION, "graph": _graph_fingerprint(graph_path),
              "runtime": _runtime_fingerprint()}
    (partial / BUILD_MARKER).write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    _remove_path(store_path)
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
        store_path = _resolved(store_path)
        try:
            build_store(graph_path, store_path)
        except OSError as exc:
            writable_errors = (errno.EACCES, errno.EPERM, errno.EROFS)
            message = str(exc).lower()
            denied = ("permission denied" in message or "read-only file system" in message
                      or "operation not permitted" in message)
            if not isinstance(exc, PermissionError) and exc.errno not in writable_errors and not denied:
                raise
            fallback = _fallback_store_path(store_path)
            log.warning("Store path %s is not writable; using %s", store_path, fallback)
            store_path = _resolved(fallback)
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
