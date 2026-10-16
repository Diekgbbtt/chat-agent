"""S3 battery 2: T3 quote variants, T4 typo wrong-links, T2 candidate longer titles.

Run from the repo root (worktree) with the venv from the main checkout.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root, so `agent` imports

from rapidfuzz import process
from rapidfuzz.distance import OSA

from agent.cli import load_agent

T3 = [
    "Who directed ''Inception''?",
    "Who directed ' Inception'?",
    "Who directed 'Inception '?",
    "Who directed ''The Godfather''?",
    "Who directed 'Inception.'?",
    "Who directed Inception'?",
    "Who directed Inception?'",
    '"Who directed Inception?"',
    "Who directed 'inception'?",
]

T4 = [
    "Who directed Godfahter?",
    "Who directed Godfather?",
    "Who directed Terminater?",
    "Who directed Pulp Ficton?",
    "Who directed Schindlers List?",
    "Who directed Jazws?",
    "Who directed Forrst Gump?",
]

T2_TITLES = ["growing up", "looking up", "it follows", "up in the air", "don't look up",
             "no country for old men", "noah", "up", "it", "her", "us", "nine", "giant"]


def main() -> int:
    agent = load_agent()
    parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))
    lex = parser.lex

    print("== candidate longer titles (T2 dataset): label presence in the KG ==")
    for title in T2_TITLES:
        ids = lex.lbl2ent.get(title, [])
        print(f"{title!r:26s} -> {ids[:4]}{' ...' if len(ids) > 4 else ''}")

    print("\n== T3 quote variants ==")
    for text in T3:
        span, candidates = parser._find_entity(text)
        reply = agent.answer(text, "s3b")
        print(f"{text!r}\n  span={span} candidates={candidates[:3]}\n  reply={reply[:180]!r}")

    print("\n== T4 typo wrong-links (fuzzy top 3 + reply) ==")
    for text in T4:
        last = text.rstrip("? ").split()[-1]
        matches = process.extract(last.lower(), parser.fuzzy_labels, scorer=OSA.normalized_similarity,
                                  score_cutoff=0.80, limit=3)
        print(f"{text!r}\n  fuzzy={[(m[0], round(m[1], 3), lex.lbl2ent[m[0]][:2]) for m in matches]}")
        reply = agent.answer(text, "s3b")
        print(f"  reply={reply[:180]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
