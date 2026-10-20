"""Entity resolution tests that need the small movies graph."""

from agent.lexicon import Lexicon
from agent.parser import Parser


def test_surname_only_person_resolves_to_the_best_known_human(movies_kg):
    lex = Lexicon(movies_kg)
    parser = Parser(movies_kg, lex)
    question = parser.parse("what films did Spielberg not direct")
    assert question.entity == "Q8877"
    assert question.predicate.endswith("P57")
    assert question.direction == "in"


def test_fuzzy_match_does_not_join_a_question_word_to_a_surname(movies_kg):
    lex = Lexicon(movies_kg)
    parser = Parser(movies_kg, lex)
    _span, candidates = parser._find_entity("what films did Spielberg not direct")
    assert candidates[0] == "Q8877"
