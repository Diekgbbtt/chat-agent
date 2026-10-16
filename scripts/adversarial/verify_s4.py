"""S4 verification: reproduce every red example of D1-D8 and probe the cited QIDs.

Run from the repo root (worktree) with the venv from the main checkout.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root, so `agent` imports

from agent.cli import load_agent

RED = [
    ("D1", "How many awards did 'Inception' win?"),
    ("D1", "How many awards has Meryl Streep won?"),
    ("D1", "How many cast members does 'Inception' have?"),
    ("D2", "I love 'Jaws'. Who directed 'Inception'?"),
    ("D2", "Who directed 'The Godfather'? Who directed 'Inception'?"),
    ("D2", "I love Jaws. Who directed Inception?"),
    ("D3", "Who directed 'Batman Begins', the first film in the trilogy?"),
    ("D3", "Who wrote the screenplay of 'The Godfather', the first film of the trilogy?"),
    ("D4", "who directed 'Amelie'?"),
    ("D4", "who directed 101 reykjavik?"),
    ("D5", "Did Steven Spielberg direct 'Inception'?"),
    ("D5", "Did Christopher Nolan direct 'Jaws'?"),
    ("D6", "When did 'The Blue Bird Vol. 2' come out?"),
    ("D6", "When was 'Tokyo Chorus II' released?"),
    ("D7", "Whodirected 'Inception'?"),
    ("D7", "who directedinception?"),
    ("D8", "Who did the directing for 'Inception'?"),
    ("D8", "Who was at the helm of 'Inception'?"),
]

QIDS = ["Q25188", "Q873", "Q189505", "Q8877", "Q25191", "Q47703", "Q166262", "Q484048",
        "Q113116290", "Q165525", "Q489818", "Q859448", "Q26989920", "Q12018",
        "Q8229794167428617", "Q0666980522408053"]


def main() -> int:
    agent = load_agent()
    parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))
    lex = parser.lex

    print("== lexicon existence of cited QIDs ==")
    for qid in QIDS:
        print(f"{qid}: label={lex.ent2lbl.get(qid)!r} in_lbl2ent={'yes' if qid in lex.lbl2ent.get(lex.ent2lbl.get(qid, '').lower(), []) else 'no'}")

    print("\n== red example reproduction ==")
    for type_id, text in RED:
        reply = agent.answer(text, f"verify-{type_id}")
        span, candidates = parser._find_entity(text)
        print(f"{type_id}: {text!r}\n    span={span} candidates={candidates[:3]}\n    reply={reply[:200]!r}")

    print("\n== true counts quoted by D1 (independent SPARQL) ==")
    kg = agent.handlers[0].kg
    for name, query in (
        ("Q25188 P166 (Inception awards)", "SELECT (COUNT(*) AS ?n) WHERE { <http://www.wikidata.org/entity/Q25188> <http://www.wikidata.org/prop/direct/P166> ?x }"),
        ("Q873 P166 (Meryl Streep awards)", "SELECT (COUNT(*) AS ?n) WHERE { <http://www.wikidata.org/entity/Q873> <http://www.wikidata.org/prop/direct/P166> ?x }"),
        ("Q25188 P161 (Inception cast)", "SELECT (COUNT(*) AS ?n) WHERE { <http://www.wikidata.org/entity/Q25188> <http://www.wikidata.org/prop/direct/P161> ?x }"),
    ):
        print(f"{name}: {int(kg.query(query).rows[0][0].value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
