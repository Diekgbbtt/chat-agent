"""Run the ten adversarial datasets and write one verbose log per type.

Usage: python scripts/adversarial/run_iter.py --out docs/design/adversarial/eval/iter1

Uses `agent.eval.passes` unchanged, so the per-case verdicts match `python -m agent.eval -v`.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.cli import load_agent  # noqa: E402
from agent.eval import passes  # noqa: E402

DATASETS = [
    "t1-negation", "t2-subvention", "t3-quote-shapes", "t4-typos", "t5-partial-titles",
    "d1-count-class", "d2-multiple-mentions", "d3-trailing-superlative", "d5-yes-no",
    "d8-relation-paraphrases",
]


def run(agent, name: str, out: Path) -> tuple:
    path = ROOT / "evals/adversarial" / f"{name}.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines, latencies, passed = [], [], 0
    for case in cases:
        start = time.perf_counter()
        reply = agent.answer(case["input"], f"eval-{case['id']}")
        latencies.append(time.perf_counter() - start)
        ok = passes(case, reply)
        passed += ok
        lines.append(f"{'PASS' if ok else 'FAIL'} {case['id']}: {case['input'][:80]!r}\n  -> {reply[:300]}")
    lines.append(f"\n{passed}/{len(cases)} passed. Latency: median {statistics.median(latencies):.2f} s, "
                 f"max {max(latencies):.2f} s")
    (out / f"{name}.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed, len(cases)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="output directory for the per-type logs")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    agent = load_agent()
    rows = []
    for name in DATASETS:
        passed, total = run(agent, name, out)
        rows.append((name, passed, total))
        print(f"{name}: {passed}/{total}")
    table = ["| type | passed | total | rate |", "| --- | --- | --- | --- |"]
    for name, passed, total in rows:
        table.append(f"| {name} | {passed} | {total} | {passed / total:.2f} |")
    total_passed = sum(r[1] for r in rows)
    total_cases = sum(r[2] for r in rows)
    table.append(f"| **all** | **{total_passed}** | **{total_cases}** | **{total_passed / total_cases:.2f}** |")
    (out / "summary.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(f"all: {total_passed}/{total_cases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
