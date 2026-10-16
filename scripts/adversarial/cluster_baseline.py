#!/usr/bin/env python3
"""S6: cluster the iter0 baseline failures per type and write the `<type>-baseline.md` reports.

Reads `docs/design/adversarial/eval/iter0/<type>.log` plus the dataset files, groups every
FAIL by reply shape, and emits the report next to the log. Cluster counts sum to the failure
total by construction.

Run: .venv/bin/python scripts/adversarial/cluster_baseline.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ITER = ROOT / "docs/design/adversarial/eval/iter0"
DATASETS = ROOT / "evals" / "adversarial"

TYPES = ["t1-negation", "t2-subvention", "t3-quote-shapes", "t4-typos", "t5-partial-titles",
         "d1-count-class", "d2-multiple-mentions", "d3-trailing-superlative", "d5-yes-no",
         "d8-relation-paraphrases"]


def parse_log(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    summary = re.search(r"(\d+)/(\d+) passed\. Latency: median ([\d.]+) s, max ([\d.]+) s", text)
    passed, total, median, maximum = summary.groups()
    cases, cur = [], None
    for line in text.splitlines():
        match = re.match(r"^(PASS|FAIL) (\S+): (.*)$", line)
        if match:
            cur = {"status": match.group(1), "id": match.group(2)}
            cases.append(cur)
        elif line.startswith("  -> ") and cur is not None:
            cur["reply"] = line[5:]
    return {"passed": int(passed), "total": int(total), "median": median, "max": maximum, "cases": cases}


def classify(reply: str, case: dict) -> str:
    r = reply.casefold().strip()
    forbidden = case.get("forbidden", [])
    clarify = any(e.casefold().startswith("i'm not sure which movie or person you mean")
                  for e in case.get("expected", []))
    if r.startswith("i'm not sure which movie or person you mean"):
        return "safe failure (no_entity reply)"
    if r.startswith("sorry, my knowledge graph has no information"):
        return "relation refused (no_facts reply)"
    if "not sure what you'd like to know" in r:
        return "relation word ignored (no_relation reply)"
    if r == "the factual answer is: 0":
        return "wrong count: 0"
    if clarify and r.startswith("the factual answer is:"):
        return "answered instead of clarifying"
    hits = [f for f in forbidden if f and f.casefold() in r]
    if hits:
        return f"trap value returned ({hits[0]!r})"
    if r.startswith("the factual answer is:"):
        return "wrong answer: expected value absent"
    return "other"


def cell(text: str, limit: int = 110) -> str:
    text = " ".join(str(text).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_report(name: str) -> str:
    log = parse_log(ITER / f"{name}.log")
    dataset = [json.loads(line) for line in (DATASETS / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {c["id"]: c for c in dataset}
    fails = [c for c in log["cases"] if c["status"] == "FAIL"]
    clusters: dict[str, list[dict]] = {}
    for case in fails:
        clusters.setdefault(classify(case.get("reply", ""), by_id[case["id"]]), []).append(case)
    required = 0.8 * log["total"]
    pct = 100.0 * log["passed"] / log["total"]
    lines = [
        f"# {name} - baseline (iter0)",
        "",
        f"- Command: `.venv/bin/python -m agent.eval -v evals/adversarial/{name}.jsonl 2>&1 | tee docs/design/adversarial/eval/iter0/{name}.log`",
        f"- Log: `docs/design/adversarial/eval/iter0/{name}.log`",
        f"- Result: {log['passed']}/{log['total']} passed ({pct:.1f}%). Latency: median {log['median']} s, max {log['max']} s.",
        f"- Fix bar: pass rate >= 0.8, so at least {int(-(-required // 1))}/{log['total']} cases must pass.",
        "",
        "## Failure clusters",
        "",
        "| Cluster | Count | Example id | Example reply |",
        "|---|---|---|---|",
    ]
    for key, cases in sorted(clusters.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        example = cases[0]
        lines.append(f"| {cell(key)} | {len(cases)} | {example['id']} | {cell(example.get('reply', ''))} |")
    lines += [
        "",
        f"Total failures: {len(fails)} (sum of the cluster counts).",
        "",
        "## Failing cases",
        "",
        "| id | input | reply | cluster |",
        "|---|---|---|---|",
    ]
    for key, cases in sorted(clusters.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        for case in cases:
            lines.append(f"| {case['id']} | {cell(by_id[case['id']]['input'])} | "
                         f"{cell(case.get('reply', ''), 90)} | {cell(key, 60)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    for name in TYPES:
        report = build_report(name)
        path = ITER / f"{name}-baseline.md"
        path.write_text(report, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
