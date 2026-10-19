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


@pytest.mark.parametrize("question, answer", [
    ("Who did the directing for 'Alien'?", "Ridley Scott"),
    ("Who was at the helm of 'Jaws'?", "Steven Spielberg"),
    ("Who is behind the camera on 'Jaws'?", "Steven Spielberg"),
    ("Who did the writing for 'The Godfather'?", "Mario Puzo"),
    ("who directed jawss?", "Steven Spielberg"),
    ("who directed virgin suicides?", "Sofia Coppola"),
    ("Who directed 'Alien', the first film in the trilogy?", "Ridley Scott"),
    ("Did Sofia Coppola direct 'Lost in Translation'?", "Yes"),
    ("Was 'Alien' directed by Steven Spielberg?", "No"),
])
def test_adversarial_forms(factual_agent, question, answer):
    assert factual_agent.answer(question) == f"The factual answer is: {answer}"


def test_negated_question_lists_the_complement(factual_agent):
    reply = factual_agent.answer("Which movies did Sofia Coppola not direct?")
    assert "Jaws" in reply and "Alien" in reply
    assert "Lost in Translation" not in reply and "Marie Antoinette" not in reply


def test_negated_question_with_the_entity_as_object(factual_agent):
    reply = factual_agent.answer("Who did not direct 'Alien'?")
    assert "Sofia Coppola" in reply and "Steven Spielberg" in reply
    assert "Ridley Scott" not in reply


def test_negated_actor_question_uses_the_actor_universe(factual_agent):
    # "actors" names the answer class (cast members, P161); it must not switch the relation to P161
    reply = factual_agent.answer("Which actors did not direct 'Alien'?")
    assert "Sigourney Weaver" in reply and "Meg Ryan" in reply
    assert "Ridley Scott" not in reply


def test_negated_multi_film_question_excludes_every_film(factual_agent):
    reply = factual_agent.answer("Which directors did not direct 'Jaws' or 'Alien'?")
    assert "Sofia Coppola" in reply
    assert "Steven Spielberg" not in reply and "Ridley Scott" not in reply


def test_negated_question_without_facts_lists_the_complement(factual_agent):
    # Meg Ryan has no directing credits: she did not direct any film, not "no information"
    reply = factual_agent.answer("What did Meg Ryan not direct?")
    assert reply.startswith("The factual answer is:") and "Jaws" in reply


def test_negation_word_in_a_title_is_not_a_negation(factual_agent):
    assert factual_agent.answer("Who directed 'Never Let Me Go'?") == "The factual answer is: Mark Romanek"


def test_two_mentions_are_clarified(factual_agent):
    assert factual_agent.answer("I love Jaws. Who directed Big?").startswith("I'm not sure which movie or person")


def test_count_does_not_filter_awards_as_films(factual_agent):
    assert factual_agent.answer("How many awards did the movie 'Alien' receive?") == "The factual answer is: 1"
