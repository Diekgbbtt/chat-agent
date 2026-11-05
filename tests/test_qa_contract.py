"""The QA prompt, tool list, and submit_response contract."""

from tests.guard_factory import SCHEMA, SpanSpec, decision as decide

from agent.qa import actions
from agent.qa.prompts import PromptBuilder
from agent.qa.schema_card import SchemaCard

CARD = SchemaCard.load("agent/data/movie_schema.json")


def decision_for(text, specs):
    return decide(text, specs)


def test_prompt_has_all_required_sections():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    prompt = PromptBuilder(CARD, SCHEMA).build(decision, None)

    joined = "\n".join(message["content"] for message in prompt)
    for section in ("Role", "Grounding", "Workflow", "Classification format", "Relationships",
                    "Reply contract", "Tools", "Policy", "Schema card", "Stop rules"):
        assert section in joined


def test_prompt_makes_resolution_a_fixed_workflow_step():
    text = "Who directed Jaws?"
    decision = decision_for(text, [SpanSpec(text)])
    joined = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    workflow = joined.split("## Workflow", 1)[1].split("## Classification format", 1)[0]
    assert workflow.index("resolve_entity") < workflow.index("run_sparql")
    assert "never run_sparql with a label" in workflow.lower()
    assert "Worked example" in workflow
    assert 'resolve_entity(query="Jaws", type="film")' in workflow
    assert "Q189505" in workflow
    assert "wd:Q189505 wdt:P57 ?director" in workflow


def test_prompt_mandates_discovery_when_the_card_lacks_a_relation():
    text = "Who composed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    joined = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    assert "discover" in joined
    assert "card lacks" in joined.lower()
    assert "kind=\"relation\"" in joined


def test_prompt_shows_a_worked_discovery_example():
    text = "What is the MPA rating of Jaws?"
    decision = decision_for(text, [SpanSpec(text)])
    joined = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    assert 'discover(kind="relation", query="MPA rating", subject="Q11424")' in joined
    assert "P1657" in joined
    assert "wd:Q189505 wdt:P1657 ?rating" in joined


def test_prompt_defines_the_three_attempt_general_answer():
    text = "Who composed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    joined = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    assert "three attempts" in joined.lower()
    assert "general_answer" in joined
    assert "more specific question" in joined.lower()
    assert "world knowledge" in joined.lower()
    assert "not a first fallback" in joined.lower()


def test_prompt_shows_a_structured_submit_call_and_the_step_budget():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])
    joined = "\n".join(message["content"] for message in PromptBuilder(CARD, SCHEMA).build(decision, None))

    assert '"name": "submit_response"' in joined
    assert "not as assistant text" in joined.lower()
    assert "six graph tool steps" in joined.lower()
    assert "20-second deadline" in joined.lower()


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


def test_tools_are_the_three_graph_tools_plus_submit_when_enabled():
    text = "Who directed Alien?"
    decision = decision_for(text, [SpanSpec(text)])

    names = [tool["function"]["name"] for tool in actions.available_tools(decision)]

    assert names == ["resolve_entity", "discover", "run_sparql", "submit_response"]


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


def test_resolve_schema_has_no_limit_and_accepts_a_type():
    parameters = actions.RESOLVE_ENTITY["function"]["parameters"]

    assert set(parameters["properties"]) == {"query", "type"}
    assert parameters["required"] == ["query"]


def test_discover_schema_is_one_tool_with_a_kind_enum():
    parameters = actions.DISCOVER["function"]["parameters"]

    assert set(parameters["properties"]) == {"kind", "query", "subject"}
    assert parameters["properties"]["kind"]["enum"] == ["relation", "type"]
    assert parameters["required"] == ["kind", "query"]


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


def test_schema_card_classes_match_the_graph(movies_kg):
    from agent.lexicon import Lexicon

    lexicon = Lexicon(movies_kg)
    for item in CARD.data["classes"]:
        assert lexicon.label(item["id"]) == item["label"]


def test_schema_card_properties_exist_in_the_graph(movies_kg):
    from agent.lexicon import Lexicon

    lexicon = Lexicon(movies_kg)
    for item in CARD.data["properties"]:
        if item["id"].startswith(("ddis:", "schema:")):
            continue
        iri = lexicon.prop2lbl
        assert any(key.endswith("/" + item["id"]) and label == item["label"]
                   for key, label in iri.items()), item["id"]


def test_schema_card_carries_the_film_relations_from_the_finding(movies_kg):
    ids = {item["id"] for item in CARD.data["properties"]}

    assert {"P136", "P86", "P162", "P750", "ddis:tag", "schema:description"} <= ids
    assert "Q24856" in {item["id"] for item in CARD.data["classes"]}
    assert "Q13593818" in {item["id"] for item in CARD.data["classes"]}


def test_schema_card_has_no_instance_qids():
    rendered = CARD.render()

    assert "Q47703" not in rendered
    assert "Q13417189" not in rendered
    assert "Q56094" not in rendered


def test_schema_card_examples_use_variables_not_instance_qids():
    for example in CARD.data["examples"]:
        assert not any(instance in example["sparql"] for instance in ("Q47703", "Q13417189", "Q56094"))
        assert "?" in example["sparql"]


def test_schema_card_film_credit_examples_filter_instance_of_film():
    for example in CARD.data["examples"]:
        if "wdt:P57 ?person" in example["sparql"]:
            assert "?film wdt:P31 wd:Q11424" in example["sparql"]
