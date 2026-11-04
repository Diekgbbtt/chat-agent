"""The eval result contract and the scoreboard summary."""

import json

import pytest

from agent import eval as eval_module
from agent.config import load_settings
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
    assert record["discrimination"] is None
    assert record["classification"] is None
    assert record["final_response"] is None


def test_case_result_exposes_guard_and_submit_feedback():
    class FeedbackAgent(FakeAgent):
        def answer(self, text, session_id="local", trace=None):
            trace = trace or Trace()
            trace.add("labels", {"safe_in_scope"})
            trace.add("discrimination", {"summary": "one request", "spans": [{"index": 0}]})
            trace.add("classification", {"verbatims": [{"index": 0, "label": {"safety": "safe"}}]})
            trace.add("llm_step", {"step": 1, "tool_calls": [
                {"name": "resolve_entity", "arguments": {"query": "Jaws"}}]})
            trace.add("llm_step", {"step": 2, "tool_calls": [
                {"name": "submit_response", "arguments": {"parts": [{"verbatim_index": 0}]}}]})
            return "The answer is 42."

    record = eval_module.run_case(FeedbackAgent(), case())

    assert record["discrimination"] == {"summary": "one request", "spans": [{"index": 0}]}
    assert record["classification"]["verbatims"][0]["label"]["safety"] == "safe"
    assert record["final_response"] == {
        "step": 2,
        "name": "submit_response",
        "arguments": {"parts": [{"verbatim_index": 0}]},
    }


def test_final_response_picks_the_last_submit_call():
    trace = Trace()
    trace.add("llm_step", {"step": 1, "tool_calls": [
        {"name": "submit_response", "arguments": {"parts": [{"verbatim_index": 0}]}}]})
    trace.add("llm_step", {"step": 2, "tool_calls": [
        {"name": "submit_response", "arguments": {"parts": [{"verbatim_index": 1}]}}]})

    call = eval_module.final_response_call(trace)

    assert call["step"] == 2
    assert call["arguments"] == {"parts": [{"verbatim_index": 1}]}


def test_local_settings_force_llm_and_one_endpoint():
    base = load_settings()

    local = eval_module.local_settings(base, "http://127.0.0.1:9999/v1", "local-model", "local-key")

    assert local.agent_mode == "llm"
    assert local.local_base_url == "http://127.0.0.1:9999/v1"
    assert local.guard_base_url == local.qa_base_url == "http://127.0.0.1:9999/v1"
    assert local.guard_model == local.qa_model == "local-model"
    assert local.guard_api_key == local.qa_api_key == "local-key"


def test_local_settings_without_overrides_use_the_local_endpoint():
    base = load_settings()

    local = eval_module.local_settings(base)

    assert local.agent_mode == "llm"
    assert local.guard_base_url == base.local_base_url
    assert local.qa_base_url == base.local_base_url
    assert local.guard_model == base.local_model
    assert local.qa_model == base.local_model


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


def test_main_local_mode_uses_the_endpoint_and_writes_feedback(tmp_path, monkeypatch):
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(case()) + "\n", encoding="utf-8")
    out = tmp_path / "results.jsonl"
    seen = {}

    class EvalAgent(FakeAgent):
        def answer(self, text, session_id="local", trace=None):
            trace = trace or Trace()
            trace.add("labels", {"safe_in_scope"})
            trace.add("discrimination", {"summary": "one request", "spans": [{"index": 0}]})
            trace.add("classification", {"verbatims": [{"index": 0, "label": {"safety": "safe"}}]})
            trace.add("llm_step", {"step": 1, "tool_calls": [
                {"name": "submit_response", "arguments": {"parts": [{"verbatim_index": 0}]}}]})
            return "The answer is 42."

    def fake_load_agent(mode="", settings=None):
        seen["mode"] = mode
        seen["settings"] = settings
        return EvalAgent()

    monkeypatch.setattr(eval_module, "load_agent", fake_load_agent)
    monkeypatch.setenv("LOG_DIR", str(tmp_path))

    code = eval_module.main([str(cases), "--local", "--no-health-check",
                             "--base-url", "http://127.0.0.1:9999/v1",
                             "--model", "local-model", "--json", str(out)])

    assert code == 0
    assert seen["mode"] == "llm"
    assert seen["settings"].guard_base_url == "http://127.0.0.1:9999/v1"
    assert seen["settings"].qa_base_url == "http://127.0.0.1:9999/v1"
    record = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert record["discrimination"]["summary"] == "one request"
    assert record["classification"]["verbatims"][0]["label"]["safety"] == "safe"
    assert record["final_response"]["arguments"] == {"parts": [{"verbatim_index": 0}]}


def test_main_local_mode_rejects_an_unhealthy_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.serve.check",
                        lambda settings, timeout_s=None: {"guard": False, "qa": False})

    with pytest.raises(SystemExit, match="unhealthy"):
        eval_module.main([str(tmp_path / "cases.jsonl"), "--local",
                          "--base-url", "http://127.0.0.1:9/v1"])


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
