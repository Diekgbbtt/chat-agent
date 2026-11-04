"""Entity linking: one normalised key, type filtering, ranked candidates, explicit failures."""

from agent.lexicon import Lexicon
from agent.normalize import normalize_label
from agent.tools.resolve import ResolveEntityTool


def test_exact_match_returns_a_full_candidate(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("The Godfather")

    assert observation.error is None
    first = observation.rows[0]
    assert first["qid"] == "Q47703"
    assert first["label"] == "The Godfather"
    assert first["film"] is True
    assert first["human"] is False
    assert first["kind"] == "film"
    assert {"id": "Q11424", "label": "film"} in first["types"]
    assert isinstance(first["degree"], int)


def test_exact_matches_come_before_prefix_and_contains(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    rows = tool.run("godfather").rows

    assert rows[0]["label"] == "The Godfather"


def test_prefix_lookup_finds_a_label(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    labels = [row["label"] for row in tool.run("francis").rows]

    assert "Francis Ford Coppola" in labels


def test_contains_lookup_finds_a_label(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    labels = [row["label"] for row in tool.run("coppola").rows]

    assert "Francis Ford Coppola" in labels
    assert "Sofia Coppola" in labels


def test_lookup_is_case_insensitive(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    qids = [row["qid"] for row in tool.run("THE GODFATHER").rows]

    assert "Q47703" in qids


def test_result_is_capped_at_ten_candidates(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    assert len(tool.run("the").rows) <= 10
    assert len(tool.run("twin").rows) == 10


def test_animated_film_is_movie_like_but_not_a_strict_film(movies_kg):
    lexicon = Lexicon(movies_kg)
    tool = ResolveEntityTool(movies_kg, lexicon)

    row = tool.run("Toy Story").rows[0]

    assert row["qid"] == "Q171048"
    assert row["film"] is False
    assert row["kind"] == "animated film"
    assert lexicon.is_movie("Q171048") is True


def test_ranking_keeps_the_film_inside_the_cap(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    rows = tool.run("twin").rows

    assert rows[0]["qid"] == "Q1900012"
    assert rows[0]["film"] is True


def test_type_filter_accepts_a_label_and_returns_labelled_types(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("The Godfather", type="film")

    assert observation.error is None
    assert [row["qid"] for row in observation.rows] == ["Q47703"]
    assert observation.rows[0]["types"] == [{"id": "Q11424", "label": "film"}]


def test_type_filter_accepts_a_qid(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    rows = tool.run("The Godfather", type="Q7725634").rows

    assert [row["qid"] for row in rows] == ["Q243556"]
    assert rows[0]["kind"] == "literary work"


def test_film_flag_is_strict_instance_of_film(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    series = tool.run("The Godfather", type="film trilogy").rows[0]

    assert series["qid"] == "Q3225260"
    assert series["film"] is False
    assert series["kind"] == "film trilogy"


def test_unknown_type_filter_is_an_actionable_error(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("The Godfather", type="television series")

    assert observation.rows == ()
    assert observation.error and "retry" in observation.error.lower()


def test_type_filter_reports_a_miss_when_the_exact_label_has_no_matching_type(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("Toy Story", type="film")

    assert observation.rows == ()
    assert observation.error and "without the type filter" in observation.error.lower()


def test_curly_apostrophe_matches_the_same_entity(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("The Cat o\u2019 Nine Tails")

    assert observation.error is None
    assert observation.rows[0]["qid"] == "Q706592"


def test_empty_lookup_is_an_actionable_error(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("Godfahter")

    assert observation.rows == ()
    assert observation.error
    assert "shorter label" in observation.error.lower()
    assert "retry" in observation.error.lower()


def test_fuzzy_fallback_is_opt_in(movies_kg):
    strict = ResolveEntityTool(movies_kg, Lexicon(movies_kg))
    fuzzy = ResolveEntityTool(movies_kg, Lexicon(movies_kg), fuzzy=True)

    assert strict.run("Godfahter").rows == ()
    observation = fuzzy.run("Godfahter")

    assert observation.error is None
    assert observation.rows[0]["qid"] == "Q47703"


def test_empty_query_is_an_error(movies_kg):
    tool = ResolveEntityTool(movies_kg, Lexicon(movies_kg))

    observation = tool.run("   ")

    assert observation.rows == ()
    assert observation.error


def test_normalize_label_applies_one_canonical_form():
    assert normalize_label("  SCHINDLER\u2019S\tList  ") == "schindler's list"
    assert normalize_label("Am\u00e9lie") == "am\u00e9lie"
    assert normalize_label("The   Godfather") == "the godfather"


def test_prefix_labels_use_the_same_canonical_form(movies_kg):
    lexicon = Lexicon(movies_kg)

    assert lexicon.prefix_labels("FRANCIS") == ["francis ford coppola"]
