"""Triage: measure the fail rate of D1-D8 with ~6 varied cases each, to rank impact.

Run from the repo root (worktree) with the venv from the main checkout.
A case "fails" when the reply does not satisfy the correct behaviour of that type.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root, so `agent` imports

from agent.cli import load_agent

WD = "http://www.wikidata.org/entity/"
WDT = "http://www.wikidata.org/prop/direct/"

# (type, input, relation, entity, direction) - correctness computed from the KG where possible
COUNT_CASES = [
    ("D1", "How many awards did 'Inception' win?", "P166", "Q25188", "out"),
    ("D1", "How many awards has Meryl Streep won?", "P166", "Q873", "out"),
    ("D1", "How many cast members does 'Inception' have?", "P161", "Q25188", "out"),
    ("D1", "How many genres does 'The Godfather' have?", "P136", "Q47703", "out"),
    ("D1", "How many awards did 'The Godfather' win?", "P166", "Q47703", "out"),
    ("D1", "How many films has Steven Spielberg directed?", "P57", "Q8877", "in"),
]

PATTERN_CASES = [
    # (type, input, must_not_contain, must_contain or None)
    ("D2", "I love 'Jaws'. Who directed 'Inception'?", "steven spielberg", "christopher nolan"),
    ("D2", "Who directed 'The Godfather'? Who directed 'Inception'?", "francis ford coppola", "christopher nolan"),
    ("D2", "I love Jaws. Who directed Inception?", None, "christopher nolan"),
    ("D2", "In 'Jaws'... actually, who wrote 'Inception'?", "steven spielberg", "christopher nolan"),
    ("D2", "The Godfather is great. Who composed the music for Inception?", "francis ford coppola", "hans zimmer"),
    ("D2", "My favourite film is Jaws. When did Inception come out?", "spielberg", "2010"),
    ("D3", "Who directed 'Batman Begins', the first film in the trilogy?", None, "christopher nolan"),
    ("D3", "Who wrote the screenplay of 'The Godfather', the first film of the trilogy?", None, "mario puzo"),
    ("D3", "Who composed the music for 'Inception', the latest film I watched?", None, "hans zimmer"),
    ("D3", "Who directed 'Inception', my first Nolan film?", None, "christopher nolan"),
    ("D3", "Who directed 'Jaws', the last film I saw?", None, "steven spielberg"),
    ("D3", "Who starred in 'Inception', the first film in the list?", None, "leonardo dicaprio"),
    ("D4", "who directed 'Amelie'?", "not sure", "jean-pierre jeunet"),
    ("D4", "who directed 101 reykjavik?", "director of 101\".", "baltasar"),
    ("D4", "who directed 'the matrix'?", None, "wachowski"),
    ("D4", "who directed 8 1/2?", "director of 2", "fellini"),
    ("D4", "who directed 3 iron?", "not sure", "kim ki-duk"),
    ("D4", "who directed 50 50?", "not sure", "levine"),
    ("D5", "Did Steven Spielberg direct 'Inception'?", "christopher nolan", "no"),
    ("D5", "Did Christopher Nolan direct 'Jaws'?", "steven spielberg", "no"),
    ("D5", "Was 'Inception' directed by Steven Spielberg?", "christopher nolan", "no"),
    ("D5", "Did Christopher Nolan direct 'Inception'?", "christopher nolan", "yes"),
    ("D5", "Did Steven Spielberg direct 'Jaws'?", "steven spielberg", "yes"),
    ("D5", "Did Alfred Hitchcock direct 'The Godfather'?", "coppola", "no"),
    ("D6", "When did 'The Blue Bird Vol. 2' come out?", "t00:00:00", None),
    ("D6", "When was 'Tokyo Chorus II' released?", "t00:00:00", None),
    ("D6", "When did the movie 'Manchester by the Sea' come out?", None, "2016-01-23"),
    ("D6", "When did 'Inception' come out?", None, "2010-07-08"),
    ("D6", "When did 'Interstellar' come out?", None, "2014"),
    ("D6", "When was 'The Godfather' released?", None, "1972"),
    ("D7", "Whodirected 'Inception'?", "no information", "christopher nolan"),
    ("D7", "who directedinception?", "not sure", "christopher nolan"),
    ("D7", "Who directed 'Inception'?", None, "christopher nolan"),
    ("D7", "Who wrote'Inception'?", "not sure", "christopher nolan"),
    ("D7", "Whodirected Jaws?", "not sure", "steven spielberg"),
    ("D7", "Who directedthe godfather?", "not sure", "coppola"),
    ("D8", "Who did the directing for 'Inception'?", "not sure about", "christopher nolan"),
    ("D8", "Who was at the helm of 'Inception'?", "not sure about", "christopher nolan"),
    ("D8", "Who is behind the camera on 'Inception'?", "not sure about", "christopher nolan"),
    ("D8", "Who did the directing for 'Jaws'?", "not sure about", "steven spielberg"),
    ("D8", "Who was at the helm of 'The Godfather'?", "not sure about", "francis ford coppola"),
    ("D8", "Who is behind the camera on 'Jaws'?", "not sure about", "steven spielberg"),
]


def main() -> int:
    agent = load_agent()
    kg = agent.handlers[0].kg
    fails = {}
    totals = {}

    print("== D1 count cases (fail when the reply is 0 but the truth is not 0) ==")
    for type_id, text, prop, entity, direction in COUNT_CASES:
        triple = (f"<{WD}{entity}> <{WDT}{prop}> ?x" if direction == "out" else f"?x <{WDT}{prop}> <{WD}{entity}>")
        truth = int(kg.query(f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ {triple} }}").rows[0][0].value)
        reply = agent.answer(text, "triage")
        failed = reply.strip().endswith(": 0") and truth > 0
        totals[type_id] = totals.get(type_id, 0) + 1
        fails[type_id] = fails.get(type_id, 0) + failed
        print(f"{'FAIL' if failed else 'pass'} {text!r} truth={truth} reply={reply[:90]!r}")

    print("\n== D2-D8 pattern cases ==")
    for type_id, text, must_not, must_contain in PATTERN_CASES:
        reply = agent.answer(text, "triage")
        low = reply.casefold()
        failed = False
        if must_not and must_not in low:
            failed = True
        if must_contain and must_contain not in low:
            failed = True
        totals[type_id] = totals.get(type_id, 0) + 1
        fails[type_id] = fails.get(type_id, 0) + failed
        print(f"{'FAIL' if failed else 'pass'} {text!r} reply={reply[:110]!r}")

    print("\n== triage summary (fail rate) ==")
    for type_id in sorted(totals, key=lambda t: -fails[t] / totals[t]):
        print(f"{type_id}: {fails[type_id]}/{totals[type_id]} fail ({fails[type_id] / totals[type_id]:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
