"""The eval result contract and the scoreboard summary."""

import json

from agent import eval as eval_module
from agent.core import Trace


class FakeAgent:
    def answer(self, text, session_id="local", trace=None):
        trace = trace or Trace()
        trace.add("labels", {"safe_in_scope"})
        return "The answer is 42."


def case(**overrides):
    value = {"id": "c1", "input": "Who?", "expected": ["42"], "labels": ["safe_in_scope"]}
    value.update(overrides)
    return value


def test_case_result_carries_the_contract_fields():
    record = eval_module.run_case(FakeAgent(), case())

    assert record["id"] == "c1"
    assert record["pass"] is True
    assert record["expected"] == ["42"]
    assert record["got_labels"] == ["safe_in_scope"]
    assert record["reply"] == "The answer is 42."
    assert isinstance(record["latency_s"], float)
    assert record["error"] is None


def test_case_result_records_a_guard_failure():
    record = eval_module.run_case(FakeAgent(), case(labels=["out_of_scope"]))

    assert record["pass"] is False
    assert record["expected_labels"] == ["out_of_scope"]
    assert record["got_labels"] == ["safe_in_scope"]


def test_case_result_records_an_exception():
    class Broken:
        def answer(self, *args, **kwargs):
            raise RuntimeError("boom")

    record = eval_module.run_case(Broken(), case())

    assert record["pass"] is False
    assert record["error"] == "boom"
    assert record["reply"] == ""


def test_json_results_are_one_object_per_line(tmp_path):
    path = tmp_path / "results.jsonl"
    records = [eval_module.run_case(FakeAgent(), case())]

    eval_module.write_results(path, records)

    lines = path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == "c1"


def test_named_suite_resolves_to_a_file():
    files = eval_module.resolve_files([], "stage1")

    assert [path.name for path in files] == ["stage1_sparql.jsonl"]


def test_unknown_suite_fails():
    try:
        eval_module.resolve_files([], "nope")
    except SystemExit as exc:
        assert "unknown suite" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_overlapping_label_sets_accept_either_explicit_label():
    class ToxicAgent(FakeAgent):
        def answer(self, text, session_id="local", trace=None):
            trace = trace or Trace()
            trace.add("labels", {"prompt_injection", "toxic"})
            return "I cannot help with that."

    overlapping = case(expected=[], labels_any_of=[["prompt_injection", "toxic"],
                                                   ["prompt_injection", "harmful"]])
    overlapping.pop("labels")

    record = eval_module.run_case(ToxicAgent(), overlapping)

    assert record["pass"] is True
    assert record["expected_labels"] == [["prompt_injection", "toxic"],
                                         ["prompt_injection", "harmful"]]


def test_overlapping_label_sets_reject_an_unlisted_set():
    record = eval_module.run_case(
        FakeAgent(),
        {"id": "c2", "input": "Who?", "expected": ["42"],
         "labels_any_of": [["harmful"], ["toxic"]]})

    assert record["pass"] is False
    assert record["got_labels"] == ["safe_in_scope"]
