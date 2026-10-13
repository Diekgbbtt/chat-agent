"""
Regression evaluation: python -m agent.eval [files...] [-v]

Each line of evals/*.jsonl is {"id": ..., "input": ..., "expected": [...], "forbidden": [...]}.
A case passes when every expected string is in the reply (case-insensitive) and no forbidden one is.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from agent.cli import load_agent
from agent.config import PROJECT_ROOT


def passes(case: dict, reply: str) -> bool:
    reply = reply.casefold()
    return (all(e.casefold() in reply for e in case.get("expected", []))
            and not any(f.casefold() in reply for f in case.get("forbidden", [])))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    files = args.files or sorted((PROJECT_ROOT / "evals").glob("*.jsonl"))
    cases = [json.loads(line) for f in files for line in Path(f).read_text(encoding="utf-8").splitlines() if line.strip()]
    agent = load_agent()

    failures, latencies = 0, []
    for case in cases:
        start = time.perf_counter()
        reply = agent.answer(case["input"], f"eval-{case['id']}")
        latencies.append(time.perf_counter() - start)
        ok = passes(case, reply)
        failures += not ok
        if args.verbose or not ok:
            print(f"{'PASS' if ok else 'FAIL'} {case['id']}: {case['input'][:80]!r}\n  -> {reply[:300]}")

    print(f"\n{len(cases) - failures}/{len(cases)} passed. Latency: median {statistics.median(latencies):.2f} s, "
          f"max {max(latencies):.2f} s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
