"""Label and type lookups over the whole graph, built once at startup (as in tutorial 04a)."""

from bisect import bisect_left
from collections import defaultdict

from agent.kg import KnowledgeGraph
from agent.normalize import normalize_label

WD = "http://www.wikidata.org/entity/"
WDT = "http://www.wikidata.org/prop/direct/"
FILM = "Q11424"
HUMAN = "Q5"
CURATED_LABELS = {HUMAN: "human"}


def qid(iri: str) -> str:
    return iri[len(WD):] if iri.startswith(WD) else iri


class Lexicon:
    def __init__(self, kg: KnowledgeGraph):
        self.ent2lbl = {}  # "Q47703" -> "The Godfather"
        self.lbl2ent = defaultdict(list)  # "the godfather" -> ["Q47703", "Q243556", ...]
        self.prop2lbl = {}  # predicate IRI -> "director"
        self.types = defaultdict(set)  # "Q47703" -> {"Q11424"}
        self.directed = set()  # entities with a director fact: legacy movie-like resolution

        labels = kg.query("SELECT ?e ?l WHERE { ?e rdfs:label ?l }", timeout=300, max_rows=10_000_000)
        for entity, label in labels.rows:
            if entity.value.startswith(WD):
                q = qid(entity.value)
                self.ent2lbl.setdefault(q, label.value)
                self.lbl2ent[normalize_label(label.value)].append(q)
            elif entity.value.startswith(WDT):
                self.prop2lbl[entity.value] = label.value

        types = kg.query("SELECT ?e ?c WHERE { ?e wdt:P31 ?c }", timeout=300, max_rows=10_000_000)
        for entity, cls in types.rows:
            self.types[qid(entity.value)].add(qid(cls.value))
        directed = kg.query("SELECT DISTINCT ?m WHERE { ?m wdt:P57 ?d }", timeout=300,
                            max_rows=10_000_000)
        for (entity,) in directed.rows:
            self.directed.add(qid(entity.value))
        self._sorted_labels = sorted(self.lbl2ent)

    def prefix_labels(self, prefix: str) -> list:
        """Sorted canonical labels that start with `prefix`, case-insensitively."""
        prefix = normalize_label(prefix)
        start = bisect_left(self._sorted_labels, prefix)
        found = []
        for label in self._sorted_labels[start:]:
            if not label.startswith(prefix):
                break
            found.append(label)
        return found

    def label(self, entity: str) -> str:
        return self.ent2lbl.get(entity) or CURATED_LABELS.get(entity, entity)

    def is_film(self, entity: str) -> bool:
        """Strict film metadata: the entity is an instance of Q11424."""
        return FILM in self.types.get(entity, ())

    def is_movie(self, entity: str) -> bool:
        """Legacy question resolution: a strict film or an entity with a director fact."""
        return self.is_film(entity) or entity in self.directed

    def is_human(self, entity: str) -> bool:
        return HUMAN in self.types.get(entity, ())
