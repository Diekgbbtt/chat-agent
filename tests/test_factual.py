"""Factual questions against the small tests/fixtures/movies.nt graph."""

import pytest

P = "Please answer this question with a factual approach: "


@pytest.mark.parametrize("question, answer", [
    (P + "Who wrote the screenplay for 'The Handmaiden'?", "Jeong Seo-kyeong and Park Chan-wook"),
    (P + "What are the countries of origin of 'Interstellar'?", "United Kingdom and United States"),
    (P + "Which movie directed by 'Sofia Coppola' has the earliest release date?", "The Virgin Suicides"),
    ("Who directed 'The Cat o' Nine Tails'?", "Dario Argento"),
    # same title for a film, a novel and a trilogy: the film wins
    ("Who directed The Godfather?", "Francis Ford Coppola"),
    ("who wrote the godfather", "Mario Puzo"),
    ("Who wrote the screenplay for the Handmaidne?", "Jeong Seo-kyeong and Park Chan-wook"),  # typo
    # the entity is the object: list its movies
    ("Which movies did Sofia Coppola direct?", "Lost in Translation, Marie Antoinette, and The Virgin Suicides"),
    ("How many movies has Sofia Coppola directed?", "3"),
    ("What is the latest film directed by Sofia Coppola?", "Marie Antoinette"),
    # literals
    ("What is the box office of Interstellar?", "701729200"),
    ("What is the IMDb ID of Interstellar?", "tt0816692"),
    ("When did Interstellar come out?", "2014-10-26"),  # first release date
    ("Who starred in Marie Antoinette?", "Meg Ryan"),  # unlabelled cast member left out
])
def test_answers(factual_agent, question, answer):
    assert factual_agent.answer(question) == f"The factual answer is: {answer}"


def test_unknown_entity(factual_agent):
    assert factual_agent.answer("Who directed 'Zzyzx Qwerty'?").startswith("I'm not sure which movie or person")


def test_known_entity_without_relation(factual_agent):
    assert factual_agent.answer("Is Interstellar any good?").startswith("I found Interstellar, but")


def test_no_facts(factual_agent):
    assert factual_agent.answer("What is the box office of The Handmaiden?") == \
        "Sorry, my knowledge graph has no information about the box office of The Handmaiden."


def test_sparql_still_wins(factual_agent):
    assert factual_agent.answer("ASK { wd:Q47703 wdt:P57 wd:Q56094 }") == "Yes."


@pytest.mark.parametrize("question, answer", [
    ("Who directed Them!?", "Gordon Douglas"),  # the "!" is part of the title
    ("Who directed Who Am I?", "Jackie Chan"),  # so is the "?"
    ("Who directed Being There?", "Hal Ashby"),  # only common words
    ("Who directed The Other?", "Robert Mulligan"),
    ("Who directed Her?", "Spike Jonze"),
    ("Who directed Never Let Me Go?", "Mark Romanek"),
])
def test_unusual_titles(factual_agent, question, answer):
    assert factual_agent.answer(question) == f"The factual answer is: {answer}"


def test_lower_case_one_word_title(factual_agent):
    assert factual_agent.answer("who directed her") == "The factual answer is: Spike Jonze"
    assert factual_agent.answer("who directed them!") == "The factual answer is: Gordon Douglas"


def test_part_of_an_unknown_title_is_not_answered(factual_agent):
    # "Don't Look Up" is not in the graph; answering for "Her" would be wrong
    assert factual_agent.answer("Who directed Don't Look Her?").startswith("I'm not sure which movie or person")
    assert factual_agent.answer("Who directed Her and Interstellar?") == "The factual answer is: Spike Jonze"
