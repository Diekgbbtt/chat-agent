"""
Knowledge graph access: loads graph.nt once and runs SPARQL queries on it.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

import rdflib

log = logging.getLogger("kg")

GRAPH_PATH = "/space_mounts/atai-hs26/dataset/graph.nt"
QUERY_TIMEOUT_S = 30
MAX_ROWS = 25

PREFIXES = """
PREFIX ddis: <http://ddis.ch/atai/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


class KnowledgeGraph:
    def __init__(self, path: str = GRAPH_PATH):
        print(f"Loading knowledge graph from {path} (this can take a few minutes) ...", flush=True)
        start = time.time()
        self.graph = rdflib.Graph()
        self.graph.parse(path, format="nt")
        print(f"Loaded {len(self.graph)} triples in {time.time() - start:.0f} s", flush=True)
        self._pool = ThreadPoolExecutor(max_workers=1)

    @staticmethod
    def clean_query(text: str) -> str:
        q = text.strip()
        q = re.sub(r"^(```(sparql)?|'''|\"\"\")", "", q, flags=re.IGNORECASE).strip()
        q = re.sub(r"(```|'''|\"\"\")$", "", q).strip()
        if "PREFIX" not in q.upper():
            q = PREFIXES + q
        return q

    @staticmethod
    def looks_like_sparql(text: str) -> bool:
        t = text.upper()
        return any(k in t for k in ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE")) and "WHERE" in t

    @staticmethod
    def _fmt(value) -> str:
        if value is None:
            return "-"
        if isinstance(value, rdflib.URIRef):
            s = str(value)
            return s.rsplit("/", 1)[-1] if "wikidata.org" in s else s
        return str(value)

    def run(self, query_text: str) -> str:
        query = self.clean_query(query_text)
        try:
            future = self._pool.submit(lambda: list(self.graph.query(query)))
            rows = future.result(timeout=QUERY_TIMEOUT_S)
        except FuturesTimeout:
            return f"That query took longer than {QUERY_TIMEOUT_S} seconds. Could you make it more specific?"
        except Exception as e:
            log.warning("SPARQL error: %s", e)
            return f"I couldn't run that query. The SPARQL seems invalid: {str(e).splitlines()[0][:200]}"

        if not rows:
            return "The query ran fine, but there are no results in the knowledge graph."
        if isinstance(rows[0], bool):
            return "Yes." if rows[0] else "No."

        lines = [" | ".join(self._fmt(v) for v in row) for row in rows[:MAX_ROWS]]
        more = f"\n... and {len(rows) - MAX_ROWS} more results." if len(rows) > MAX_ROWS else ""
        return "\n".join(lines) + more
