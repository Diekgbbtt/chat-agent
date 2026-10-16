"""S2 trace capture: real intermediate values for the phase-boundary contracts.

Run from the repo root (worktree) with the venv from the main checkout:
    /Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_traces.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root, so `agent` imports

from agent.cli import load_agent
from agent.core import Trace

QUESTIONS = [
    # happy path, one per shape
    "Who directed 'Inception'?",
    "Which films did Christopher Nolan direct?",
    "How many films did Christopher Nolan direct?",
    "What was the earliest film directed by Christopher Nolan?",
    "When did the movie 'Manchester by the Sea' come out?",
    # error paths
    "hello",
    "Who directed 'Qwzxv Plorbnik Unfilmable'?",
    "How tall is 'Inception'?",
    # T1 negation
    "Which movies did Christopher Nolan not direct?",
    "Who did not direct 'Inception'?",
    # T2 subvention
    "Who directed 'Don't Look Up'?",
    "Who directed Don't Look Up?",
    "who directed don't look up",
    # T3 quote shapes
    "Who directed Inception?",
    "Who directed \u201cInception\u201d?",
    "Who directed 'Inception?",
    # T4 typos
    "Who directed Godfahter?",
    "Who wrote the screenplay for Intersteller?",
    # T5 partial titles
    "Who wrote the screenplay for handmaiden?",
    "who directed the matrix",
]


def main() -> int:
    agent = load_agent()
    parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))

    for text in QUESTIONS:
        print(f"=== {text!r}")
        span, candidates = parser._find_entity(text)
        rest = text[:span[0]] + " " + text[span[1]:]
        predicates = parser._find_predicates(rest)
        print(f"  span={span} candidates={candidates}")
        print(f"  rest_after_span={rest!r} predicates={predicates}")
        trace = Trace()
        reply = agent.answer(text, "trace", trace)
        for step, detail in trace.steps:
            print(f"  [{step}] {detail}")
        print(f"  reply={reply[:400]!r}{' ...' if len(reply) > 400 else ''}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
