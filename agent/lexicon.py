"""Label and type lookups over the whole graph, built once at startup (as in tutorial 04a)."""

from collections import defaultdict

from agent.kg import KnowledgeGraph

WD = "http://www.wikidata.org/entity/"
WDT = "http://www.wikidata.org/prop/direct/"
FILM = "Q11424"
HUMAN = "Q5"


def qid(iri: str) -> str:
    return iri[len(WD):] if iri.startswith(WD) else iri


class Lexicon:
    def __init__(self, kg: KnowledgeGraph):
        self.ent2lbl = {}  # "Q47703" -> "The Godfather"
        self.lbl2ent = defaultdict(list)  # "the godfather" -> ["Q47703", "Q243556", ...]
        self.prop2lbl = {}  # predicate IRI -> "director"
        self.types = defaultdict(set)  # "Q47703" -> {"Q11424"}
        self.directed = set()  # everything with a director: films, animated films, TV films, ...

        labels = kg.query("SELECT ?e ?l WHERE { ?e rdfs:label ?l }", timeout=300, max_rows=10_000_000)
        for entity, label in labels.rows:
            if entity.value.startswith(WD):
                q = qid(entity.value)
                self.ent2lbl.setdefault(q, label.value)
                self.lbl2ent[label.value.lower().replace("’", "'")].append(q)
            elif entity.value.startswith(WDT):
                self.prop2lbl[entity.value] = label.value

        types = kg.query("SELECT ?e ?c WHERE { ?e wdt:P31 ?c }", timeout=300, max_rows=10_000_000)
        for entity, cls in types.rows:
            self.types[qid(entity.value)].add(qid(cls.value))
        for (entity,) in kg.query("SELECT DISTINCT ?m WHERE { ?m wdt:P57 ?d }", timeout=300, max_rows=10_000_000).rows:
            self.directed.add(qid(entity.value))

    def label(self, entity: str) -> str:
        return self.ent2lbl.get(entity, entity)

    def is_film(self, entity: str) -> bool:
        return FILM in self.types.get(entity, ()) or entity in self.directed

    def is_human(self, entity: str) -> bool:
        return HUMAN in self.types.get(entity, ())
