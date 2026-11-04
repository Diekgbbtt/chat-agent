"""One normalised message string for the guard and one canonical label key for lookup."""

import re
import unicodedata

MAX_INPUT_CHARS = 5_000
CURLY = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
APOSTROPHES = {"\u2018": "'", "\u2019": "'", "\u02bc": "'", "\u00b4": "'", "\u0060": "'"}
APPROACH_PREFIX = re.compile(r"^please answer this question[^:]*:\s*", re.IGNORECASE)
SPACES = re.compile(r"\s+")


def normalise(text) -> str:
    value = "" if text is None else str(text)
    value = "".join(CURLY.get(char, char) for char in value)
    value = APPROACH_PREFIX.sub("", value.strip())
    return value.strip()[:MAX_INPUT_CHARS]


def normalize_label(text) -> str:
    """One key for index and lookup: NFKC, folded case, plain apostrophes, single spaces."""
    value = unicodedata.normalize("NFKC", "" if text is None else str(text))
    value = "".join(APOSTROPHES.get(char, char) for char in value)
    return SPACES.sub(" ", value).strip().casefold()
