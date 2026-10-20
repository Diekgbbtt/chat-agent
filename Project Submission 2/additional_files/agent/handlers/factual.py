"""Stage 2: answers single-hop natural-language questions from the knowledge graph."""

from agent import nlg, sparql_builder as sb
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon, qid
from agent.parser import Parser
from agent.preprocess import Preprocessor


class FactualHandler:
    name = "factual"

    def __init__(self, kg: KnowledgeGraph, lexicon: Lexicon):
        self.kg = kg
        self.lex = lexicon
        self.parser = Parser(kg, lexicon)
        self.pre = Preprocessor(kg, lexicon, self.parser)

    def can_handle(self, text: str, session) -> bool:
        return True

    def handle(self, text: str, session, trace) -> str:
        plan = self.pre.analyze(text)
        trace.add("preprocess", plan)
        if plan.claim is not None:
            holds = self.kg.query(sb.claim(plan.claim.film, plan.claim.predicate, plan.claim.person))
            return nlg.answer(["Yes" if holds else "No"])
        if plan.clarify:
            return nlg.no_entity()
        q = self.parser.parse(plan.text)
        trace.add("question", q)
        if q.error == "no_entity":
            return nlg.no_entity()
        entity = self.lex.label(q.entity)
        if q.error == "no_relation":
            return nlg.no_relation(entity)
        relation = self.lex.prop2lbl.get(q.predicate, nlg.short_iri(q.predicate))
        negated = plan.negated and q.kind in ("lookup", "count") and q.predicate
        negated_lookup = negated and q.kind == "lookup"
        if q.error == "no_facts" and not negated:
            return nlg.no_facts(relation, entity)

        if negated:
            direction = q.direction
            if q.error == "no_facts":
                # the negation is about the whole relation, not about this entity's (missing) facts
                direction = "out" if self.lex.is_film(q.entity) else "in"
            others = [f for f in plan.films if f != q.entity]
            # "how many ... not ..." counts the complement, not the entity's own values
            build = sb.complement_count if q.kind == "count" else sb.complement
            query = build(q.entity, q.predicate, direction, universe=plan.universe, others=others)
        elif q.kind == "count":
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

        if negated_lookup:
            values = self._rank_complement(rows, nlg.ANSWER_LIMIT)
            trace.add("complement", {"candidates": len(rows), "serialized": len(values)})
        else:
            values = {nlg.format_term(label or value) for value, label, *_ in rows if label or value.kind != "iri"}
            values = sorted(values, key=str.casefold)
        if not values:
            return nlg.no_facts(relation, entity)
        return nlg.answer(values)

    def _rank_complement(self, rows, limit: int):
        """Keep the most prominent complement members; degree matches Parser._rank."""
        candidates = {}
        for value, label, *_ in rows:
            if value is None or value.kind != "iri" or label is None:
                continue
            candidates.setdefault(qid(value.value), nlg.format_term(label))
        if not candidates:
            return []

        degree = self._degrees(list(candidates))
        ordered = sorted(candidates.items(),
                         key=lambda item: (-degree.get(item[0], 0), item[1].casefold()))
        values, seen = [], set()
        for _entity, text in ordered:
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(text)
            if len(values) >= limit:
                break
        return values

    def _degrees(self, entities):
        if not entities:
            return {}
        rows = self.kg.query(sb.degrees(entities)).rows
        return {qid(row[0].value): int(row[1].value)
                for row in rows if row[0] is not None and row[1] is not None}
