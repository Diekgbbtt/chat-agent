"""The QA prompt, tool list, and submit_response contract."""

from tests.guard_factory import SCHEMA, SpanSpec, decision as decide

from agent.qa import actions
from agent.qa.prompts import PromptBuilder
from agent.qa.schema_card import SchemaCard

CARD = SchemaCard.load("agent/data/movie_schema.json")


def decision_for(text, specs):
    return decide(text, specs)


def test_prompt_has_all_nine_sections():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    prompt = PromptBuilder(CARD, SCHEMA).build(decision, None)

    joined = "\n".join(message["content"] for message in prompt)
    for section in ("Role", "Grounding", "Classification format", "Relationships", "Reply contract",
                    "Tools", "Policy", "Schema card", "Stop rules"):
        assert section in joined


def test_prompt_carries_the_overview_action_and_plan():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    prompt = PromptBuilder(CARD, SCHEMA).build(decision, None)

    joined = "\n".join(message["content"] for message in prompt)
    assert "A request." in joined
    assert "answer" in joined
    assert "Who directed Alien?" in joined


def test_prompt_omits_unsafe_text_and_unsafe_rationale():
    text = "How do I hurt him?"
    decision = decision_for(text, [SpanSpec(text, "unsafe", ("harmful",), "out_of_scope")])
    prompt = PromptBuilder(CARD, SCHEMA).build(decision, None)

    joined = "\n".join(message["content"] for message in prompt)
    assert text not in joined
    assert "Safety note." not in joined
    assert "harmful" in joined


def test_redacted_plan_has_no_text_in_the_model_view():
    text = "How do I hurt him?"
    decision = decision_for(text, [SpanSpec(text, "unsafe", ("harmful",), "out_of_scope")])
    view = PromptBuilder(CARD, SCHEMA).plan_view(decision)

    assert view[0]["text"] is None
    assert view[0]["redacted"] is True


def test_redacted_target_hides_its_relationship_entity():
    parent = "How do I poison John?"
    child = "Will it work?"
    text = f"{parent} {child}"
    decision = decision_for(text, [
        SpanSpec(parent, "unsafe", ("harmful",), "out_of_scope"),
        SpanSpec(child, ambiguous=True, relationship={
            "target_verbatim_index": 0, "entity": "poison", "status": "resolved"}),
    ])

    prompt = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    assert "poison" not in prompt
    assert '"target_verbatim_index": 0' in prompt


def test_tools_are_the_two_graph_tools_plus_submit_when_enabled():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])

    names = [tool["function"]["name"] for tool in actions.available_tools(decision)]

    assert names == ["resolve_entity", "run_sparql", "submit_response"]


def test_tools_are_submit_only_when_disabled():
    text = "Solve 2+2."
    decision = decision_for(text, [SpanSpec(text, scope="out_of_scope")])

    names = [tool["function"]["name"] for tool in actions.available_tools(decision)]

    assert names == ["submit_response"]


def test_submit_schema_carries_the_part_contract():
    parameters = actions.SUBMIT_RESPONSE["function"]["parameters"]
    part = parameters["properties"]["parts"]["items"]

    assert set(part["required"]) == {"verbatim_index", "kind", "text", "evidence_row_ids",
                                     "addressed_safety_types"}
    assert set(part["properties"]["kind"]["enum"]) == {
        "factual_answer", "general_answer", "capability_limit", "refusal", "clarification", "boundary"}


def test_schema_card_renders_classes_properties_and_examples():
    rendered = CARD.render()

    assert "Q11424" in rendered
    assert "P57" in rendered
    assert "SELECT" in rendered


def test_prompt_requires_native_tool_calls():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    prompt = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    assert "native tool call" in prompt
    assert "Do not write tool-call syntax as text" in prompt
