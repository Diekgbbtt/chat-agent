"""Regression evaluation: python -m agent.eval [files...] [-v] [--json PATH] [--local]

Each line of evals/*.jsonl is {"id": ..., "input": ..., "expected": [...], "forbidden": [...], "labels": [...]}.
A case may instead carry "labels_any_of": [[...], [...]] for inherently overlapping types.
A case passes when every expected string is in the reply (case-insensitive), no forbidden one is,
and the guardrail labels match the exact set or one of the accepted sets.
--local runs the llm runtime against the local vLLM endpoint.
Each result also carries the guard discrimination, classification, and final submit_response call.
"""

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

from agent.cli import load_agent
from agent.config import PROJECT_ROOT, load_settings
from agent.core import Trace
from agent.observability import configure_logging, to_jsonable

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


def trace_detail(trace: Trace, name: str):
    """The last value of one trace step, or None when the step did not run."""
    for step, detail in reversed(trace.steps):
        if step == name:
            return detail
    return None


def final_response_call(trace: Trace):
    """The last submit_response tool call from the QA logs, or None."""
    for step, detail in reversed(trace.steps):
        if step != "llm_step":
            continue
        for call in reversed(detail.get("tool_calls") or []):
            if call.get("name") == "submit_response":
                return {"step": detail.get("step"),
                        "name": "submit_response",
                        "arguments": call.get("arguments")}
    return None


def response_kinds(trace: Trace) -> list:
    """The part kinds in the final submit_response call, in order."""
    call = final_response_call(trace)
    if call is None:
        return []
    arguments = call.get("arguments") or {}
    return [part.get("kind") for part in arguments.get("parts") or []]


def local_settings(settings, base_url: str = "", model: str = "", api_key: str = ""):
    """Point both roles at one local vLLM endpoint in llm mode."""
    base_url = base_url or settings.local_base_url
    model = model or settings.local_model
    changes = {"agent_mode": "llm",
               "local_base_url": base_url, "guard_base_url": base_url, "qa_base_url": base_url,
               "local_model": model, "guard_model": model, "qa_model": model}
    if api_key:
        changes.update(guard_api_key=api_key, qa_api_key=api_key)
    return replace(settings, **changes)


def labels(trace: Trace):
    return next((set(detail) for step, detail in trace.steps if step == "labels"), None)


def acceptable_labels(case: dict):
    if "labels" in case:
        return [set(case["labels"])]
    if "labels_any_of" in case:
        return [set(item) for item in case["labels_any_of"]]
    return None


def expected_text(value: str) -> str:
    """Drop the legacy response wrapper from an expected value."""
    prefix = "the factual answer is: "
    text = value[len(prefix):] if value.casefold().startswith(prefix) else value
    return text.removesuffix("T00:00:00")


def contains_expected(reply: str, expected: str) -> bool:
    """Case-insensitive containment with numeric comma normalisation."""
    value = expected_text(expected).casefold()
    if value.isdigit():
        return value in reply.replace(",", "")
    return value in reply


def passes(case: dict, reply: str, trace: Trace) -> bool:
    reply = reply.casefold()
    allowed = acceptable_labels(case)
    label_ok = allowed is None or labels(trace) in allowed
    expected_kinds = case.get("expected_kinds")
    kinds_ok = expected_kinds is None or response_kinds(trace) == list(expected_kinds)
    return (all(contains_expected(reply, e) for e in case.get("expected", []))
            and not any(f.casefold() in reply for f in case.get("forbidden", []))
            and label_ok and kinds_ok)


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
        "request_id": trace.request_id,
        "input": case["input"],
        "pass": ok,
        "expected": list(case.get("expected", [])),
        "forbidden": list(case.get("forbidden", [])),
        "expected_labels": (list(case["labels"]) if "labels" in case
                            else [list(item) for item in case.get("labels_any_of", [])]),
        "got_labels": sorted(got) if got is not None else [],
        "expected_kinds": list(case.get("expected_kinds", [])),
        "got_kinds": response_kinds(trace),
        "reply": reply,
        "discrimination": trace_detail(trace, "discrimination"),
        "classification": trace_detail(trace, "classification"),
        "final_response": final_response_call(trace),
        "latency_s": latency,
        "error": error,
    }


def write_results(path, records) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(to_jsonable(record), ensure_ascii=False) + "\n")


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
    parser.add_argument("--local", action="store_true",
                        help="run the llm runtime against the local vLLM endpoint")
    parser.add_argument("--base-url", default="",
                        help="local vLLM base URL; implies --local")
    parser.add_argument("--model", default="",
                        help="local vLLM model id; implies --local")
    parser.add_argument("--api-key", default="",
                        help="local vLLM API key; implies --local")
    parser.add_argument("--no-health-check", action="store_true",
                        help="skip the local endpoint probe")
    args = parser.parse_args(argv)

    settings = load_settings()
    local = bool(args.local or args.base_url or args.model or args.api_key)
    if local:
        settings = local_settings(settings, args.base_url, args.model, args.api_key)
        print(f"Local eval endpoint: {settings.guard_base_url} model={settings.guard_model}")
        if not args.no_health_check:
            from agent.serve import check
            status = check(settings, timeout_s=5.0)
            if not all(status.values()):
                raise SystemExit(f"Local model endpoint is unhealthy: {status}. "
                                 "Start vLLM or pass --no-health-check.")

    files = resolve_files(args.files, args.suite)
    cases = [json.loads(line) for f in files for line in Path(f).read_text(encoding="utf-8").splitlines() if line.strip()]
    configure_logging(settings)
    agent = load_agent("llm" if local else (args.mode or ""), settings=settings)

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
            if args.verbose:
                for field in ("discrimination", "classification", "final_response"):
                    if record[field] is not None:
                        detail = json.dumps(to_jsonable(record[field]), ensure_ascii=False)
                        print(f"  {field}: {detail[:500]}")

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
