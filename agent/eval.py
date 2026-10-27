"""
Regression evaluation: python -m agent.eval [files...] [-v]

Each line of evals/*.jsonl is {"id": ..., "input": ..., "expected": [...], "forbidden": [...], "labels": [...]}.
A case passes when every expected string is in the reply (case-insensitive), no forbidden one is,
and, if "labels" is given, the guardrail labels in the trace are exactly those labels.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from agent.cli import load_agent
from agent.config import PROJECT_ROOT
from agent.core import Trace


def labels(trace: Trace):
    return next((set(detail) for step, detail in trace.steps if step == "labels"), None)


def passes(case: dict, reply: str, trace: Trace) -> bool:
    reply = reply.casefold()
    return (all(e.casefold() in reply for e in case.get("expected", []))
            and not any(f.casefold() in reply for f in case.get("forbidden", []))
            and ("labels" not in case or labels(trace) == set(case["labels"])))


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
        trace = Trace()
        start = time.perf_counter()
        reply = agent.answer(case["input"], f"eval-{case['id']}", trace)
        latencies.append(time.perf_counter() - start)
        ok = passes(case, reply, trace)
        failures += not ok
        if args.verbose or not ok:
            got = f" labels={sorted(labels(trace) or [])}" if "labels" in case else ""
            print(f"{'PASS' if ok else 'FAIL'} {case['id']}: {case['input'][:80]!r}{got}\n  -> {reply[:300]}")

    print(f"\n{len(cases) - failures}/{len(cases)} passed. Latency: median {statistics.median(latencies):.2f} s, "
          f"max {max(latencies):.2f} s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
