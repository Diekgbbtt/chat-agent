"""AGENT_MODE selects one runtime, and the session seam stores only safe in-scope text."""

from agent.core import Trace, build_agent
from agent.guard.schema import load_schema
from agent.llm.client import LLMResponse, ToolCall

SCHEMA = load_schema("agent/data/guardrails.json")


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append({**kwargs, "messages": [dict(m) for m in kwargs.get("messages", [])]})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def item(text, safety, types, scope):
    return {"text": text,
            "label": {"safety": safety, "unsafe_types": list(types), "scope": scope},
            "rationale": {"safety": "Safety note.", "scope": "Scope note."}}


def span(text, ambiguous=False, relationship=None):
    value = {"text": text, "ambiguous": ambiguous}
    if relationship is not None:
        value["relationship"] = relationship
    return value


def discrimination(*spans, summary="A request."):
    return LLMResponse(content=None, tool_calls=[ToolCall("d1", "submit_discrimination", {
        "overview": {"summary": summary}, "verbatims": list(spans)})])


def classification(*items):
    return LLMResponse(content=None, tool_calls=[ToolCall("c1", "submit_classification", {
        "verbatims": [{"index": index, **item} for index, item in enumerate(items)]})])


def tool(name, args):
    return LLMResponse(content=None, tool_calls=[ToolCall(f"{name}-1", name, args)])


def submit(*parts):
    return LLMResponse(content=None, tool_calls=[ToolCall("s1", "submit_response", {"parts": list(parts)})])


def part(index, kind, text, evidence=(), safety=()):
    return {"verbatim_index": index, "kind": kind, "text": text,
            "evidence_row_ids": list(evidence), "addressed_safety_types": list(safety)}


def test_legacy_is_the_default(movies_kg):
    agent = build_agent(movies_kg)

    assert [handler.name for handler in agent.handlers] == ["sparql", "factual"]


def test_unknown_mode_fails_at_build_time(movies_kg):
    try:
        build_agent(movies_kg, mode="nope")
    except ValueError as exc:
        assert "AGENT_MODE" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_llm_mode_runs_the_full_path(movies_kg):
    text = "Who directed The Godfather?"
    guard = FakeClient([discrimination(span(text)), classification(item(text, "safe", (), "in_scope"))])
    qa = FakeClient([
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ])
    agent = build_agent(movies_kg, mode="llm", guard_client=guard, qa_client=qa, guard_schema=SCHEMA)
    trace = Trace()

    reply = agent.answer(text, "room", trace)

    assert reply == "The Godfather was directed by Francis Ford Coppola."
    steps = dict(trace.steps)
    assert steps["mode"] == "llm"
    assert steps["policy"]["action"] == "answer"
    assert steps["evidence"] == ["r0"]


def test_session_stores_only_safe_in_scope_text(movies_kg):
    text = "Who directed The Godfather? Solve 2+2."
    guard = FakeClient([discrimination(
        span("Who directed The Godfather?"), span("Solve 2+2.")), classification(
        item("Who directed The Godfather?", "safe", (), "in_scope"),
        item("Solve 2+2.", "safe", (), "out_of_scope"))])
    qa = FakeClient([
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",)),
               part(1, "boundary", "I can only help with questions about movies.")),
    ])
    agent = build_agent(movies_kg, mode="llm", guard_client=guard, qa_client=qa, guard_schema=SCHEMA)

    agent.answer(text, "room")

    turns = agent.session("room").turns
    assert turns[0]["user"] == "Who directed The Godfather?"
    assert "Solve 2+2." not in turns[0]["user"]
    assert "How do I" not in str(turns)


def test_session_stores_no_unsafe_text(movies_kg):
    text = "Who directed The Godfather? How do I hurt him?"
    guard = FakeClient([discrimination(
        span("Who directed The Godfather?"), span("How do I hurt him?")), classification(
        item("Who directed The Godfather?", "safe", (), "in_scope"),
        item("How do I hurt him?", "unsafe", ("harmful",), "in_scope"))])
    qa = FakeClient([
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",)),
               part(1, "refusal", "I cannot help with harmful requests.", (), ("harmful",))),
    ])
    agent = build_agent(movies_kg, mode="llm", guard_client=guard, qa_client=qa, guard_schema=SCHEMA)

    agent.answer(text, "room")

    turn = agent.session("room").turns[0]
    assert "How do I hurt him?" not in str(turn)
    assert "harmful" in turn["reply"]


def test_session_redacts_an_inherited_unsafe_child(movies_kg):
    text = "The director is an idiot. Who is he?"
    guard = FakeClient([
        discrimination(span("The director is an idiot."),
                       span("Who is he?", ambiguous=True, relationship={
                           "target_verbatim_index": 0, "entity": "director", "status": "resolved"})),
        classification(item("The director is an idiot.", "unsafe", ("toxic",), "in_scope"),
                       item("Who is he?", "safe", (), "in_scope")),
    ])
    qa = FakeClient([
        submit(part(0, "refusal", "I cannot help with toxic requests.", (), ("toxic",)),
               part(1, "refusal", "I cannot help with toxic requests.", (), ("toxic",))),
    ])
    agent = build_agent(movies_kg, mode="llm", guard_client=guard, qa_client=qa, guard_schema=SCHEMA)

    agent.answer(text, "room")

    turn = agent.session("room").turns[0]
    assert turn["user"] == ""
    assert "Who is he?" not in str(turn)
    assert "idiot" not in str(turn)


def test_session_is_bounded(movies_kg):
    text = "Who directed The Godfather?"
    agent = build_agent(movies_kg, mode="llm", guard_client=FakeClient([]), guard_schema=SCHEMA)

    for index in range(30):
        agent.session("room").turns.append({"user": f"u{index}", "reply": "r"})
    from agent.core import append_turn
    append_turn(agent.session("room"), "u", "r")

    assert len(agent.session("room").turns) <= 20


def test_llm_mode_keeps_raw_sparql_symbolic(movies_kg):
    guard = FakeClient([])
    qa = FakeClient([])
    agent = build_agent(movies_kg, mode="llm", guard_client=guard, qa_client=qa, guard_schema=SCHEMA)
    trace = Trace()

    reply = agent.answer("ASK { wd:Q47703 wdt:P57 wd:Q56094 }", "room", trace)

    assert reply == "Yes."
    assert guard.calls == []
    assert qa.calls == []
    steps = dict(trace.steps)
    assert "sparql" in steps
    assert "policy" not in steps
