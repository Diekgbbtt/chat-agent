#!/usr/bin/env python3
"""S7 red-repro capture: run representative failing inputs per cluster through the current agent.

Each entry is (dataset file stem, case id). The script prints the case contract (expected,
forbidden), the parser internals, the trace steps, and the reply.

Run from the repo root (worktree) with the venv from the main checkout:
    /Users/diekgbbtt/atai-conversation-agent/.venv/bin/python scripts/adversarial/capture_repros.py \
      2>&1 | tee docs/design/adversarial/eval/s7-repros.log
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.cli import load_agent  # noqa: E402
from agent.core import Trace  # noqa: E402

REPROS = {
    "c-t1-negation": [
        ("t1-negation", "t1-negation-001"),   # film side, director, red
        ("t1-negation", "t1-negation-029"),   # film side, writer, red
        ("t1-negation", "t1-negation-039"),   # person side, red
        ("t1-negation", "t1-negation-057"),   # masking control, green
    ],
    "c-t2-subvention": [
        ("t2-subvention", "t2-subvention-001"),
        ("t2-subvention", "t2-subvention-002"),
        ("t2-subvention", "t2-subvention-003"),
    ],
    "c-t3-quote-shapes": [
        ("t3-quote-shapes", "t3-quote-shapes-001"),  # doubled quotes
        ("t3-quote-shapes", "t3-quote-shapes-024"),  # inner period
        ("t3-quote-shapes", "t3-quote-shapes-054"),  # inner question mark
        ("t3-quote-shapes", "t3-quote-shapes-010"),  # wrong link
    ],
    "c-t4-typos": [
        ("t4-typos", "t4-typos-003"),  # no_entity
        ("t4-typos", "t4-typos-031"),  # no_entity
        ("t4-typos", "t4-typos-002"),  # wrong link
        ("t4-typos", "t4-typos-033"),  # wrong title
    ],
    "c-t5-partials": [
        ("t5-partial-titles", "t5-partial-titles-001"),  # no_entity
        ("t5-partial-titles", "t5-partial-titles-006"),  # no_facts
        ("t5-partial-titles", "t5-partial-titles-035"),  # wrong title
        ("t5-partial-titles", "t5-partial-titles-007"),  # wrong link
        ("t5-partial-titles", "t5-partial-titles-045"),  # clarify case
    ],
    "c-d1-counts": [
        ("d1-count-class", "d1-count-class-001"),
        ("d1-count-class", "d1-count-class-002"),
        ("d1-count-class", "d1-count-class-036"),
    ],
    "c-d2-multi-mention": [
        ("d2-multiple-mentions", "d2-multiple-mentions-001"),
        ("d2-multiple-mentions", "d2-multiple-mentions-002"),
    ],
    "c-d3-trailing": [
        ("d3-trailing-superlative", "d3-trailing-superlative-001"),
        ("d3-trailing-superlative", "d3-trailing-superlative-002"),
        ("d3-trailing-superlative", "d3-trailing-superlative-005"),  # green control
    ],
    "c-d5-yes-no": [
        ("d5-yes-no", "d5-yes-no-001"),  # true claim, Yes
        ("d5-yes-no", "d5-yes-no-002"),  # true claim, quoted, Yes
        ("d5-yes-no", "d5-yes-no-003"),  # false claim, No
    ],
    "c-d8-paraphrases": [
        ("d8-relation-paraphrases", "d8-relation-paraphrases-001"),  # nominalisation
        ("d8-relation-paraphrases", "d8-relation-paraphrases-002"),  # idiom, helm
        ("d8-relation-paraphrases", "d8-relation-paraphrases-003"),  # idiom, camera
        ("d8-relation-paraphrases", "d8-relation-paraphrases-061"),  # control
    ],
}


def load_case(dataset: str, case_id: str) -> dict:
    path = ROOT / "evals" / "adversarial" / f"{dataset}.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["id"] == case_id:
                return row
    raise KeyError(f"{case_id} not found in {path}")


def main() -> int:
    agent = load_agent()
    parser = next(h.parser for h in agent.handlers if hasattr(h, "parser"))

    for cluster, entries in REPROS.items():
        print(f"\n{'=' * 72}\n## {cluster}\n")
        for dataset, case_id in entries:
            case = load_case(dataset, case_id)
            text = case["input"]
            print(f"--- {case_id}")
            print(f"input: {text!r}")
            print(f"expected: {case.get('expected')}")
            print(f"forbidden: {case.get('forbidden')}")
            try:
                span, candidates = parser._find_entity(text)
                rest = text[: span[0]] + " " + text[span[1]:]
                predicates = parser._find_predicates(rest)
                print(f"span={span} candidates={candidates}")
                print(f"rest_after_span={rest!r} predicates={predicates}")
            except Exception as exc:  # pragma: no cover - diagnostics only
                print(f"parser internals failed: {exc!r}")
            trace = Trace()
            try:
                reply = agent.answer(text, "repro", trace)
            except Exception as exc:  # pragma: no cover - diagnostics only
                reply = f"<exception {exc!r}>"
            for step, detail in trace.steps:
                print(f"  [{step}] {detail}")
            print(f"reply={reply[:400]!r}{' ...' if len(reply) > 400 else ''}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
