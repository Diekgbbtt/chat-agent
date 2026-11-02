"""One normalised message string for the guard and the QA prompt."""

import re

MAX_INPUT_CHARS = 5_000
CURLY = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
APPROACH_PREFIX = re.compile(r"^please answer this question[^:]*:\s*", re.IGNORECASE)


def normalise(text) -> str:
    value = "" if text is None else str(text)
    value = "".join(CURLY.get(char, char) for char in value)
    value = APPROACH_PREFIX.sub("", value.strip())
    return value.strip()[:MAX_INPUT_CHARS]
