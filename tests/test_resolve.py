"""Entity linking: exact, prefix, and contains lookup with no fuzzy recall."""

from agent.lexicon import Lexicon
from agent.tools.resolve import ResolveEntityTool


def test_exact_match_returns_a_full_candidate(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    observation = tool.run("The Godfather")

    assert observation.error is None
    first = observation.rows[0]
    assert first["qid"] == "Q47703"
    assert first["label"] == "The Godfather"
    assert first["film"] is True
    assert first["human"] is False
    assert isinstance(first["degree"], int)
    assert "Q11424" in first["types"]


def test_exact_matches_come_before_prefix_and_contains(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    rows = tool.run("godfather", limit=10).rows

    assert rows[0]["label"] == "The Godfather"


def test_prefix_lookup_finds_a_label(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    labels = [row["label"] for row in tool.run("francis", limit=10).rows]

    assert "Francis Ford Coppola" in labels


def test_contains_lookup_finds_a_label(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    labels = [row["label"] for row in tool.run("coppola", limit=10).rows]

    assert "Francis Ford Coppola" in labels


def test_missing_label_returns_no_rows(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    assert tool.run("Zzyzx Qwerty").rows == ()


def test_typo_is_not_fuzzy_matched(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    assert tool.run("Godfathr").rows == ()


def test_limit_is_enforced(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    assert len(tool.run("the", limit=2).rows) <= 2


def test_limit_is_capped(kg):
    tool = ResolveEntityTool(kg, Lexicon(kg))

    assert len(tool.run("the", limit=99).rows) <= 10


def test_lexicon_exposes_a_sorted_prefix_index(kg):
    lexicon = Lexicon(kg)

    assert lexicon.prefix_labels("fran") == ["francis ford coppola"]
