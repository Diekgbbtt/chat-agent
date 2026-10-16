#!/usr/bin/env python3
"""G5 check for the adversarial datasets: row count, unique ids, non-empty input/expected.

Prints "datasets OK" when every file passes.

Run: .venv/bin/python scripts/adversarial/check_datasets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    files = sorted((ROOT / "evals" / "adversarial").glob("*.jsonl"))
    if not files:
        print("no dataset files under evals/adversarial/")
        return 1
    problems = []
    for path in files:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(rows) < 50:
            problems.append(f"{path.name}: only {len(rows)} rows (need >= 50)")
        ids = [r.get("id") for r in rows]
        if len(set(ids)) != len(ids):
            problems.append(f"{path.name}: duplicate ids")
        for r in rows:
            if not isinstance(r.get("input"), str) or not r["input"].strip():
                problems.append(f"{path.name}: {r.get('id')} has empty input")
            expected = r.get("expected")
            if not expected or not all(isinstance(e, str) and e.strip() for e in expected):
                problems.append(f"{path.name}: {r.get('id')} has empty expected")
            forbidden = r.get("forbidden", [])
            if not all(isinstance(f, str) and f.strip() for f in forbidden):
                problems.append(f"{path.name}: {r.get('id')} has an empty forbidden entry")
    if problems:
        print("\n".join(problems))
        print("datasets NOT OK")
        return 1
    print(f"{len(files)} files checked")
    print("datasets OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
