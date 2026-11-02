"""Read eval JSONL results and print counts, failures, per-label recall, and latency."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def expected_labels(record) -> set:
    values = record.get("expected_labels", [])
    if values and isinstance(values[0], list):
        return {label for group in values for label in group}
    return set(values)


def summarize(records) -> dict:
    records = list(records)
    recall = defaultdict(lambda: {"passed": 0, "cases": 0})
    latencies = []
    failures = []
    for record in records:
        latencies.append(record.get("latency_s", 0.0))
        if not record.get("pass"):
            failures.append(record)
        for label in expected_labels(record):
            recall[label]["cases"] += 1
            recall[label]["passed"] += bool(record.get("pass"))
    for value in recall.values():
        value["rate"] = value["passed"] / value["cases"] if value["cases"] else 0.0
    return {
        "cases": len(records),
        "passed": sum(1 for record in records if record.get("pass")),
        "failed": len(failures),
        "failures": failures,
        "recall": dict(sorted(recall.items())),
        "latency_s": {
            "median": statistics.median(latencies) if latencies else 0.0,
            "max": max(latencies) if latencies else 0.0,
        },
    }


def render(summary) -> str:
    lines = [f"{summary['passed']}/{summary['cases']} passed, {summary['failed']} failed."]
    if summary["recall"]:
        lines.append("Per-label recall:")
        for label, value in summary["recall"].items():
            lines.append(f"  {label}: {value['passed']}/{value['cases']} ({value['rate']:.0%})")
    if summary["failures"]:
        lines.append("Failures:")
        lines.extend(f"  {record['id']}: {record.get('error') or record.get('reply', '')[:120]}"
                     for record in summary["failures"])
    lines.append(f"Latency: median {summary['latency_s']['median']:.2f} s, max {summary['latency_s']['max']:.2f} s")
    return "\n".join(lines)


def load(path) -> list:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    records = [record for path in args.paths for record in load(path)]
    summary = summarize(records)
    print(render(summary))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
