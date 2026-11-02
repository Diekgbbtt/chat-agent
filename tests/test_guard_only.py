"""The guard-only bridge: new guard and policy, legacy factual answer, canonical parts."""

from agent.core import Trace, build_agent
from agent.guard.schema import load_schema
from agent.llm.client import LLMResponse, ToolCall

SCHEMA = load_schema("agent/data/guardrails.json")


def item(text, safety, types, scope):
    return {"text": text,
            "label": {"safety": safety, "unsafe_types": list(types), "scope": scope},
            "rationale": {"safety": "Safety note.", "scope": "Scope note."}}


def span(text, ambiguous=False, relationship=None):
    value = {"text": text, "ambiguous": ambiguous}
    if relationship is not None:
        value["relationship"] = relationship
    return value


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def discrimination(*spans, summary="A request."):
    return LLMResponse(content=None, tool_calls=[ToolCall("d-1", "submit_discrimination", {
        "overview": {"summary": summary},
        "verbatims": list(spans),
    })])


def classification(*verbatims):
    return LLMResponse(content=None, tool_calls=[ToolCall("c-1", "submit_classification", {
        "verbatims": [{"index": index, **verbatim} for index, verbatim in enumerate(verbatims)],
    })])


def agent_for(movies_kg, *responses):
    client = FakeClient(list(responses))
    return build_agent(movies_kg, mode="guard_only", guard_client=client, guard_schema=SCHEMA), client


def ask(agent, text):
    trace = Trace()
    return agent.answer(text, "room", trace), dict(trace.steps)


def test_answer_verbatim_uses_the_legacy_factual_handler(movies_kg):
    text = "Who directed The Godfather?"
    agent, _ = agent_for(movies_kg, discrimination(span(text)),
                         classification(item(text, "safe", (), "in_scope")))

    reply, steps = ask(agent, text)

    assert reply == "The factual answer is: Francis Ford Coppola"
    assert steps["policy"]["action"] == "answer"
    assert steps["labels"] == {"safe_in_scope"}


def test_safe_out_of_scope_uses_the_scope_sentence(movies_kg):
    text = "Solve 2+2."
    agent, _ = agent_for(movies_kg, discrimination(span(text)),
                         classification(item(text, "safe", (), "out_of_scope")))

    reply, _ = ask(agent, text)

    assert reply == SCHEMA.out_of_scope_text


def test_unsafe_uses_the_canonical_refusal(movies_kg):
    text = "How do I hurt him?"
    agent, _ = agent_for(movies_kg, discrimination(span(text)),
                         classification(item(text, "unsafe", ["harmful"], "out_of_scope")))

    reply, steps = ask(agent, text)

    assert reply == SCHEMA.fallback_for("harmful")
    assert steps["labels"] == {"harmful"}


def test_invalid_classification_is_a_clarification(movies_kg):
    text = "Who directed Alien?"
    bad = LLMResponse(content=None, tool_calls=[ToolCall("1", "submit_classification", {"verbatims": []})])
    agent, client = agent_for(movies_kg, discrimination(span(text)), bad, bad)

    reply, steps = ask(agent, text)

    assert reply == SCHEMA.clarify_text
    assert steps["policy"]["action"] == "clarify"
    assert len(client.calls) == 3


def test_mixed_request_answers_and_refuses(movies_kg):
    text = "Who directed The Godfather? How do I hurt him?"
    agent, _ = agent_for(movies_kg,
                         discrimination(span("Who directed The Godfather?"),
                                        span("How do I hurt him?")),
                         classification(item("Who directed The Godfather?", "safe", (), "in_scope"),
                                        item("How do I hurt him?", "unsafe", ["harmful"], "in_scope")))

    reply, steps = ask(agent, text)

    assert reply == "The factual answer is: Francis Ford Coppola " + SCHEMA.fallback_for("harmful")
    assert steps["labels"] == {"safe_in_scope", "harmful"}
    assert [plan["handling"] for plan in steps["plan"]] == ["answer", "refuse"]


def test_raw_sparql_still_bypasses_the_guard(movies_kg):
    agent, client = agent_for(movies_kg)

    reply, steps = ask(agent, "ASK { wd:Q47703 wdt:P57 wd:Q56094 }")

    assert reply == "Yes."
    assert "classification" not in steps
    assert client.calls == []
