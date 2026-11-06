"""Stage 3: runs a checked request from the planner on the graph, through fixed SPARQL templates only."""

from dataclasses import dataclass, field
from typing import List

from agent import nlg, sparql_builder as sb
from agent.kg import PREFIXES, KnowledgeGraph
from agent.lexicon import WDT, Lexicon, qid
from agent.parser import Parser

MAX_PROPERTIES = 120  # the most used properties go into the planner prompt
DDIS_LABELS = {PREFIXES["ddis"] + "tag": "user tag", PREFIXES["ddis"] + "rating": "user rating"}


@dataclass
class Property:
    id: str  # "P57" or "ddis:rating", as the planner writes it
    iri: str
    label: str
    shape: str  # "item", "date", "number" or "text"


@dataclass
class Request:
    kind: str  # "lookup", "count", "claim", "superlative", "filter" or "chain"
    entity: str = ""
    properties: List[str] = field(default_factory=list)  # IRIs
    direction: str = "out"
    negated: bool = False
    value: str = ""
    op: str = ""
    order_by: str = ""  # IRI
    pick: str = "max"


@dataclass
class Answer:
    text: str  # template sentence
    values: List[str] = field(default_factory=list)
    found: bool = False


def _shape(term) -> str:
    if term.kind == "iri":
        return "item"
    datatype = (term.datatype or "").rsplit("#", 1)[-1]
    if datatype in ("date", "dateTime", "gYear"):
        return "date"
    if datatype in ("decimal", "double", "float", "integer", "int"):
        return "number"
    return "text"


def _unmangle(text: str) -> str:
    """Undo UTF-8 read as Latin-1: "AlmodÃ³var" -> "Almodóvar"."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


class QueryEngine:
    def __init__(self, kg: KnowledgeGraph, lexicon: Lexicon):
        self.kg = kg
        self.lex = lexicon
        self.parser = Parser(kg, lexicon)
        self.properties = {}  # "P57" -> Property
        rows = kg.query("SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?o1) WHERE { ?s ?p ?o } GROUP BY ?p "
                        "ORDER BY DESC(?n)", timeout=300, max_rows=100_000).rows
        for predicate, _count, sample in rows:
            iri = predicate.value
            label = self.lex.prop2lbl.get(iri) or DDIS_LABELS.get(iri)
            if label and len(self.properties) < MAX_PROPERTIES:
                pid = iri[len(WDT):] if iri.startswith(WDT) else "ddis:" + iri[len(PREFIXES["ddis"]):]
                self.properties[pid] = Property(pid, iri, label, _shape(sample))
        self.by_iri = {p.iri: p for p in self.properties.values()}

    def resolve(self, name: str) -> List[str]:
        """Candidate Q-ids for a name, best first: exact label, else the Stage 2 entity finder (fuzzy, surnames)."""
        name = _unmangle(name).replace("’", "'").strip(" \"'?.!,")
        bare = name.lower().removeprefix("the ")
        for label in (name.lower(), "the " + bare, bare):  # "Irishman" is "The Irishman" in the graph
            if label in self.lex.lbl2ent:
                return self.parser._rank(self.lex.lbl2ent[label])
        return self.parser._find_entity(name)[1]

    def run(self, request: Request, trace) -> Answer:
        if request.kind == "filter":
            return self._filter(request, trace)
        candidates = self.resolve(request.entity)
        if not candidates:
            return Answer(nlg.unknown_entity(request.entity))
        if request.kind == "chain":
            return self._chain(request, candidates, trace)

        entity, direction = self._pick(candidates, request)
        relation = " or ".join(self.by_iri[p].label for p in request.properties)
        if entity is None and not request.negated:
            if request.kind == "claim":
                return Answer(nlg.answer(["No"]), ["No"], True)
            return Answer(nlg.no_facts(relation, self.lex.label(candidates[0])))
        entity = entity or candidates[0]
        predicates = request.properties

        if request.kind == "claim":
            others = self.resolve(request.value)
            query = (sb.claim_any(entity, predicates, others) if others
                     else sb.claim_literal(entity, predicates, request.value))
            holds = self._query(query, trace)
            return Answer(nlg.answer(["Yes" if holds else "No"]), ["Yes" if holds else "No"], True)
        if request.negated:
            build = sb.complement_count if request.kind == "count" else sb.complement
            rows = self._query(build(entity, predicates[0], direction), trace).rows
            if request.kind == "count":
                return self._values([rows[0][0].value])
            return self._values(self._rank_complement(rows, nlg.ANSWER_LIMIT))
        if request.kind == "count":
            rows = self._query(sb.count_any(entity, predicates, direction), trace).rows
            return self._values([rows[0][0].value])
        if request.kind == "superlative":
            order = "DESC" if request.pick == "max" else "ASC"
            rows = self._query(sb.ranked(entity, predicates, direction, request.order_by, order), trace).rows
            return self._values(self._labels(rows))

        rows = self._query(sb.lookup_any(entity, predicates, direction), trace).rows
        if predicates == [sb.RELEASE_DATE] and direction == "out" and rows:
            rows = [min(rows, key=lambda r: r[0].value)]  # one date per country: keep the first release
        return self._values(sorted(self._labels(rows), key=str.casefold))

    def _pick(self, candidates, request):
        """The first candidate with facts for the relation; the other direction if the planner's has none."""
        flipped = "in" if request.direction == "out" else "out"
        for direction in (request.direction, flipped):
            for entity in candidates:
                if self.kg.query(sb.has_any(entity, request.properties, direction)):
                    return entity, direction
        return None, request.direction

    def _filter(self, request: Request, trace) -> Answer:
        predicate = request.properties[0]
        is_date = self.by_iri[predicate].shape == "date"
        rows = self._query(sb.filtered(predicate, request.op, request.value, is_date), trace).rows
        return self._values(sorted(self._labels(rows), key=str.casefold))

    def _chain(self, request: Request, candidates, trace) -> Answer:
        for entity in candidates:
            rows = self._query(sb.chain(entity, request.properties), trace).rows
            if rows:
                return self._values(sorted(self._labels(rows), key=str.casefold))
        return Answer(nlg.no_facts(" of the ".join(self.by_iri[p].label for p in reversed(request.properties)),
                                   self.lex.label(candidates[0])))

    def _query(self, query: str, trace):
        trace.add("sparql", query)
        return self.kg.query(query)

    @staticmethod
    def _labels(rows) -> List[str]:
        return list(dict.fromkeys(nlg.format_term(label or value) for value, label, *_ in rows
                                  if label or (value is not None and value.kind != "iri")))

    @staticmethod
    def _values(values: List[str]) -> Answer:
        if not values:
            return Answer(nlg.no_match())
        return Answer(nlg.answer(values), values[:nlg.ANSWER_LIMIT], True)

    def _rank_complement(self, rows, limit: int) -> List[str]:
        """The best-known members of a complement, as in the Stage 2 factual handler."""
        candidates = {}
        for value, label, *_ in rows:
            if value is not None and value.kind == "iri" and label is not None:
                candidates.setdefault(qid(value.value), nlg.format_term(label))
        if not candidates:
            return []
        degree = {qid(row[0].value): int(row[1].value)
                  for row in self.kg.query(sb.degrees(list(candidates))).rows if row[0] is not None}
        ordered = sorted(candidates.items(), key=lambda item: (-degree.get(item[0], 0), item[1].casefold()))
        return list(dict.fromkeys(text for _, text in ordered))[:limit]

