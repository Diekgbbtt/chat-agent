"""Stage 3: the LLM turns the graph's answer into a natural sentence, without changing the facts."""

import logging
import re
from typing import List

log = logging.getLogger("agent.rephrase")

MAX_VALUES = 5  # longer lists keep the template sentence
MAX_EXTRA_CHARS = 60  # a much longer sentence added something
WORD = re.compile(r"[\w'’-]+")
NEGATION = re.compile(r"\b(?:not|never|nobody|none)\b|\b(?:did|does|do|is|was|were|are|has|have|had|could|would|ca|wo)n'?t\b",
                      re.IGNORECASE)
SENTENCE_WORDS = {"the", "a", "an", "it", "its", "this", "that", "yes", "he", "she", "they", "there", "in", "on"}

SYSTEM_PROMPT = """Rewrite the answer to the user's movie question as one short, natural sentence. \
Use exactly the given facts, written exactly as given. Do not add, change or leave out any fact, \
and do not add any other information."""


def rephrase(llm, question: str, values: List[str], template: str) -> str:
    """A natural sentence with every value in it, or the template sentence."""
    if not values or len(values) > MAX_VALUES:
        return template
    try:
        sentence = llm.chat([{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": f"Question: {question}\nFacts: {'; '.join(values)}"}],
                            max_new_tokens=60)
    except Exception:
        log.exception("rephrasing failed")
        return template
    complete = all(value.casefold() in sentence.casefold() for value in values)
    short = len(sentence) <= len(template) + MAX_EXTRA_CHARS
    if sentence and complete and short and _adds_nothing(sentence, question, values):
        return sentence
    log.info("rephrasing rejected: %r", sentence)
    return template


def _words(text: str) -> set:
    return {w.casefold().removesuffix("'s") for w in WORD.findall(text)}


def _adds_nothing(sentence: str, question: str, values: List[str]) -> bool:
    """No negation the question lacks, and no name or number that is not in the question or the facts."""
    if NEGATION.search(sentence) and not NEGATION.search(question) and values != ["No"]:
        return False
    known = _words(question + " " + " ".join(values)) | SENTENCE_WORDS
    return all(w.casefold().removesuffix("'s") in known for w in WORD.findall(sentence)
               if w[0].isupper() or any(c.isdigit() for c in w))
