"""The agent writes one complete, correlated trace for every answer."""

import json
import logging
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from agent.core import Agent, Trace
from agent.llm.client import LLMClient
from agent.observability import configure_logging, reset_logging, to_jsonable


@pytest.fixture(autouse=True)
def clean_logging():
    reset_logging()
    yield
    reset_logging()


def settings(tmp_path, **overrides):
    values = dict(log_dir=str(tmp_path), agent_log_file="", agent_log_level="DEBUG")
    values.update(overrides)
    return SimpleNamespace(**values)


def records(tmp_path):
    lines = (tmp_path / "agent.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@dataclass
class Point:
    x: int
    y: int


def test_json_values_handle_dataclasses_sets_and_errors():
    assert to_jsonable({"point": Point(1, 2), "tags": {"b", "a"}}) == {
        "point": {"x": 1, "y": 2},
        "tags": ["a", "b"],
    }
    assert to_jsonable(ValueError("bad")) == {"type": "ValueError", "message": "bad"}


def test_one_answer_writes_a_complete_trace(tmp_path):
    configure_logging(settings(tmp_path))

    class Echo:
        name = "echo"

        def can_handle(self, text, session):
            return True

        def handle(self, text, session, trace):
            trace.add("detail", {"tags": {"b", "a"}})
            return "ok"

    assert Agent([Echo()]).answer("hi", "room-1") == "ok"

    trace = next(record for record in records(tmp_path) if record["event"] == "trace")
    payload = trace["fields"]["trace"]
    assert payload["request_id"]
    assert payload["session_id"] == "room-1"
    assert payload["input"] == "hi"
    assert payload["handler"] == "echo"
    assert payload["reply"] == "ok"
    assert payload["error"] == ""
    assert payload["duration_ms"] is not None
    assert payload["steps"] == [{"step": "handler", "detail": "echo"},
                                {"step": "detail", "detail": {"tags": ["a", "b"]}}]


def test_every_event_has_the_same_request_id(tmp_path):
    configure_logging(settings(tmp_path))

    class Echo:
        name = "echo"

        def can_handle(self, text, session):
            return True

        def handle(self, text, session, trace):
            trace.add("detail", "one")
            return "ok"

    Agent([Echo()]).answer("hi", "room-1")

    trace = next(record for record in records(tmp_path) if record["event"] == "trace")
    request_id = trace["fields"]["trace"]["request_id"]
    events = [record for record in records(tmp_path) if record["event"] != "trace"]
    assert events
    assert {record["request_id"] for record in events} == {request_id}
    assert {record["event"] for record in events} >= {"request.start", "trace.step"}


def test_failure_is_logged_with_the_trace(tmp_path):
    configure_logging(settings(tmp_path))

    class Broken:
        name = "broken"

        def can_handle(self, text, session):
            return True

        def handle(self, text, session, trace):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        Agent([Broken()]).answer("hi", "room-1")

    rows = records(tmp_path)
    assert any(record["event"] == "request.error" for record in rows)
    trace = next(record for record in rows if record["event"] == "trace")
    payload = trace["fields"]["trace"]
    assert payload["error"] == "RuntimeError: boom"
    assert payload["handler"] == "broken"


def test_trace_is_available_in_process():
    trace = Trace()
    trace.add("answer", {"values": {"b", "a"}})

    payload = json.loads(trace.to_json())

    assert payload["request_id"] == trace.request_id
    assert payload["steps"] == [{"step": "answer", "detail": {"values": ["a", "b"]}}]


def test_cli_can_write_a_trace_json(tmp_path):
    from agent.cli import ask

    class Echo:
        name = "echo"

        def can_handle(self, text, session):
            return True

        def handle(self, text, session, trace):
            trace.add("answer", "ok")
            return "ok"

    path = tmp_path / "trace.json"
    assert ask(Agent([Echo()]), "hi", False, str(path)) == "ok"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["reply"] == "ok"
    assert payload["trace"]["handler"] == "echo"
    assert payload["trace"]["steps"][-1] == {"step": "answer", "detail": "ok"}


class FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeTransport:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=FakeCompletions(response))


def completion(content=None, tool_calls=None, reasoning=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [],
                              reasoning_content=reasoning)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="tool_calls")],
                           usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3,
                                                 total_tokens=10))


def tool_call(name, arguments, call_id="call-1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def test_llm_client_logs_payloads_reasoning_and_tool_calls(caplog):
    transport = FakeTransport(completion(
        tool_calls=[tool_call("run_sparql", '{"query": "SELECT * WHERE { ?s ?p ?o }"}')],
        reasoning="I should inspect the graph first.",
    ))
    llm = LLMClient(base_url="http://localhost:8001/v1", model="qa",
                    transport=transport, log_payloads=True)

    with caplog.at_level(logging.INFO, logger="agent.llm.client"):
        response = llm.chat([{"role": "user", "content": "who directed Jaws"}])

    assert response.reasoning == "I should inspect the graph first."
    events = {record.event: to_jsonable(record.fields) for record in caplog.records
              if record.name == "agent.llm.client"}
    assert events["llm.request"]["messages"] == [{"role": "user", "content": "who directed Jaws"}]
    assert events["llm.response"]["reasoning"] == "I should inspect the graph first."
    assert events["llm.response"]["tool_calls"][0]["name"] == "run_sparql"
    assert events["llm.response"]["usage"]["total_tokens"] == 10


def test_payload_switch_hides_prompt_and_response_bodies(caplog):
    transport = FakeTransport(completion(content="answer", reasoning="thought"))
    llm = LLMClient(base_url="http://localhost:8001/v1", model="qa",
                    transport=transport, log_payloads=False)

    with caplog.at_level(logging.INFO, logger="agent.llm.client"):
        llm.chat([{"role": "user", "content": "hi"}])

    events = {record.event: to_jsonable(record.fields) for record in caplog.records
              if record.name == "agent.llm.client"}
    assert events["llm.request"]["message_count"] == 1
    assert "messages" not in events["llm.request"]
    assert events["llm.response"]["content_chars"] == 6
    assert events["llm.response"]["reasoning_chars"] == 7
    assert "content" not in events["llm.response"]
