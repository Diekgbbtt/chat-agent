"""Entity linking over the lexicon label index."""

import logging
import time
from typing import List

from agent.kg import Term
from agent.lexicon import qid
from agent.observability import emit
from agent.tools.sparql import Observation

log = logging.getLogger("agent.tools.resolve")

MAX_LIMIT = 10
DEFAULT_LIMIT = 5


class ResolveEntityTool:
    name = "resolve_entity"

    def __init__(self, kg, lexicon):
        self.kg = kg
        self.lexicon = lexicon

    def _degrees(self, entities: List[str]) -> dict:
        if not entities:
            return {}
        values = " ".join(f"wd:{entity}" for entity in entities)
        query = (f"SELECT ?e (COUNT(?p) AS ?c) WHERE {{ VALUES ?e {{ {values} }} "
                 "?e ?p ?o } GROUP BY ?e")
        try:
            result = self.kg.query(query)
        except Exception:  # noqa: BLE001 - degree is metadata, not a reason to fail lookup
            return {}
        return {qid(row[0].value): int(row[1].value)
                for row in result.rows if row[0] is not None and row[1] is not None}

    def _bucket(self, query: str):
        exact = list(self.lexicon.lbl2ent.get(query, ()))
        prefix_labels = [label for label in self.lexicon.prefix_labels(query) if label != query]
        contains_labels = [label for label in self.lexicon._sorted_labels
                           if query in label and label not in prefix_labels and label != query]
        ordered = []
        for label in [query] if exact else []:
            ordered.extend(self.lexicon.lbl2ent.get(label, ()))
        for label in prefix_labels:
            ordered.extend(self.lexicon.lbl2ent.get(label, ()))
        for label in contains_labels:
            ordered.extend(self.lexicon.lbl2ent.get(label, ()))
        seen, unique = set(), []
        for entity in ordered:
            if entity not in seen:
                seen.add(entity)
                unique.append(entity)
        return unique

    def run(self, query: str, limit: int = DEFAULT_LIMIT) -> Observation:
        started = time.perf_counter()
        query = (query or "").strip().casefold()
        if not query:
            return Observation(())
        limit = max(1, min(int(limit), MAX_LIMIT))
        entities = self._bucket(query)[:limit]
        degrees = self._degrees(entities)
        rows = []
        for index, entity in enumerate(entities):
            rows.append({
                "row_id": f"e{index}",
                "qid": entity,
                "label": self.lexicon.label(entity),
                "types": sorted(self.lexicon.types.get(entity, ())),
                "film": self.lexicon.is_film(entity),
                "human": self.lexicon.is_human(entity),
                "degree": degrees.get(entity, 0),
            })
        emit(log, "resolve.run", query=query, limit=limit, row_count=len(rows),
             entities=[row["qid"] for row in rows],
             latency_ms=round((time.perf_counter() - started) * 1000.0, 1))
        return Observation(tuple(rows))
