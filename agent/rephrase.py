"""Stage 3: the LLM turns the graph's answer into a natural sentence, without changing the facts."""

import logging
from typing import List

log = logging.getLogger("agent.rephrase")

MAX_VALUES = 5  # longer lists keep the template sentence
MAX_EXTRA_CHARS = 60  # a much longer sentence added something

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
    if sentence and complete and len(sentence) <= len(template) + MAX_EXTRA_CHARS:
        return sentence
    return template
