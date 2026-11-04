"""The guard classifier labels a fixed decomposition."""

from tests.guard_factory import SpanSpec, discrimination

from agent.guard.classifier import GuardClassifier
from agent.guard.schema import load_schema
from agent.llm.client import LLMError, LLMResponse, ToolCall

SCHEMA = load_schema("agent/data/guardrails.json")
TEXT = "Who directed Alien?"
SPANS = discrimination(TEXT, [SpanSpec(TEXT)])


def response(arguments, name="submit_classification"):
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


def labels(index=0, safety="safe", types=(), scope="in_scope"):
    return {"verbatims": [{"index": index,
                           "label": {"safety": safety, "unsafe_types": list(types), "scope": scope},
                           "rationale": {"safety": "Benign.", "scope": "Film credit."}}]}


def test_classifier_returns_the_raw_labels():
    raw = labels()
    client = FakeClient(response(raw))

    result = GuardClassifier(client, SCHEMA).classify(TEXT, SPANS)

    assert result.verbatims == raw["verbatims"]


def test_classifier_forces_one_tool_and_caps_output():
    client = FakeClient(response(labels()))
    classifier = GuardClassifier(client, SCHEMA)

    classifier.classify(TEXT, SPANS)

    call = client.calls[0]
    assert call["tool_choice"]["function"]["name"] == "submit_classification"
    assert call["max_tokens"] == 1600
    assert call["parallel_tool_calls"] is False


def test_prompt_defines_the_classification_boundary_and_relationships():
    client = FakeClient(response(labels()))
    classifier = GuardClassifier(client, SCHEMA)

    prompt = "\n".join(message["content"] for message in classifier.messages(TEXT, SPANS))

    assert "fixed decomposition" in prompt
    assert "Do not merge, split, reorder, or rename the decomposition." in prompt
    assert "prompt_injection verbatim is always out_of_scope" in prompt
    assert "Every span gets exactly one label, including an ambiguous span." in prompt
    assert "Do not skip an ambiguous span" in prompt
    assert "The policy applies relationships after you return every own label." in prompt
    assert "The labels array length must equal the number of input spans." in prompt
    assert "The rationale must justify the label you returned." in prompt


def test_prompt_separates_movie_capabilities_from_general_capabilities():
    client = FakeClient(response(labels()))
    classifier = GuardClassifier(client, SCHEMA)

    prompt = "\n".join(message["content"] for message in classifier.messages(TEXT, SPANS))

    assert "a capability request that names the movie domain" in prompt
    assert "general capability questions" in prompt


def test_prompt_contains_every_example():
    client = FakeClient(response(labels()))
    classifier = GuardClassifier(client, SCHEMA)

    prompt = "\n".join(message["content"] for message in classifier.messages(TEXT, SPANS))

    assert all(example.message in prompt for example in SCHEMA.examples)


def test_prompt_examples_use_the_tool_label_vocabulary():
    client = FakeClient(response(labels()))
    classifier = GuardClassifier(client, SCHEMA)

    prompt = "\n".join(message["content"] for message in classifier.messages(TEXT, SPANS))

    assert "safety=harmful" not in prompt
    assert "safety=unsafe, unsafe_types=[harmful]" in prompt
    assert "safety=safe" in prompt


def test_user_prompt_carries_the_decomposition():
    text = "The director is an idiot. Who is he?"
    spans = discrimination(text, [
        SpanSpec("The director is an idiot.", "unsafe", ("toxic",), "in_scope"),
        SpanSpec("Who is he?", ambiguous=True, relationship={
            "target_verbatim_index": 0, "entity": "director", "status": "resolved"}),
    ])
    client = FakeClient(response({"verbatims": []}))

    messages = GuardClassifier(client, SCHEMA).messages(text, spans)
    user = messages[-1]["content"]

    assert "The director is an idiot." in user
    assert '"span_count": 2' in user
    assert '"required_label_count": 2' in user
    assert '"ambiguous": true' in user
    assert '"target_verbatim_index": 0' in user
    assert '"status": "resolved"' in user


def test_a_missing_tool_call_is_a_typed_error():
    client = FakeClient(LLMResponse(content="not a tool call", tool_calls=[]))

    try:
        GuardClassifier(client, SCHEMA).classify(TEXT, SPANS)
    except LLMError as exc:
        assert "submit_classification" in str(exc)
    else:
        raise AssertionError("expected LLMError")


def test_two_tool_calls_are_rejected():
    client = FakeClient(LLMResponse(content=None, tool_calls=[
        ToolCall("1", "submit_classification", labels()),
        ToolCall("2", "submit_classification", labels()),
    ]))

    try:
        GuardClassifier(client, SCHEMA).classify(TEXT, SPANS)
    except LLMError:
        pass
    else:
        raise AssertionError("expected LLMError")


def test_correction_names_every_required_index():
    text = "The director is an idiot. Who is he?"
    spans = discrimination(text, [
        SpanSpec("The director is an idiot.", "unsafe", ("toxic",), "in_scope"),
        SpanSpec("Who is he?", ambiguous=True, relationship={
            "target_verbatim_index": 0, "entity": "director", "status": "resolved"}),
    ])
    client = FakeClient(response({"verbatims": []}))
    classifier = GuardClassifier(client, SCHEMA)

    messages = classifier.messages(text, spans, correction="expected 2 labels, got 1")
    user = messages[-1]["content"]

    assert "Return exactly 2 labels" in user
    assert "index: 0, 1" in user
    assert "Do not skip an ambiguous span." in user


def test_prompt_and_tool_schema_carry_the_rationale_limit():
    client = FakeClient(response(labels()))
    classifier = GuardClassifier(client, SCHEMA)

    prompt = "\n".join(message["content"] for message in classifier.messages(TEXT, SPANS))
    classifier.classify(TEXT, SPANS)
    rationale = (client.calls[0]["tools"][0]["function"]["parameters"]["properties"]
                 ["verbatims"]["items"]["properties"]["rationale"])

    assert "240" in prompt
    assert rationale["properties"]["safety"]["maxLength"] == 240
    assert rationale["properties"]["scope"]["maxLength"] == 240


def test_tool_schema_enforces_the_exact_label_count():
    text = "The director is an idiot. Who is he?"
    spans = discrimination(text, [
        SpanSpec("The director is an idiot.", "unsafe", ("toxic",), "in_scope"),
        SpanSpec("Who is he?", ambiguous=True, relationship={
            "target_verbatim_index": 0, "entity": "director", "status": "resolved"}),
    ])
    client = FakeClient(response(labels()))
    GuardClassifier(client, SCHEMA).classify(text, spans)

    array = client.calls[0]["tools"][0]["function"]["parameters"]["properties"]["verbatims"]

    assert array["minItems"] == 2
    assert array["maxItems"] == 2
    assert client.calls[0]["messages"][-1]["content"].count('"required_label_count": 2') == 1
