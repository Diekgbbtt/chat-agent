"""S1 domain-model probe: relation union, labels, triple counts and grounded examples.

Run from the repo root (worktree) with the venv from the main checkout:
    /Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/probe_domain_model.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root, so `agent` imports

from agent import sparql_builder as sb
from agent.config import load_settings
from agent.kg import KnowledgeGraph, PREFIXES
from agent.lexicon import Lexicon
from agent.parser import Parser, _load_synonyms


def short(iri: str) -> str:
    for prefix, base in PREFIXES.items():
        if iri.startswith(base):
            return f"{prefix}:{iri[len(base):]}"
    return iri


def one(kg: KnowledgeGraph, query: str) -> int:
    return int(kg.query(query).rows[0][0].value)


def main() -> int:
    settings = load_settings()
    kg = KnowledgeGraph.open(settings.graph_path, settings.store_path)
    lex = Lexicon(kg)
    parser = Parser(kg, lex)

    print("== 1. relation union ==")
    synonyms = _load_synonyms()
    print(f"source A: agent/data/relations.json -> {len(synonyms)} predicates")

    parsed, errors = Counter(), Counter()
    with open("evals/stage2_factual.jsonl", encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            question = parser.parse(case["input"])
            if question.error:
                errors[question.error] += 1
            elif question.predicate:
                parsed[question.predicate] += 1
    print(f"source B: predicates from parsing all 508 eval inputs -> {len(parsed)} distinct")
    for predicate, count in parsed.most_common():
        print(f"    {short(predicate):14s} label={lex.prop2lbl.get(predicate)!r:24s} cases={count}")
    print(f"source B parse errors: {dict(errors)}")
    print(f"source C: sparql_builder.RELEASE_DATE -> {short(sb.RELEASE_DATE)}")
    print("source D: sparql_builder type constraint -> wdt:P31 wd:Q11424 (films)")

    union = sorted(set(synonyms) | set(parsed) | {sb.RELEASE_DATE})
    print(f"\nunion size: {len(union)} predicates")

    print("\n== 2. per-relation facts: label, triples, 2 grounded examples ==")
    for predicate in union:
        label = lex.prop2lbl.get(predicate, "(no @en label)")
        count = one(kg, f"SELECT (COUNT(*) AS ?n) WHERE {{ ?s <{predicate}> ?o }}")
        rows = kg.query(
            f"SELECT ?s ?sl ?o ?ol WHERE {{ ?s <{predicate}> ?o . "
            f"OPTIONAL {{ ?s rdfs:label ?sl }} OPTIONAL {{ ?o rdfs:label ?ol }} }} LIMIT 40").rows
        examples = []
        for subj, subj_label, obj, obj_label in rows:
            if len(examples) >= 2:
                break
            examples.append(f"{subj_label.value if subj_label else short(subj.value)}"
                            f" -> {obj_label.value if obj_label else short(obj.value)}")
        while len(examples) < 2:
            examples.append("(fewer than 2 triples with labels)")
        print(f"{short(predicate):14s} label={label!r:26s} triples={count:>7d}  e.g. {examples[0]} | {examples[1]}")

    print("\n== 3. entity types used by the pipeline ==")
    films = one(kg, "SELECT (COUNT(DISTINCT ?f) AS ?n) WHERE { ?f wdt:P31 wd:Q11424 }")
    print(f"films (wdt:P31 wd:Q11424): {films}")
    directed = one(kg, "SELECT (COUNT(DISTINCT ?m) AS ?n) WHERE { ?m wdt:P57 ?d }")
    print(f"entities with a director (Lexicon.directed): {directed}")
    for qid_label in (("Q25188", "film example"), ("Q25191", "human example"), ("Q47703", "ambiguous label example")):
        qid, what = qid_label
        types = [short(t) for t in sorted(lex.types.get(qid, set()))][:6]
        print(f"{qid} ({what}): label={lex.label(qid)!r} types={types} is_film={lex.is_film(qid)} is_human={lex.is_human(qid)}")
    print(f"label 'The Godfather' resolves to: {lex.lbl2ent['the godfather']}")

    print("\n== 4. direction conventions on P57 (grounded) ==")
    for entity, direction, question in (("Q25188", "out", "Who directed 'Inception'?"),
                                        ("Q25191", "in", "Which films did Christopher Nolan direct?")):
        query = sb.lookup(entity, "http://www.wikidata.org/prop/direct/P57", direction)
        rows = kg.query(query).rows
        values = [row[1].value if row[1] else short(row[0].value) for row in rows]
        print(f"{question}  entity={entity} direction={direction}")
        print(f"    SPARQL: {query}")
        print(f"    rows: {values[:6]}{' ...' if len(values) > 6 else ''}")

    print("\n== 5. sample answer values from the eval set (label -> first QID -> types) ==")
    for label in ("United States", "South Korea", "drama", "The Handmaiden", "Inception"):
        candidates = lex.lbl2ent.get(label.lower(), [])[:2]
        for qid in candidates:
            types = [short(t) for t in sorted(lex.types.get(qid, set()))][:4]
            print(f"{label!r} -> {qid} types={types}")

    kg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
