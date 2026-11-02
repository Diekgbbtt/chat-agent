"""The guard schema is data, and the loader rejects every incomplete shape."""

import copy
import json

import pytest

from agent.guard.schema import SchemaError, load_schema

PARENTS = ("harmful", "toxic", "prompt_injection")


def shipped():
    return json.loads(open("agent/data/guardrails.json", encoding="utf-8").read())


def write(tmp_path, data):
    path = tmp_path / "guardrails.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_shipped_schema_has_two_scopes_and_three_parent_types():
    schema = load_schema("agent/data/guardrails.json")

    assert schema.scopes == ("in_scope", "out_of_scope")
    assert schema.type_names == PARENTS
    assert set(schema.safety_types) == set(PARENTS)


def test_shipped_schema_has_one_example_for_every_pair():
    schema = load_schema("agent/data/guardrails.json")

    pairs = {(example.scope, example.safety) for example in schema.examples}
    assert len(schema.examples) == 8
    assert pairs == {(scope, safety) for scope in schema.scopes
                     for safety in ("safe", *schema.type_names)}


def test_shipped_schema_carries_limits_and_fallback_text():
    schema = load_schema("agent/data/guardrails.json")

    assert schema.max_verbatims == 8
    assert schema.max_rationale_chars == 240
    assert schema.max_overview_chars == 300
    assert schema.fallback_for("harmful").startswith("I cannot help with harmful")
    assert schema.safety_types["harmful"].description
    assert schema.clarify_text
    assert schema.out_of_scope_text
    assert schema.capability_limit_text
    assert schema.answer_unavailable_text


def test_severity_tone_and_legacy_labels_are_gone():
    schema = load_schema("agent/data/guardrails.json")
    safety = schema.safety_types["harmful"]
    data = shipped()

    assert not hasattr(safety, "severity")
    assert not hasattr(safety, "tone")
    assert not hasattr(safety, "legacy_label")
    assert not hasattr(schema, "severity_order")
    assert all(not {"severity", "tone", "legacy_label"} & set(item)
               for item in data["safety_types"])
    assert "severity_order" not in data


@pytest.mark.parametrize("field_name", ["severity", "tone", "legacy_label"])
def test_legacy_safety_fields_are_rejected(tmp_path, field_name):
    data = shipped()
    data["safety_types"][0][field_name] = "stale"

    with pytest.raises(SchemaError, match=field_name):
        load_schema(write(tmp_path, data))


def test_top_level_severity_order_is_rejected(tmp_path):
    data = shipped()
    data["severity_order"] = ["harmful"]

    with pytest.raises(SchemaError, match="severity_order"):
        load_schema(write(tmp_path, data))


def test_top_level_max_ambiguities_is_rejected(tmp_path):
    data = shipped()
    data["max_ambiguities"] = 6

    with pytest.raises(SchemaError, match="max_ambiguities"):
        load_schema(write(tmp_path, data))


def test_duplicate_scope_is_rejected(tmp_path):
    data = shipped()
    data["scope_values"] = ["in_scope", "in_scope"]

    with pytest.raises(SchemaError, match="scope"):
        load_schema(write(tmp_path, data))


def test_missing_safety_type_is_rejected(tmp_path):
    data = shipped()
    data["safety_types"] = data["safety_types"][:-1]

    with pytest.raises(SchemaError, match="safety"):
        load_schema(write(tmp_path, data))


def test_specific_safety_type_is_rejected(tmp_path):
    data = shipped()
    data["safety_types"][1]["name"] = "violence"

    with pytest.raises(SchemaError, match="safety"):
        load_schema(write(tmp_path, data))


def test_reordered_safety_types_are_rejected(tmp_path):
    data = shipped()
    data["safety_types"] = [data["safety_types"][1], data["safety_types"][0],
                            data["safety_types"][2]]

    with pytest.raises(SchemaError, match="safety"):
        load_schema(write(tmp_path, data))


def test_duplicate_safety_type_is_rejected(tmp_path):
    data = shipped()
    data["safety_types"][1]["name"] = "harmful"

    with pytest.raises(SchemaError, match="safety"):
        load_schema(write(tmp_path, data))


def test_missing_description_is_rejected(tmp_path):
    data = shipped()
    data["safety_types"][0].pop("description")

    with pytest.raises(SchemaError, match="description"):
        load_schema(write(tmp_path, data))


def test_missing_fallback_text_is_rejected(tmp_path):
    data = shipped()
    data["safety_types"][0].pop("fallback_text")

    with pytest.raises(SchemaError, match="fallback"):
        load_schema(write(tmp_path, data))


def test_incomplete_example_set_is_rejected(tmp_path):
    data = shipped()
    data["examples"] = data["examples"][:-1]

    with pytest.raises(SchemaError, match="example"):
        load_schema(write(tmp_path, data))


def test_allow_example_is_rejected(tmp_path):
    data = shipped()
    data["examples"][0]["safety"] = "allow"

    with pytest.raises(SchemaError, match="allow"):
        load_schema(write(tmp_path, data))


def test_a_copy_of_the_shipped_file_is_accepted(tmp_path):
    assert load_schema(write(tmp_path, copy.deepcopy(shipped()))).scopes == ("in_scope", "out_of_scope")
