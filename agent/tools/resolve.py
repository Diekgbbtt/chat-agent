"""Entity linking over the lexicon label index."""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from agent.lexicon import qid
from agent.normalize import normalize_label
from agent.observability import emit
from agent.tools.sparql import Observation

log = logging.getLogger("agent.tools.resolve")

MAX_LIMIT = 10
DEGREE_POOL = 1_000
QUERY_ID = re.compile(r"^Q\d+$")
EMPTY_QUERY = "The entity query is empty. Retry with a film or person label."
MISS_ERROR = ("No entity matched '{query}'. Retry with a shorter label or a spelling variant.")
TYPE_ERROR = ("Unknown type '{type}'. Retry with a type label from the schema card or a type QID.")
FILTER_MISS = ("No entity matched '{query}' with type '{type}'. "
               "Retry without the type filter or with a type label from the schema card.")


class ResolveEntityTool:
    name = "resolve_entity"

    def __init__(self, kg, lexicon, fuzzy: bool = False):
        self.kg = kg
        self.lexicon = lexicon
        self.fuzzy = fuzzy
        self._type_labels = self._build_type_labels()

    def _build_type_labels(self) -> Dict[str, str]:
        """Canonical label -> QID for classes the graph actually uses as a type."""
        known = {value for values in self.lexicon.types.values() for value in values}
        mapping = {}
        for entity in sorted(known):
            mapping.setdefault(normalize_label(self.lexicon.label(entity)), entity)
        return mapping

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

    def _bucket(self, query: str, type_qid: Optional[str] = None) -> List[Tuple[str, int]]:
        """Candidates with a match rank: 0 exact, 1 prefix, 2 contains."""
        exact = list(self.lexicon.lbl2ent.get(query, ()))
        if type_qid is not None and exact:
            exact = [entity for entity in exact
                     if type_qid in self.lexicon.types.get(entity, ())]
            if not exact:
                return []
        prefix_labels = [label for label in self.lexicon.prefix_labels(query) if label != query]
        prefix_set = set(prefix_labels)
        contains_labels = [label for label in self.lexicon._sorted_labels
                           if query in label and label not in prefix_set and label != query]
        seen, unique = {}, []
        for rank, labels in enumerate(([query] if exact else [], prefix_labels, contains_labels)):
            for label in labels:
                for entity in self.lexicon.lbl2ent.get(label, ()):
                    if entity in seen:
                        continue
                    if type_qid is not None and type_qid not in self.lexicon.types.get(entity, ()):
                        continue
                    seen[entity] = rank
                    unique.append((entity, rank))
                    if len(unique) >= DEGREE_POOL:
                        return unique
        return unique

    @staticmethod
    def _fuzzy_variants(query: str) -> set:
        """Bounded one-edit variants: delete one character, swap two, or toggle a leading article."""
        edits = {query}
        for index in range(len(query)):
            edits.add(query[:index] + query[index + 1:])
        for index in range(len(query) - 1):
            edits.add(query[:index] + query[index + 1] + query[index] + query[index + 2:])
        variants = set()
        for value in edits:
            variants.add(value)
            variants.add(value[4:] if value.startswith("the ") else f"the {value}")
        return variants

    def _fuzzy_candidates(self, query: str, type_qid: Optional[str] = None) -> List[Tuple[str, int]]:
        if not query or len(query) > 120:
            return []
        found, seen = [], set()
        for label in sorted(self._fuzzy_variants(query)):
            for entity in self.lexicon.lbl2ent.get(label, ()):
                if entity in seen:
                    continue
                if type_qid is not None and type_qid not in self.lexicon.types.get(entity, ()):
                    continue
                seen.add(entity)
                found.append((entity, 0))
                if len(found) >= DEGREE_POOL:
                    return found
        return found

    def _type_qid(self, value: str):
        if QUERY_ID.fullmatch(value):
            return value, None
        entity = self._type_labels.get(normalize_label(value))
        if entity is None:
            return None, TYPE_ERROR.format(type=value)
        return entity, None

    def _rows(self, candidates: List[Tuple[str, int]], type_qid: Optional[str]) -> list:
        degrees = self._degrees([entity for entity, _ in candidates])
        rows = []
        for entity, match_rank in candidates:
            types = [{"id": value, "label": self.lexicon.label(value)}
                     for value in sorted(self.lexicon.types.get(entity, ()))]
            rows.append({
                "row_id": "",
                "qid": entity,
                "label": self.lexicon.label(entity),
                "types": types,
                "kind": types[0]["label"] if types else None,
                "type_match": None if type_qid is None else type_qid in self.lexicon.types.get(entity, ()),
                "film": self.lexicon.is_film(entity),
                "human": self.lexicon.is_human(entity),
                "degree": degrees.get(entity, 0),
                "match_rank": match_rank,
            })
        rows.sort(key=lambda row: (row["match_rank"], row["type_match"] is False,
                                   -row["degree"], row["qid"]))
        return rows

    def run(self, query: str, type: str = "") -> Observation:
        started = time.perf_counter()
        key = normalize_label(query)
        if not key:
            return Observation((), error=EMPTY_QUERY)
        type_qid, type_error = self._type_qid(type.strip()) if type else (None, None)
        if type_error:
            return Observation((), error=type_error)

        candidates = self._bucket(key, type_qid)
        fuzzy = False
        if not candidates and self.fuzzy:
            candidates = self._fuzzy_candidates(key, type_qid)
            fuzzy = bool(candidates)
        if not candidates:
            if type_qid is not None and self._bucket(key):
                return Observation((), error=FILTER_MISS.format(query=query.strip(), type=type))
            return Observation((), error=MISS_ERROR.format(query=query.strip()))

        rows = self._rows(candidates, type_qid)
        rows = rows[:MAX_LIMIT]
        for index, row in enumerate(rows):
            row["row_id"] = f"e{index}"
            del row["match_rank"]
        emit(log, "resolve.run", query=key, type=type_qid, fuzzy=fuzzy, row_count=len(rows),
             entities=[row["qid"] for row in rows],
             latency_ms=round((time.perf_counter() - started) * 1000.0, 1))
        return Observation(tuple(rows))
