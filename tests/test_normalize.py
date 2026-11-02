"""One normalised message string for the guard and the QA prompt."""

from agent.normalize import MAX_INPUT_CHARS, normalise


def test_trims_and_keeps_internal_text():
    assert normalise("  Who directed Inception?  ") == "Who directed Inception?"


def test_repairs_curly_quotes():
    assert normalise("Who directed \u201cInception\u201d?") == 'Who directed "Inception"?'


def test_strips_the_course_prefix():
    assert normalise("Please answer this question with a factual approach: Who directed Inception?") == \
        "Who directed Inception?"
    assert normalise("PLEASE ANSWER THIS QUESTION WITH A FACTUAL APPROACH: Who directed Inception?") == \
        "Who directed Inception?"


def test_caps_the_input():
    assert normalise("x" * (MAX_INPUT_CHARS * 2)) == "x" * MAX_INPUT_CHARS


def test_is_idempotent():
    once = normalise("  Please answer this question in a factual way:  Who directed \u201cInception\u201d? ")
    assert normalise(once) == once


def test_empty_input_stays_empty():
    assert normalise("   ") == ""
    assert normalise(None) == ""
