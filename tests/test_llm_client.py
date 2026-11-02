"""The local OpenAI-compatible client and health probe."""

from types import SimpleNamespace

import pytest

from agent.llm import health
from agent.llm.client import LLMClient, LLMError


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeTransport:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))
        self.models = SimpleNamespace(list=lambda: SimpleNamespace(data=[]))

    @property
    def calls(self):
        return self.chat.completions.calls


def completion(content=None, tool_calls=None, finish_reason="stop"):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
                           usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15))


def tool_call(name, arguments, call_id="call-1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def client(responses):
    transport = FakeTransport(responses)
    return LLMClient(base_url="http://localhost:8001/v1", model="guard", api_key="local",
                     transport=transport), transport


def test_content_is_normalised():
    llm, _ = client([completion(content="hello")])

    response = llm.chat([{"role": "user", "content": "hi"}])

    assert response.content == "hello"
    assert response.tool_calls == []
    assert response.usage["total_tokens"] == 15


def test_tool_arguments_are_parsed():
    llm, _ = client([completion(tool_calls=[tool_call("submit_classification", '{"overview": {}}')],
                                finish_reason="tool_calls")])

    response = llm.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}], tool_choice="required")

    assert response.tool_calls[0].name == "submit_classification"
    assert response.tool_calls[0].arguments == {"overview": {}}
    assert response.finish_reason == "tool_calls"


def test_malformed_tool_arguments_raise_a_typed_error():
    llm, _ = client([completion(tool_calls=[tool_call("submit_classification", "not json")])])

    with pytest.raises(LLMError):
        llm.chat([{"role": "user", "content": "hi"}])


def test_one_retry_on_transport_error():
    llm, transport = client([RuntimeError("temporary"), completion(content="ok")])

    response = llm.chat([{"role": "user", "content": "hi"}])

    assert response.content == "ok"
    assert len(transport.calls) == 2


def test_two_transport_errors_raise_a_typed_error():
    llm, transport = client([RuntimeError("one"), RuntimeError("two")])

    with pytest.raises(LLMError):
        llm.chat([{"role": "user", "content": "hi"}])
    assert len(transport.calls) == 2


def test_budget_arguments_are_forwarded():
    llm, transport = client([completion(content="ok")])

    llm.chat([{"role": "user", "content": "hi"}], tools=[], max_tokens=12, temperature=0.0)

    call = transport.calls[0]
    assert call["model"] == "guard"
    assert call["max_tokens"] == 12
    assert call["temperature"] == 0.0
    assert call["parallel_tool_calls"] is False


def test_health_reports_success_and_failure():
    healthy, _ = client([])
    broken, _ = client([])
    broken.transport = None  # not used; the probe takes an explicit callable
    healthy.transport.models.list = lambda: SimpleNamespace(data=[])

    assert health.probe(healthy).ok is True

    def explode():
        raise RuntimeError("down")

    healthy.transport.models.list = explode
    result = health.probe(healthy)
    assert result.ok is False
    assert "down" in result.error
