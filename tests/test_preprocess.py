"""Unit tests for the normalisation layer (agent/preprocess.py)."""

import pytest

from agent import sparql_builder as sb
from agent.lexicon import Lexicon
from agent.parser import Parser
from agent.preprocess import Preprocessor, strip_article


@pytest.fixture(scope="module")
def pre(movies_kg):
    lex = Lexicon(movies_kg)
    return Preprocessor(movies_kg, lex, Parser(movies_kg, lex))


# ------------------------------------------------------------------ quotes

def test_doubled_quotes_collapse(pre):
    plan = pre.analyze("Who directed ''Jaws''?")
    assert "'Jaws'" in plan.text and "''" not in plan.text


@pytest.mark.parametrize("text", [
    "what films did steven spielberg not direct",
    "what films did Steven Spielberg NOT direct",
])
def test_negation_word_does_not_block_a_person_mention(pre, text):
    plan = pre.analyze(text)
    assert plan.negated and not plan.clarify
    assert "'Steven Spielberg'" in plan.text


def test_inner_punctuation_trimmed_outer_question_kept(pre):
    assert pre.analyze("Who directed 'Jaws.'?").text == "Who directed 'Jaws'?"


def test_unclosed_quote_is_closed(pre):
    assert pre.analyze("Who directed 'Jaws?").text == "Who directed 'Jaws'"


def test_inner_whitespace_trimmed(pre):
    assert pre.analyze("Who directed ' Jaws '?").text == "Who directed 'Jaws'?"


def test_curly_quotes_replaced(pre):
    assert "'Jaws'" in pre.analyze("Who directed \u2018Jaws\u2019?").text


def test_interior_apostrophe_title_kept(pre):
    plan = pre.analyze("Who directed 'The Cat o' Nine Tails'?")
    assert plan.text == "Who directed 'The Cat o' Nine Tails'?"


def test_contraction_is_not_an_opening_quote(pre):
    plan = pre.analyze("Who directed Don't Look Her?")
    assert plan.text == "Who directed Don't Look Her?"
    assert plan.clarify is False


# ---------------------------------------------------------- trailing clause

def test_trailing_clause_stripped(pre):
    assert pre.analyze("Who directed 'Jaws', the first film in the trilogy?").text == "Who directed 'Jaws'?"


def test_question_without_clause_unchanged(pre):
    assert pre.analyze("Who directed 'Jaws'?").text == "Who directed 'Jaws'?"


# ------------------------------------------------- mentions and resolution

def test_article_variant_resolves(pre):
    assert "'The Godfather'" in pre.analyze("who directed godfather?").text


def test_partial_title_resolves(pre):
    assert "'The Virgin Suicides'" in pre.analyze("who directed virgin suicides?").text


def test_typo_resolves(pre):
    assert "'Jaws'" in pre.analyze("who directed jawss?").text


def test_long_typo_resolves(pre):
    assert "'The Handmaiden'" in pre.analyze("Who wrote the screenplay for the Handmaidne?").text


def test_sub_run_mention_is_not_rewritten(pre):
    plan = pre.analyze("Who directed Don't Look Her?")
    assert "'Her'" not in plan.text


def test_subvention_clarifies(pre):
    assert pre.analyze("Who directed looking jaws?").clarify is True


def test_quoted_subvention_clarifies(pre):
    assert pre.analyze("Who directed 'The jaws within'?").clarify is True


def test_known_title_does_not_clarify(pre):
    assert pre.analyze("Who directed 'Jaws'?").clarify is False


# ------------------------------------------------------------ two mentions

def test_film_mentions_in_two_sentences_clarify(pre):
    assert pre.analyze("I love Jaws. Who directed Big?").clarify is True


def test_two_titles_in_one_sentence_do_not_clarify(pre):
    plan = pre.analyze("Who directed Her and Interstellar?")
    assert plan.clarify is False
    assert plan.text == "Who directed Her and Interstellar?"


# ---------------------------------------------------------------- negation

def test_not_negation_detected(pre):
    assert pre.analyze("Which movies did Sofia Coppola not direct?").negated is True


def test_never_negation_detected(pre):
    assert pre.analyze("Which movies did Sofia Coppola never direct?").negated is True


def test_not_object_negation_detected(pre):
    assert pre.analyze("Who did not direct 'Alien'?").negated is True


def test_negation_word_inside_quoted_title_is_masked(pre):
    assert pre.analyze("Who directed 'Never Let Me Go'?").negated is False


def test_negation_word_inside_listed_title_is_masked(pre):
    assert pre.analyze("Who directed Never Let Me Go?").negated is False


def test_plain_question_is_not_negated(pre):
    assert pre.analyze("Who directed 'Jaws'?").negated is False


def test_actor_noun_scopes_the_universe(pre):
    plan = pre.analyze("Which actors did not direct 'Alien'?")
    assert plan.negated is True and plan.universe == "actor"
    assert plan.text == "Which did not direct 'Alien'?"


def test_director_noun_scopes_the_universe(pre):
    plan = pre.analyze("Which directors did not direct 'Alien'?")
    assert plan.negated is True and plan.universe == "director"
    assert plan.text == "Which did not direct 'Alien'?"


def test_positive_actor_question_keeps_the_noun(pre):
    plan = pre.analyze("Which actors are in 'Alien'?")
    assert plan.negated is False and plan.universe is None
    assert "actors" in plan.text


def test_single_film_mention_is_collected(pre):
    assert pre.analyze("Who did not direct 'Alien'?").films == ["Q103569"]


def test_multi_film_mentions_are_collected(pre):
    plan = pre.analyze("Which directors did not direct 'Jaws' or 'Alien'?")
    assert len(plan.films) == 2 and len(set(plan.films)) == 2
    assert "Q189505" in plan.films and "Q103569" in plan.films


# ---------------------------------------------------------------- claims

def test_direct_claim_detected(pre):
    plan = pre.analyze("Did Sofia Coppola direct 'Lost in Translation'?")
    assert plan.claim is not None and plan.claim.predicate == sb.DIRECTOR
    assert pre.lex.label(plan.claim.film) == "Lost in Translation"
    assert pre.lex.label(plan.claim.person) == "Sofia Coppola"


def test_inverse_claim_detected(pre):
    plan = pre.analyze("Was 'Alien' directed by Steven Spielberg?")
    assert plan.claim is not None and plan.claim.predicate == sb.DIRECTOR
    assert pre.lex.label(plan.claim.film) == "Alien"
    assert pre.lex.label(plan.claim.person) == "Steven Spielberg"


def test_write_claim_maps_to_screenwriter(pre):
    plan = pre.analyze("Was 'The Godfather' written by Mario Puzo?")
    assert plan.claim is not None and plan.claim.predicate == sb.SCREENWRITER


def test_question_is_not_a_claim(pre):
    assert pre.analyze("Who directed 'Alien'?").claim is None


# ------------------------------------------------------------ paraphrases

@pytest.mark.parametrize("question, verb", [
    ("Who did the directing for 'Jaws'?", "directed"),
    ("Who was at the helm of 'Jaws'?", "directed"),
    ("Who is behind the camera on 'Jaws'?", "directed"),
    ("Who did the writing for 'Jaws'?", "wrote"),
    ("Who did the composing for 'Jaws'?", "composed"),
])
def test_paraphrase_rewritten_to_relation_word(pre, question, verb):
    plan = pre.analyze(question)
    assert verb in plan.text
    assert "the directing" not in plan.text and "at the helm" not in plan.text


def test_unknown_paraphrase_is_left_alone(pre):
    assert pre.analyze("Who approved the casting for 'Jaws'?").text == "Who approved the casting for 'Jaws'?"


# ---------------------------------------------------------------- helpers

def test_strip_article():
    assert strip_article("The Godfather") == "godfather"
    assert strip_article("Matrix") == "matrix"
    assert strip_article("  The  Matrix  ") == "matrix"
