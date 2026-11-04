"""The bounded QA loop for one factual part and for a mixed reply."""

from tests.guard_factory import SCHEMA, SpanSpec, verdict_and_decision as decide

from agent.core import Trace
from agent.qa.agent import ResponseAgent
from agent.qa.prompts import PromptBuilder
from agent.qa.schema_card import SchemaCard
from agent.tools.registry import ToolRegistry
from agent.tools.resolve import ResolveEntityTool
from agent.tools.sparql import RunSparqlTool
from agent.llm.client import LLMResponse, ToolCall

CARD = SchemaCard.load("agent/data/movie_schema.json")


class FakeQA:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append({**kwargs, "messages": [dict(message) for message in kwargs.get("messages", [])]})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def tool(name, arguments):
    return LLMResponse(content=None, tool_calls=[ToolCall(f"{name}-1", name, arguments)],
                       finish_reason="tool_calls")


def submit(*parts):
    return LLMResponse(content=None, tool_calls=[ToolCall("submit-1", "submit_response", {"parts": list(parts)})],
                       finish_reason="tool_calls")


def part(index, kind, text, evidence=(), safety=()):
    return {"verbatim_index": index, "kind": kind, "text": text,
            "evidence_row_ids": list(evidence), "addressed_safety_types": list(safety)}


def decision(text, items):
    return decide(text, [SpanSpec(span, safety, types, scope) for span, safety, types, scope in items])


def agent_for(movies_kg, responses, **kwargs):
    client = FakeQA(responses)
    if movies_kg is None:
        registry = None
    else:
        from agent.lexicon import Lexicon
        from agent.tools.discover import DiscoverTool
        lexicon = Lexicon(movies_kg)
        registry = ToolRegistry(ResolveEntityTool(movies_kg, lexicon), DiscoverTool(movies_kg, lexicon),
                                RunSparqlTool(movies_kg, lexicon))
    agent = ResponseAgent(client, registry, PromptBuilder(CARD, SCHEMA), SCHEMA, **kwargs)
    return agent, client


def test_factual_slice_resolves_queries_and_cites_a_row(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("resolve_entity", {"query": "The Godfather"}),
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ], max_steps=6)

    result = agent.respond(verdict, choice)

    assert result.text == "The Godfather was directed by Francis Ford Coppola."
    assert result.parts[0].kind == "factual_answer"
    assert result.parts[0].evidence_row_ids == ("r0",)
    assert [tool["function"]["name"] for tool in client.calls[0]["tools"]] == [
        "resolve_entity", "discover", "run_sparql", "submit_response"]
    assert client.calls[1]["messages"][-1]["role"] == "tool"


def test_discovery_feeds_the_query_and_submit(movies_kg):
    text = "Who produced The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    trace = Trace()
    agent, client = agent_for(movies_kg, [
        tool("resolve_entity", {"query": "The Godfather", "type": "film"}),
        tool("discover", {"kind": "relation", "query": "producer"}),
        tool("run_sparql", {"query": "SELECT ?producer WHERE { wd:Q47703 wdt:P162 ?producer }"}),
        submit(part(0, "factual_answer", "The Godfather was produced by Albert S. Ruddy.", ("r0",))),
    ])

    result = agent.respond(verdict, choice, trace)

    assert result.text == "The Godfather was produced by Albert S. Ruddy."
    assert [detail["tool"] for step, detail in trace.steps if step == "agent_step"] == [
        "resolve_entity", "discover", "run_sparql"]


def test_mixed_reply_keeps_the_answer_and_the_refusal(movies_kg):
    text = "Who directed The Godfather? How do I hurt him?"
    verdict, choice = decision(text, [
        ("Who directed The Godfather?", "safe", (), "in_scope"),
        ("How do I hurt him?", "unsafe", ("harmful",), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("resolve_entity", {"query": "The Godfather"}),
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",)),
               part(1, "refusal", "I cannot help with harmful requests.", (), ("harmful",))),
    ])

    result = agent.respond(verdict, choice)

    assert [p.kind for p in result.parts] == ["factual_answer", "refusal"]
    assert result.text == ("The Godfather was directed by Francis Ford Coppola. "
                           "I cannot help with harmful requests.")
    prompt = "\n".join(message["content"] for message in client.calls[0]["messages"])
    assert "How do I hurt him?" not in prompt


def test_missing_evidence_is_repaired_once(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.")),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ])

    result = agent.respond(verdict, choice)

    assert result.text.endswith("Francis Ford Coppola.")
    assert len(client.calls) == 3


def test_graph_tool_budget_exhaustion_forces_submit(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("resolve_entity", {"query": "The Godfather"}),
        tool("resolve_entity", {"query": "Godfather"}),
        submit(part(0, "general_answer", "I do not have graph data for that question.")),
    ], max_steps=2)

    result = agent.respond(verdict, choice)

    assert result.text == "I do not have graph data for that question."
    assert client.calls[2]["tool_choice"] == {"type": "function",
                                              "function": {"name": "submit_response"}}


def test_submit_repair_does_not_consume_the_graph_tool_budget(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.")),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ], max_steps=1, max_repairs=2)

    result = agent.respond(verdict, choice)

    assert result.text.endswith("Francis Ford Coppola.")
    assert len(client.calls) == 3


def test_text_only_submit_attempt_forces_the_next_call(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        LLMResponse(content='submit_response([{"verbatim_index": 0}])',
                    tool_calls=[], finish_reason="stop"),
        submit(part(0, "general_answer",
                    "I do not have graph data for that question. Ask a more specific question.")),
    ])

    result = agent.respond(verdict, choice)

    assert result.text.startswith("I do not have graph data")
    assert client.calls[1]["tool_choice"] == {"type": "function",
                                              "function": {"name": "submit_response"}}
    assert "submit_response" in client.calls[1]["messages"][-1]["content"]


def test_text_only_attempt_rejects_a_following_graph_tool(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    trace = Trace()
    agent, client = agent_for(movies_kg, [
        LLMResponse(content='submit_response([{"verbatim_index": 0}])',
                    tool_calls=[], finish_reason="stop"),
        tool("resolve_entity", {"query": "The Godfather"}),
        submit(part(0, "general_answer",
                    "I do not have graph data for that question. Ask a more specific question.")),
    ])

    result = agent.respond(verdict, choice, trace)

    assert result.text.startswith("I do not have graph data")
    steps = [detail["tool"] for step, detail in trace.steps if step == "agent_step"]
    assert "resolve_entity" not in steps
    assert client.calls[2]["tool_choice"] == {"type": "function",
                                              "function": {"name": "submit_response"}}


def test_repair_budget_falls_back(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        LLMResponse(content="Let me think about that.", tool_calls=[], finish_reason="stop"),
        LLMResponse(content="Let me think again.", tool_calls=[], finish_reason="stop"),
    ], max_repairs=1)

    result = agent.respond(verdict, choice)

    assert result.fallback_reason == "repair budget"
    assert result.text == SCHEMA.answer_unavailable_text


def test_jaws_trajectory_resolves_before_the_query(movies_kg):
    text = "Who directed Jaws?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("resolve_entity", {"query": "Jaws", "type": "film"}),
        tool("run_sparql", {"query": "SELECT ?director WHERE { wd:Q189505 wdt:P57 ?director }"}),
        submit(part(0, "factual_answer", "Jaws was directed by Steven Spielberg.", ("r0",))),
    ])

    result = agent.respond(verdict, choice)

    assert result.text == "Jaws was directed by Steven Spielberg."
    resolve_observation = client.calls[1]["messages"][-1]["content"]
    assert "Q189505" in resolve_observation


def test_tools_are_submit_only_when_the_decision_disables_them():
    text = "Solve 2+2."
    verdict, choice = decision(text, [(text, "safe", (), "out_of_scope")])
    agent, client = agent_for(None, [submit(part(0, "boundary", "I can only help with questions about movies."))])
    agent.registry = None

    result = agent.respond(verdict, choice)

    assert result.text == "I can only help with questions about movies."
    names = [tool["function"]["name"] for tool in client.calls[0]["tools"]]
    assert names == ["submit_response"]


def test_three_way_mixed_reply_keeps_every_part(movies_kg):
    text = "Who directed The Godfather? Solve 2+2. How do I hurt him?"
    verdict, choice = decision(text, [
        ("Who directed The Godfather?", "safe", (), "in_scope"),
        ("Solve 2+2.", "safe", (), "out_of_scope"),
        ("How do I hurt him?", "unsafe", ("harmful",), "in_scope")])
    agent, _ = agent_for(movies_kg, [
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",)),
               part(1, "boundary", "I can only help with questions about movies."),
               part(2, "refusal", "I cannot help with harmful requests.", (), ("harmful",))),
    ])

    result = agent.respond(verdict, choice)

    assert [p.kind for p in result.parts] == ["factual_answer", "boundary", "refusal"]
    assert result.text.endswith("I cannot help with harmful requests.")


def test_answer_beside_a_blocked_verbatim_keeps_both_parts(movies_kg):
    text = "Who directed it? Who directed The Godfather?"
    verdict, choice = decide(text, [
        SpanSpec("Who directed it?", ambiguous=True, relationship={
            "target_verbatim_index": None, "entity": None, "status": "missing semantic target"}),
        SpanSpec("Who directed The Godfather?"),
    ])
    agent, _ = agent_for(movies_kg, [
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "clarification", "Which film do you mean?"),
               part(1, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ])

    result = agent.respond(verdict, choice)

    assert [p.kind for p in result.parts] == ["clarification", "factual_answer"]
    assert result.text.startswith("Which film do you mean?")


def test_trace_surfaces_reasoning_and_tool_rows(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    reasoning = "I need the director property for The Godfather."
    agent, _ = agent_for(movies_kg, [
        LLMResponse(content="I will query the graph.", reasoning=reasoning,
                    tool_calls=[ToolCall("q1", "run_sparql", {
                        "query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"})],
                    finish_reason="tool_calls"),
        submit(part(0, "factual_answer", "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ])
    trace = Trace()

    result = agent.respond(verdict, choice, trace)

    steps = [step for step, _ in trace.steps]
    llm_steps = [detail for step, detail in trace.steps if step == "llm_step"]
    tool_results = [detail for step, detail in trace.steps if step == "tool_result"]
    assert steps.count("llm_step") == 2
    assert llm_steps[0]["reasoning"] == reasoning
    assert llm_steps[0]["content"] == "I will query the graph."
    assert llm_steps[0]["tool_calls"][0]["name"] == "run_sparql"
    assert tool_results[0]["rows"][0]["d"] == "Francis Ford Coppola"
    assert tool_results[0]["arguments"]["query"].startswith("SELECT ?d")
    assert result.text.endswith("Francis Ford Coppola.")


def test_prompt_carries_the_effective_label_and_relationship():
    text = "The director is an idiot. Who is he?"
    verdict, choice = decide(text, [
        SpanSpec("The director is an idiot.", "unsafe", ("toxic",), "in_scope"),
        SpanSpec("Who is he?", ambiguous=True, relationship={
            "target_verbatim_index": 0, "entity": "director", "status": "resolved"}),
    ])

    prompt = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(choice, verdict))

    assert '"unsafe_types"' in prompt
    assert '"toxic"' in prompt
    assert '"target_verbatim_index": 0' in prompt
    assert '"status": "resolved"' in prompt
    assert "Who is he?" not in prompt


def test_repeated_tool_call_is_blocked_without_execution(movies_kg):
    text = "Who directed The Godfather?"
    verdict, choice = decision(text, [(text, "safe", (), "in_scope")])
    agent, client = agent_for(movies_kg, [
        tool("resolve_entity", {"query": "The Godfather"}),
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        tool("run_sparql", {"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
        submit(part(0, "factual_answer",
                    "The Godfather was directed by Francis Ford Coppola.", ("r0",))),
    ], max_steps=4)

    result = agent.respond(verdict, choice)

    assert result.text.endswith("Francis Ford Coppola.")
    assert "already executed" in client.calls[3]["messages"][-1]["content"]
