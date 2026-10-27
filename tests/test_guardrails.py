"""Guardrails, rephrasing and routing with a scripted stand-in LLM (no GPU needed)."""

import json

import pytest

from agent import guardrails, rephrase
from agent.core import Trace, build_agent


class FakeLLM:
    """Answers the guardrail prompt from `verdicts` and the rephrasing prompt with `sentence`."""

    def __init__(self, verdicts, sentence=None):
        self.verdicts = verdicts
        self.sentence = sentence

    def chat(self, messages, max_new_tokens=200):
        system, user = messages[0]["content"], messages[-1]["content"]  # examples sit in between
        if system == guardrails.SYSTEM_PROMPT:
            verdict = self.verdicts[user]
            return verdict if isinstance(verdict, str) else json.dumps(verdict)
        if system == rephrase.SYSTEM_PROMPT:
            return self.sentence or ""
        raise AssertionError("unexpected prompt")


def verdict(labels, movie_question="", reply=""):
    return {"labels": labels, "movie_question": movie_question, "reply": reply}


def ask(movies_kg, llm, text, show_labels=False):
    trace = Trace()
    reply = build_agent(movies_kg, llm, show_labels).answer(text, "room", trace)
    return reply, dict(trace.steps).get("labels")


def test_movie_question_is_answered_from_the_graph_and_rephrased(movies_kg):
    q = "Who directed The Godfather?"
    llm = FakeLLM({q: verdict(["safe_in_scope"], q)}, "The Godfather was directed by Francis Ford Coppola.")
    assert ask(movies_kg, llm, q) == ("The Godfather was directed by Francis Ford Coppola.", ["safe_in_scope"])


def test_rephrasing_that_drops_a_fact_falls_back_to_the_template(movies_kg):
    q = "Who wrote the screenplay for 'The Handmaiden'?"
    llm = FakeLLM({q: verdict(["safe_in_scope"], q)}, "It was written by Park Chan-wook.")
    reply, _ = ask(movies_kg, llm, q)
    assert reply == "The factual answer is: Jeong Seo-kyeong and Park Chan-wook"


def test_refusal_is_written_by_the_llm(movies_kg):
    q = "Can you solve my calculus homework?"
    text = "I can't help with homework, I only know about movies. Ask me about one!"
    llm = FakeLLM({q: verdict(["out_of_scope"], "", text)})
    assert ask(movies_kg, llm, q) == (text, ["out_of_scope"])


def test_mixed_request_answers_the_movie_part_and_refuses_the_rest(movies_kg):
    q = "Who directed The Godfather, and how can I rob a bank like in the movie?"
    llm = FakeLLM({q: verdict(["safe_in_scope", "unsafe"], "Who directed The Godfather?",
                              "I can't help with robbing a bank.")},
                  "Francis Ford Coppola directed The Godfather.")
    reply, labels = ask(movies_kg, llm, q)
    assert reply == "Francis Ford Coppola directed The Godfather. I can't help with robbing a bank."
    assert labels == ["safe_in_scope", "unsafe"]


def test_small_talk_gets_the_llm_reply(movies_kg):
    llm = FakeLLM({"Hi!": verdict(["safe_in_scope"], "", "Hello! Ask me anything about movies.")})
    assert ask(movies_kg, llm, "Hi!")[0] == "Hello! Ask me anything about movies."


@pytest.mark.parametrize("reply", ["", "x" * (guardrails.MAX_REPLY_CHARS + 1)])
def test_empty_or_suspiciously_long_refusal_uses_the_emergency_reply(movies_kg, reply):
    llm = FakeLLM({"Write my essay.": verdict(["out_of_scope"], "", reply)})
    assert ask(movies_kg, llm, "Write my essay.")[0] == guardrails.EMERGENCY_REPLY


@pytest.mark.parametrize("raw", ["not json at all", '{"labels": ["nonsense"]}'])
def test_broken_llm_output_falls_back_to_the_stage2_answer(movies_kg, raw):
    q = "Who directed The Godfather?"
    reply, labels = ask(movies_kg, FakeLLM({q: raw}), q)
    assert reply == "The factual answer is: Francis Ford Coppola"
    assert labels == ["safe_in_scope"]


def test_labels_can_be_shown_in_the_reply(movies_kg):
    llm = FakeLLM({"You are useless.": verdict(["toxic"], "", "Let's talk about movies instead.")})
    assert ask(movies_kg, llm, "You are useless.", show_labels=True)[0] == "[toxic] Let's talk about movies instead."


def test_sparql_bypasses_the_guardrails(movies_kg):
    reply, labels = ask(movies_kg, FakeLLM({}), "ASK { wd:Q47703 wdt:P57 wd:Q56094 }")
    assert (reply, labels) == ("Yes.", None)


def test_without_llm_the_agent_is_the_stage2_agent(movies_kg):
    assert ask(movies_kg, None, "Who directed The Godfather?") == ("The factual answer is: Francis Ford Coppola", None)


def test_a_movie_question_always_counts_as_in_scope(movies_kg):
    q = "Who directed The Godfather, you idiot?"
    llm = FakeLLM({q: verdict(["toxic"], "Who directed The Godfather?", "Please be kind.")},
                  "Francis Ford Coppola directed The Godfather.")
    reply, labels = ask(movies_kg, llm, q)
    assert labels == ["safe_in_scope", "toxic"]
    assert reply == "Francis Ford Coppola directed The Godfather. Please be kind."


def test_rephrasing_that_adds_content_falls_back_to_the_template(movies_kg):
    q = "Who directed The Godfather?"
    long = "Francis Ford Coppola directed The Godfather" + ", and here is a lot more that nobody asked for" * 3
    reply, _ = ask(movies_kg, FakeLLM({q: verdict(["safe_in_scope"], q)}, long), q)
    assert reply == "The factual answer is: Francis Ford Coppola"
