"""Regression evaluation: python -m agent.eval [files...] [-v] [--json PATH]

Each line of evals/*.jsonl is {"id": ..., "input": ..., "expected": [...], "forbidden": [...], "labels": [...]}.
A case may instead carry "labels_any_of": [[...], [...]] for inherently overlapping types.
A case passes when every expected string is in the reply (case-insensitive), no forbidden one is,
and the guardrail labels match the exact set or one of the accepted sets.
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

SUITES = {
    "stage1": "stage1_sparql.jsonl",
    "stage2": "stage2_factual.jsonl",
    "negation": "stage2_factual_negation.jsonl",
    "guard": "stage3_guardrails.jsonl",
    "policy": "stage3_policy.jsonl",
    "redteam": "stage3_redteam.jsonl",
    "heldout": "stage3_heldout.jsonl",
    "e2e": "stage3_e2e.jsonl",
}


def labels(trace: Trace):
    return next((set(detail) for step, detail in trace.steps if step == "labels"), None)


def acceptable_labels(case: dict):
    if "labels" in case:
        return [set(case["labels"])]
    if "labels_any_of" in case:
        return [set(item) for item in case["labels_any_of"]]
    return None


def passes(case: dict, reply: str, trace: Trace) -> bool:
    reply = reply.casefold()
    allowed = acceptable_labels(case)
    label_ok = allowed is None or labels(trace) in allowed
    return (all(e.casefold() in reply for e in case.get("expected", []))
            and not any(f.casefold() in reply for f in case.get("forbidden", []))
            and label_ok)


def run_case(agent, case: dict) -> dict:
    """Run one case and capture the result contract, including a transport error."""
    trace = Trace()
    start = time.perf_counter()
    reply, error = "", None
    try:
        reply = agent.answer(case["input"], f"eval-{case['id']}", trace)
    except Exception as exc:  # noqa: BLE001 - the eval records the failure, it does not hide it
        error = str(exc) or exc.__class__.__name__
    latency = time.perf_counter() - start
    got = labels(trace)
    ok = error is None and passes(case, reply, trace)
    return {
        "id": case["id"],
        "input": case["input"],
        "pass": ok,
        "expected": list(case.get("expected", [])),
        "forbidden": list(case.get("forbidden", [])),
        "expected_labels": (list(case["labels"]) if "labels" in case
                            else [list(item) for item in case.get("labels_any_of", [])]),
        "got_labels": sorted(got) if got is not None else [],
        "reply": reply,
        "latency_s": latency,
        "error": error,
    }


def write_results(path, records) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def resolve_files(files, suite: str = "") -> list:
    if suite:
        if suite not in SUITES:
            raise SystemExit(f"unknown suite: {suite}")
        return [PROJECT_ROOT / "evals" / SUITES[suite]]
    return list(files) or sorted((PROJECT_ROOT / "evals").glob("*.jsonl"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", metavar="PATH", help="write one result object per case")
    parser.add_argument("--suite", help="named eval suite")
    parser.add_argument("--mode", choices=["legacy", "llm"], help="runtime mode override")
    args = parser.parse_args(argv)

    files = resolve_files(args.files, args.suite)
    cases = [json.loads(line) for f in files for line in Path(f).read_text(encoding="utf-8").splitlines() if line.strip()]
    agent = load_agent(args.mode)

    records, failures, latencies = [], 0, []
    for case in cases:
        record = run_case(agent, case)
        records.append(record)
        failures += not record["pass"]
        latencies.append(record["latency_s"])
        if args.verbose or not record["pass"]:
            got = f" labels={record['got_labels']}" if "labels" in case else ""
            print(f"{'PASS' if record['pass'] else 'FAIL'} {case['id']}: {case['input'][:80]!r}{got}\n"
                  f"  -> {record['reply'][:300]}")

    if args.json:
        write_results(args.json, records)

    if latencies:
        print(f"\n{len(cases) - failures}/{len(cases)} passed. "
              f"Latency: median {statistics.median(latencies):.2f} s, max {max(latencies):.2f} s")
    else:
        print("\n0/0 passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
