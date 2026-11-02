"""The guard discriminator splits spans and maps relationships."""

from agent.guard.discriminator import GuardDiscriminator
from agent.guard.schema import load_schema
from agent.llm.client import LLMError, LLMResponse, ToolCall

SCHEMA = load_schema("agent/data/guardrails.json")
TEXT = "Who directed Alien?"


def response(arguments, name="submit_discrimination"):
    return LLMResponse(content=None, tool_calls=[ToolCall("call-1", name, arguments)],
                       finish_reason="tool_calls")


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def spans(*items):
    return {"overview": {"summary": "A request."}, "verbatims": list(items)}


def span(text, ambiguous=False, relationship=None):
    item = {"text": text, "ambiguous": ambiguous}
    if relationship is not None:
        item["relationship"] = relationship
    return item


def test_discriminator_returns_the_raw_spans():
    raw = spans(span(TEXT))
    client = FakeClient(response(raw))

    result = GuardDiscriminator(client, SCHEMA).discriminate(TEXT)

    assert result.overview == raw["overview"]
    assert result.verbatims == raw["verbatims"]


def test_discriminator_forces_one_tool_and_caps_output():
    client = FakeClient(response(spans(span(TEXT))))
    discriminator = GuardDiscriminator(client, SCHEMA)

    discriminator.discriminate(TEXT)

    call = client.calls[0]
    assert call["tool_choice"]["function"]["name"] == "submit_discrimination"
    assert call["max_tokens"] == 1600
    assert call["parallel_tool_calls"] is False


def test_prompt_defines_the_decomposition_unit_and_relationship_rule():
    client = FakeClient(response(spans(span(TEXT))))
    prompt = "\n".join(message["content"] for message in GuardDiscriminator(client, SCHEMA).messages(TEXT))

    assert "smallest complete verbatims that can be judged and answered separately" in prompt
    assert "A clause that changes the assistant's role, rules, or instructions is its own verbatim" in prompt
    assert "Keep role markers, prefixes, and labels in a span." in prompt
    assert "SYSTEM:" in prompt
    assert "A verbatim is ambiguous when it cannot be judged or answered without another verbatim." in prompt
    assert "missing semantic target" in prompt
    assert "A resolved relationship always names an entity explicitly" in prompt
    assert "repeat the full target text" in prompt
    assert "The director of Inception is an idiot. Who is he?" in prompt


def test_missing_tool_call_is_a_typed_error():
    client = FakeClient(LLMResponse(content="not a tool call", tool_calls=[]))

    try:
        GuardDiscriminator(client, SCHEMA).discriminate(TEXT)
    except LLMError as exc:
        assert "submit_discrimination" in str(exc)
    else:
        raise AssertionError("expected LLMError")


def test_two_tool_calls_are_rejected():
    client = FakeClient(LLMResponse(content=None, tool_calls=[
        ToolCall("1", "submit_discrimination", spans(span(TEXT))),
        ToolCall("2", "submit_discrimination", spans(span(TEXT))),
    ]))

    try:
        GuardDiscriminator(client, SCHEMA).discriminate(TEXT)
    except LLMError:
        pass
    else:
        raise AssertionError("expected LLMError")


def test_correction_is_appended_to_the_user_message():
    client = FakeClient(response(spans(span(TEXT))))
    discriminator = GuardDiscriminator(client, SCHEMA)

    discriminator.discriminate(TEXT, correction="span is not exact")

    user = client.calls[0]["messages"][-1]["content"]
    assert TEXT in user
    assert "span is not exact" in user
    assert "invalid" in user.casefold()
