#!/usr/bin/env python3
"""G5 re-validation: 5 random cases per dataset file, checked with an independent KG query.

The grounding.check query is re-run and the expected condition is asserted per case:
  expected_in_rows  - every expected string appears in a returned cell
  forbidden_in_rows - every forbidden string appears in a returned cell
  expected_count    - the returned count equals expected[0]
  ask_yesno         - the ASK result matches "yes" in expected[0]
  no_film_rows      - the query returns no row (no film among the candidate entities)

Run: .venv/bin/python scripts/adversarial/verify_datasets.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.cli import load_agent  # noqa: E402

SEED = 20261016
SAMPLES = 5
TEMPLATE_SENTINELS = ("the factual answer is", "not sure which movie or person you mean",
                      "no information", "i'm not sure what you'd like to know")


def main() -> int:
    agent = load_agent()
    handler = next(h for h in agent.handlers if hasattr(h, "parser"))
    kg = handler.kg
    rng = random.Random(SEED)
    failures = 0
    for path in sorted((ROOT / "evals" / "adversarial").glob("*.jsonl")):
        file_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        sample = rng.sample(file_rows, min(SAMPLES, len(file_rows)))
        print(f"\n## {path.name} ({len(sample)}/{len(file_rows)} sampled, seed {SEED})")
        for case in sample:
            g = case.get("grounding") or {}
            res = kg.query(g["check"], timeout=120)
            kind = g["assert"]
            qrows = getattr(res, "rows", [])
            cells = [c.value for row in qrows for c in row if c is not None]
            if kind == "expected_in_rows":
                needles = case.get("expected", [])
                ok = all(any(n.casefold() in c.casefold() for c in cells) for n in needles)
                detail = f"expected {needles} found" if ok else f"expected {needles} MISSING"
            elif kind == "forbidden_in_rows":
                needles = [n for n in case.get("forbidden", [])
                           if not any(n.casefold().startswith(s) for s in TEMPLATE_SENTINELS)]
                ok = bool(needles) and all(any(n.casefold() in c.casefold() for c in cells) for n in needles)
                detail = f"forbidden values {needles} confirmed in KG" if ok else f"forbidden {needles} MISSING"
            elif kind == "expected_count":
                got = cells[0] if cells else None
                ok = got == case["expected"][0]
                detail = f"count {got} == {'/'.join(case['expected'])}" if ok else f"count {got} != expected"
            elif kind == "ask_yesno":
                want = "yes" in case["expected"][0].casefold()
                ok = bool(res) == want
                detail = f"ASK={bool(res)} matches expected {'Yes' if want else 'No'}"
            elif kind == "no_film_rows":
                ok = len(qrows) == 0
                detail = "no film row" if ok else "unexpected film row"
            else:
                ok, detail = False, f"unknown assert kind {kind!r}"
            failures += not ok
            status = "VERIFIED" if ok else "FAILED"
            print(f"- {case['id']}: {case['input'][:72]!r}")
            print(f"  {status}: {detail}")
            print(f"  query: {g['check'][:150]}")
    print(f"\nsummary: {failures} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
