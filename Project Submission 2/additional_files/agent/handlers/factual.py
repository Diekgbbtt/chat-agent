"""Stage 2: answers single-hop natural-language questions from the knowledge graph."""

from agent import nlg, sparql_builder as sb
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.parser import Parser


class FactualHandler:
    name = "factual"

    def __init__(self, kg: KnowledgeGraph, lexicon: Lexicon):
        self.kg = kg
        self.lex = lexicon
        self.parser = Parser(kg, lexicon)

    def can_handle(self, text: str, session) -> bool:
        return True

    def handle(self, text: str, session, trace) -> str:
        q = self.parser.parse(text)
        trace.add("question", q)
        if q.error == "no_entity":
            return nlg.no_entity()
        entity = self.lex.label(q.entity)
        if q.error == "no_relation":
            return nlg.no_relation(entity)
        relation = self.lex.prop2lbl.get(q.predicate, nlg.short_iri(q.predicate))
        if q.error == "no_facts":
            return nlg.no_facts(relation, entity)

        if q.kind == "count":
            query = sb.count(q.entity, q.predicate, q.direction)
        elif q.kind in ("earliest", "latest"):
            query = sb.superlative(q.entity, q.predicate, q.direction, "ASC" if q.kind == "earliest" else "DESC")
        else:
            query = sb.lookup(q.entity, q.predicate, q.direction)
        trace.add("sparql", query)
        rows = self.kg.query(query).rows

        if q.kind == "count":
            return nlg.answer([rows[0][0].value])
        if q.predicate == sb.RELEASE_DATE and q.direction == "out":
            rows = [min(rows, key=lambda r: r[0].value)]  # one date per country: keep the first release
        values = {nlg.format_term(label or value) for value, label, *_ in rows if label or value.kind != "iri"}
        if not values:
            return nlg.no_facts(relation, entity)
        return nlg.answer(sorted(values, key=str.casefold))
