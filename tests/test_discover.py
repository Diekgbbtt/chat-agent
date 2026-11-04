"""Discovery finds the relation or type the card does not carry."""

from agent.lexicon import Lexicon
from agent.tools.discover import DiscoverTool


def tool_for(movies_kg):
    return DiscoverTool(movies_kg, Lexicon(movies_kg))


def test_relation_search_matches_a_label(movies_kg):
    observation = tool_for(movies_kg).run("relation", "genre")

    assert observation.error is None
    first = observation.rows[0]
    assert first["id"] == "P136"
    assert first["label"] == "genre"
    assert first["usage"] >= 1
    assert first["samples"]
    assert first["direction"] == "out"


def test_relation_search_matches_an_alias(movies_kg):
    observation = tool_for(movies_kg).run("relation", "composed")

    assert "P86" in [row["id"] for row in observation.rows]


def test_relation_search_matches_a_property_id(movies_kg):
    observation = tool_for(movies_kg).run("relation", "p136")

    assert [row["id"] for row in observation.rows] == ["P136"]


def test_relation_search_finds_a_curated_metadata_relation(movies_kg):
    observation = tool_for(movies_kg).run("relation", "description")

    first = observation.rows[0]
    assert first["id"] == "schema:description"
    assert first["label"] == "description"
    assert first["samples"]


def test_relation_search_filters_by_a_subject_type(movies_kg):
    observation = tool_for(movies_kg).run("relation", "director", subject="Q11424")

    first = observation.rows[0]
    assert first["id"] == "P57"
    assert first["direction"] == "out"
    assert first["usage"] >= 10


def test_relation_search_reports_an_incoming_relation_for_a_person(movies_kg):
    observation = tool_for(movies_kg).run("relation", "director", subject="Q56094")

    first = observation.rows[0]
    assert first["id"] == "P57"
    assert first["direction"] == "in"
    assert first["usage"] == 3


def test_relation_search_with_a_subject_returns_a_retry_hint(movies_kg):
    observation = tool_for(movies_kg).run("relation", "genre", subject="Q56094")

    assert observation.rows == ()
    assert observation.error
    assert "without the subject filter" in observation.error.lower()


def test_unknown_subject_qid_is_an_actionable_error(movies_kg):
    observation = tool_for(movies_kg).run("relation", "director", subject="Q999999999")

    assert observation.rows == ()
    assert observation.error
    assert "resolve the entity first" in observation.error.lower()


def test_type_search_matches_a_class_label(movies_kg):
    observation = tool_for(movies_kg).run("type", "film")

    ids = [row["id"] for row in observation.rows]
    assert ids[0] == "Q11424"
    assert {"Q24856", "Q13593818"} <= set(ids)
    assert observation.rows[0]["instances"] >= 10
    assert observation.rows[0]["samples"]


def test_type_search_matches_a_class_qid(movies_kg):
    observation = tool_for(movies_kg).run("type", "Q24856")

    assert [row["id"] for row in observation.rows] == ["Q24856"]
    assert observation.rows[0]["label"] == "film series"


def test_type_search_does_not_substring_match_a_qid(movies_kg):
    observation = tool_for(movies_kg).run("type", "Q114")

    assert observation.rows == ()
    assert observation.error


def test_type_search_finds_the_class_whose_node_is_absent_from_the_graph(movies_kg):
    observation = tool_for(movies_kg).run("type", "human")

    assert observation.rows[0]["id"] == "Q5"
    assert observation.rows[0]["label"] == "human"
    assert observation.rows[0]["instances"] >= 10


def test_unknown_kind_is_an_actionable_error(movies_kg):
    observation = tool_for(movies_kg).run("colour", "genre")

    assert observation.rows == ()
    assert observation.error and "relation" in observation.error.lower()
    assert "type" in observation.error.lower()


def test_blank_query_is_an_actionable_error(movies_kg):
    observation = tool_for(movies_kg).run("relation", "   ")

    assert observation.rows == ()
    assert observation.error and "retry" in observation.error.lower()


def test_missing_relation_is_an_actionable_error(movies_kg):
    observation = tool_for(movies_kg).run("relation", "flibbertigibbet")

    assert observation.rows == ()
    assert observation.error and "retry" in observation.error.lower()
