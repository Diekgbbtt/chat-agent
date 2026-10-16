"""S3 probe: candidate red/green cases per known type, with real KG values.

Run from the repo root (worktree) with the venv from the main checkout:
    /Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/s3_probe.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root, so `agent` imports

from rapidfuzz import process
from rapidfuzz.distance import OSA

from agent.cli import load_agent
from agent.core import Trace

T3_CASES = [
    "who directed inception",
    "WHO DIRECTED INCEPTION?",
    'Who directed "Inception"?',
    "Who directed 'Inception' (2010)?",
    "Who directed Inception (2010 film)?",
    "who directed \u201cthe handmaiden\u201d?",
    "Who directed 'the handmaiden'?",
    "Who directed The Handmaiden?",
    "Who directed the handmaiden?",
    "Who wrote 'The Handmaiden's screenplay?",
    "Who directed '12 Angry Men'?",
    "Who directed ''Inception''?",
    "Who directed 'Inception ?",
    "Who directed the movie 'Inception'?",
]

T2_CASES = [
    "Who directed 'Don't Look Up'?",
    "Who directed Don't Look Up?",
    "who directed don't look up",
    "Who directed 'No Country for Old Men'?",
    "Who directed No Country for Old Men?",
    "who directed up",
    "Who directed 'Up'?",
    "Who directed 'It'?",
    "Who directed 'Us'?",
    "Who directed 'Her'?",
]

T5_CASES = [
    "who directed matrix",
    "who directed the matrix",
    "who wrote the screenplay of handmaiden",
    "Who directed Handmaiden?",
    "who directed godfather",
    "who directed the godfather",
    "who directed titanic",
]

T1_CASES = [
    "Which movies did Christopher Nolan not direct?",
    "Who did not direct 'Inception'?",
]

T4_SCORES = ["godfahter", "the godfahter", "intersteller", "incepton", "handmaiden", "godfather"]
T4_ENTITIES = ["Q5576354", "Q47703", "Q28008305", "Q174811", "Q13417189"]


def main() -> int:
    agent = load_agent()
    parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))
    lex = parser.lex

    print("== fuzzy scores (OSA normalized similarity >= 0.80) ==")
    for typo in T4_SCORES:
        matches = process.extract(typo, parser.fuzzy_labels, scorer=OSA.normalized_similarity,
                                  score_cutoff=0.80, limit=5)
        print(f"{typo!r}:")
        for label, score, _ in matches:
            ids = lex.lbl2ent[label]
            films = [q for q in ids if lex.is_film(q)]
            print(f"    {label!r:34s} score={score:.4f} ids={ids} film_ids={films}")

    print("\n== entity facts for the T2/T4 probes ==")
    for qid in T4_ENTITIES:
        print(f"{qid}: label={lex.label(qid)!r} is_film={lex.is_film(qid)} types={sorted(lex.types.get(qid, set()))[:4]}")
    for label in ("up", "it", "us", "her", "no country for old men", "don", "don't look up"):
        print(f"label {label!r}: {lex.lbl2ent.get(label, [])}")
    for qid in ("Q174811", "Q28008305"):
        print(f"{qid} label={lex.label(qid)!r}")

    for name, cases in (("T3", T3_CASES), ("T2", T2_CASES), ("T5", T5_CASES), ("T1", T1_CASES)):
        print(f"\n== {name} cases ==")
        for text in cases:
            span, candidates = parser._find_entity(text)
            trace = Trace()
            reply = agent.answer(text, "s3", trace)
            verdict = "?"
            print(f"{text!r}\n  span={span} candidates={candidates[:4]}\n  reply={reply[:220]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
