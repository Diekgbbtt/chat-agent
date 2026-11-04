"""Vocabulary discovery: find the relation or type that the schema card does not carry."""

import json
import logging
import re
import time
from pathlib import Path

from agent.kg import PREFIXES
from agent.normalize import normalize_label
from agent.observability import emit
from agent.tools.sparql import Observation

log = logging.getLogger("agent.tools.discover")

MAX_LIMIT = 10
RELATION_POOL = 200
TYPE_POOL = 200
QID = re.compile(r"^Q\d+$")
QID_NEEDLE = re.compile(r"^q\d+$")
RELATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "relations.json"
WDT = PREFIXES["wdt"]
EMPTY_QUERY = ("The discovery query is empty. Retry with a relation word such as composer "
               "or a type word such as film.")
UNKNOWN_KIND = "Unknown discovery kind '{kind}'. Retry with kind=relation or kind=type."
NO_RELATION = ("No relation matched '{query}'. Retry with a shorter word, a synonym such as "
               "composer, or the property ID.")
NO_RELATION_SUBJECT = ("No relation matched '{query}' for subject '{subject}'. "
                       "Retry without the subject filter.")
NO_TYPE = "No type matched '{query}'. Retry with a shorter word such as film or the class QID."
UNKNOWN_SUBJECT = "Unknown subject '{subject}'. Resolve the entity first and pass its QID."


def short_id(iri: str) -> str:
    if iri.startswith(WDT):
        return iri[len(WDT):]
    for prefix, base in PREFIXES.items():
        if iri.startswith(base):
            return f"{prefix}:{iri[len(base):]}"
    return iri


def expand(key: str) -> str:
    prefix, _, name = key.partition(":")
    return PREFIXES[prefix] + name


class DiscoverTool:
    name = "discover"

    def __init__(self, kg, lexicon):
        self.kg = kg
        self.lexicon = lexicon
        self.aliases = self._load_aliases()
        self.class_ids = sorted({value for values in lexicon.types.values() for value in values})
        self.class_set = set(self.class_ids)

    @staticmethod
    def _load_aliases() -> dict:
        data = json.loads(RELATIONS_PATH.read_text(encoding="utf-8"))
        return {expand(key): [normalize_label(word) for word in words]
                for key, words in data.items()}

    def _properties(self) -> list:
        entries, seen = [], set()
        for iri, label in self.lexicon.prop2lbl.items():
            if not iri.startswith(WDT):
                continue
            entries.append({"iri": iri, "id": short_id(iri), "label": label,
                            "aliases": self.aliases.get(iri, [])})
            seen.add(iri)
        for iri, aliases in self.aliases.items():
            if iri in seen:
                continue
            entries.append({"iri": iri, "id": short_id(iri),
                            "label": aliases[0] if aliases else short_id(iri),
                            "aliases": aliases})
        return entries

    @staticmethod
    def _match(entry: dict, needle: str):
        label = normalize_label(entry["label"])
        if needle in (normalize_label(entry["id"]), label):
            return 0
        if needle in entry["aliases"]:
            return 1
        if label.startswith(needle):
            return 2
        if any(alias.startswith(needle) for alias in entry["aliases"]):
            return 3
        if needle in label:
            return 4
        if any(needle in alias for alias in entry["aliases"]):
            return 5
        return None

    def _query(self, sparql: str) -> list:
        try:
            return list(self.kg.query(sparql).rows)
        except Exception:  # noqa: BLE001 - discovery reports an empty result, never crashes
            return []

    def _subject(self, raw: str):
        value = (raw or "").strip()
        if not value:
            return None, None
        if QID.fullmatch(value):
            known = value in self.lexicon.ent2lbl or value in self.lexicon.types
            return (value, value in self.class_set) if known else (None, None)
        matches = self.lexicon.lbl2ent.get(normalize_label(value), ())
        if not matches:
            return None, None
        classes = [entity for entity in matches if entity in self.class_set]
        entity = (classes or list(matches))[0]
        return entity, entity in self.class_set

    def _usage(self, iris: list, subject: str, is_class: bool) -> dict:
        if not iris:
            return {}
        values = " ".join(f"<{iri}>" for iri in iris)
        if not subject:
            query = (f"SELECT ?p (COUNT(*) AS ?n) WHERE {{ VALUES ?p {{ {values} }} "
                     "?s ?p ?o } GROUP BY ?p")
            return {row[0].value: int(row[1].value) for row in self._query(query)}
        if is_class:
            query = (f"SELECT ?p (COUNT(*) AS ?n) WHERE {{ VALUES ?p {{ {values} }} "
                     f"?s wdt:P31 wd:{subject} . ?s ?p ?o }} GROUP BY ?p")
            return {row[0].value: int(row[1].value) for row in self._query(query)}
        query = (f"SELECT ?p (COUNT(*) AS ?n) WHERE {{ VALUES ?p {{ {values} }} "
                 f"wd:{subject} ?p ?o }} GROUP BY ?p")
        out = {row[0].value: int(row[1].value) for row in self._query(query)}
        query = (f"SELECT ?p (COUNT(*) AS ?n) WHERE {{ VALUES ?p {{ {values} }} "
                 f"?s ?p wd:{subject} }} GROUP BY ?p")
        into = {row[0].value: int(row[1].value) for row in self._query(query)}
        return {iri: out.get(iri, 0) + into.get(iri, 0) for iri in iris}

    def _direction(self, iri: str, subject: str, is_class: bool, usage: int) -> str:
        if not subject or is_class or usage == 0:
            return "out"
        query = f"SELECT (COUNT(*) AS ?n) WHERE {{ wd:{subject} <{iri}> ?o }}"
        rows = self._query(query)
        outgoing = int(rows[0][0].value) if rows else 0
        return "both" if outgoing and usage > outgoing else "in"

    def _relation_samples(self, iri: str, subject: str, is_class: bool, direction: str) -> list:
        if subject and not is_class and direction == "in":
            query = f"SELECT ?s WHERE {{ ?s <{iri}> wd:{subject} }} LIMIT 3"
            variable = 0
        elif subject:
            query = (f"SELECT ?o WHERE {{ wd:{subject} <{iri}> ?o }} LIMIT 3"
                     if not is_class else
                     f"SELECT ?o WHERE {{ ?s wdt:P31 wd:{subject} . ?s <{iri}> ?o }} LIMIT 3")
            variable = 0
        else:
            query = (f"SELECT ?o WHERE {{ ?s wdt:P31 wd:Q11424 . ?s <{iri}> ?o }} LIMIT 3")
            variable = 0
        rows = self._query(query)
        if not rows:
            rows = self._query(f"SELECT ?o WHERE {{ ?s <{iri}> ?o }} LIMIT 3")
        samples = []
        for row in rows:
            if row[variable] is None:
                continue
            term = row[variable]
            value = self.lexicon.label(term.value.rsplit("/", 1)[-1]) if term.kind == "iri" else term.value
            if value not in samples:
                samples.append(value)
        return samples

    def _relations(self, needle: str, subject: str) -> Observation:
        subject_id, is_class = self._subject(subject)
        if subject and subject_id is None:
            return Observation((), error=UNKNOWN_SUBJECT.format(subject=subject))
        matched = []
        for entry in self._properties():
            score = self._match(entry, needle)
            if score is not None:
                matched.append((score, entry))
        if not matched:
            return Observation((), error=NO_RELATION.format(query=needle))
        matched.sort(key=lambda item: (item[0], normalize_label(item[1]["label"]), item[1]["id"]))
        pool = matched[:RELATION_POOL]
        usage = self._usage([entry["iri"] for _, entry in pool], subject_id, is_class)
        rows = []
        for score, entry in pool:
            count = usage.get(entry["iri"], 0)
            if subject_id and count == 0:
                continue
            rows.append((score, count, entry))
        if not rows:
            return Observation((), error=NO_RELATION_SUBJECT.format(query=needle, subject=subject))
        rows.sort(key=lambda item: (item[0], -item[1], item[2]["id"]))
        final = []
        for score, count, entry in rows[:MAX_LIMIT]:
            direction = self._direction(entry["iri"], subject_id, is_class, count)
            final.append({
                "row_id": "",
                "id": entry["id"],
                "label": entry["label"],
                "direction": direction,
                "usage": count,
                "samples": self._relation_samples(entry["iri"], subject_id, is_class, direction),
            })
        return self._finish(final)

    def _type_match(self, entity: str, label: str, needle: str):
        if QID_NEEDLE.fullmatch(needle):
            return 0 if needle == normalize_label(entity) else None
        if needle == normalize_label(entity):
            return 0
        normalized = normalize_label(label)
        if needle == normalized:
            return 0
        if normalized.startswith(needle):
            return 1
        if needle in normalized:
            return 2
        return None

    def _type_usage(self, entities: list) -> dict:
        if not entities:
            return {}
        values = " ".join(f"wd:{entity}" for entity in entities)
        query = (f"SELECT ?c (COUNT(*) AS ?n) WHERE {{ VALUES ?c {{ {values} }} "
                 "?e wdt:P31 ?c } GROUP BY ?c")
        return {row[0].value.rsplit("/", 1)[-1]: int(row[1].value) for row in self._query(query)}

    def _type_samples(self, entity: str) -> list:
        rows = self._query(f"SELECT ?e WHERE {{ ?e wdt:P31 wd:{entity} }} LIMIT 3")
        samples = []
        for row in rows:
            if row[0] is None:
                continue
            label = self.lexicon.label(row[0].value.rsplit("/", 1)[-1])
            if label not in samples:
                samples.append(label)
        return samples

    def _types(self, needle: str) -> Observation:
        matched = []
        for entity in self.class_ids:
            label = self.lexicon.label(entity)
            score = self._type_match(entity, label, needle)
            if score is not None:
                matched.append((score, entity, label))
        if not matched:
            return Observation((), error=NO_TYPE.format(query=needle))
        matched.sort(key=lambda item: (item[0], normalize_label(item[2]), item[1]))
        pool = matched[:TYPE_POOL]
        usage = self._type_usage([entity for _, entity, _ in pool])
        rows = []
        for score, entity, label in pool:
            rows.append((score, -usage.get(entity, 0), entity, label))
        rows.sort(key=lambda item: (item[0], item[1], item[2]))
        final = []
        for score, negative, entity, label in rows[:MAX_LIMIT]:
            final.append({
                "row_id": "",
                "id": entity,
                "label": label,
                "instances": -negative,
                "samples": self._type_samples(entity),
            })
        return self._finish(final)

    @staticmethod
    def _finish(rows: list) -> Observation:
        rows = rows[:MAX_LIMIT]
        for index, row in enumerate(rows):
            row["row_id"] = f"d{index}"
        return Observation(tuple(rows))

    def run(self, kind: str, query: str, subject: str = "") -> Observation:
        started = time.perf_counter()
        needle = normalize_label(query)
        if not needle:
            return Observation((), error=EMPTY_QUERY)
        if kind == "relation":
            observation = self._relations(needle, subject)
        elif kind == "type":
            observation = self._types(needle)
        else:
            return Observation((), error=UNKNOWN_KIND.format(kind=kind))
        emit(log, "discover.run", kind=kind, query=needle, subject=subject,
             row_count=len(observation.rows), error=observation.error,
             latency_ms=round((time.perf_counter() - started) * 1000.0, 1))
        return observation
