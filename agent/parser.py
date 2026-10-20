"""
Turns a question into a Question: which entity, which predicate, which direction, which kind.

1. Entity: a quoted title, else the longest run of words that is a graph label,
   else the closest label (fuzzy, for typos).
2. Predicate: the graph's property labels plus the synonyms in data/relations.json.
3. Among same-named entities and matching predicates, the first combination
   that has facts in the graph wins (films first, then the best-known entity).
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from rapidfuzz import process
from rapidfuzz.distance import OSA

from agent import sparql_builder as sb
from agent.kg import KnowledgeGraph, PREFIXES
from agent.lexicon import Lexicon

STOPWORDS = set("""a an the of in on at by for to from with and or is are was were be been did does do has have had
who whom what which when where how many much this that it its me my please tell movie movies film films""".split())
# Question words and negation words make a fuzzy window straddle a relation phrase.
# Articles and prepositions can legally start or end a title, so they stay in fuzzy windows.
FUZZY_EDGE_NOISE = (STOPWORDS - {"a", "an", "the", "of", "in", "on", "at", "by", "for", "to",
                                  "from", "with", "and", "or"}) | {"not", "never"}
APPROACH_PREFIX = re.compile(r"^please answer this question[^:]*:\s*", re.IGNORECASE)
EARLIEST = re.compile(r"\b(earliest|first|oldest)\b", re.IGNORECASE)
LATEST = re.compile(r"\b(latest|most recent|newest|last)\b", re.IGNORECASE)
HOW_MANY = re.compile(r"\bhow many\b", re.IGNORECASE)


@dataclass
class Question:
    text: str
    entity: Optional[str] = None
    predicate: Optional[str] = None
    direction: str = "out"
    kind: str = "lookup"  # "lookup", "count", "earliest" or "latest"
    error: Optional[str] = None  # "no_entity", "no_relation" or "no_facts"


def _load_synonyms() -> dict:
    data = json.loads((Path(__file__).parent / "data" / "relations.json").read_text(encoding="utf-8"))
    expand = lambda key: PREFIXES[key.split(":")[0]] + key.split(":")[1]
    return {expand(key): words for key, words in data.items()}


class Parser:
    def __init__(self, kg: KnowledgeGraph, lexicon: Lexicon):
        self.kg = kg
        self.lex = lexicon
        self.phrases = {}  # "directed" -> [wdt:P57]
        for predicate, label in lexicon.prop2lbl.items():
            self.phrases.setdefault(label.lower(), []).append(predicate)
        for predicate, words in _load_synonyms().items():
            for word in words:
                self.phrases.setdefault(word, []).append(predicate)
        alternatives = sorted(self.phrases, key=len, reverse=True)
        self.phrase_pattern = re.compile(r"\b(" + "|".join(map(re.escape, alternatives)) + r")\b", re.IGNORECASE)
        self.fuzzy_labels = [l for l, ids in lexicon.lbl2ent.items()
                             if any(lexicon.is_film(q) or lexicon.is_human(q) for q in ids)]
        self.surnames = {}  # "spielberg" -> ["Q8877", "Q1866328", ...]
        for label_text, ids in lexicon.lbl2ent.items():
            if " " not in label_text:
                continue
            humans = [q for q in ids if lexicon.is_human(q)]
            if not humans:
                continue
            surname = label_text.rsplit(" ", 1)[-1]
            bucket = self.surnames.setdefault(surname, [])
            for q in humans:
                if q not in bucket:
                    bucket.append(q)

    def parse(self, text: str) -> Question:
        text = APPROACH_PREFIX.sub("", text.replace("‘", "'").replace("’", "'").strip())
        question = Question(text)
        span, candidates = self._find_entity(text)
        if not candidates:
            question.error = "no_entity"
            return question

        rest = text[:span[0]] + " " + text[span[1]:]
        predicates = self._find_predicates(rest)
        if HOW_MANY.search(rest):
            question.kind = "count"
        elif EARLIEST.search(rest) or LATEST.search(rest):
            other = [p for p in predicates if p != sb.RELEASE_DATE]
            if other:
                question.kind = "earliest" if EARLIEST.search(rest) else "latest"
                predicates = other
        if not predicates:
            question.entity, question.error = candidates[0], "no_relation"
            return question

        for predicate in predicates:
            for entity in candidates:
                out = self.kg.query(sb.has_facts(entity, predicate, "out"))
                into = self.kg.query(sb.has_facts(entity, predicate, "in"))
                if out or into:
                    question.entity, question.predicate = entity, predicate
                    question.direction = "out" if out and (not into or self.lex.is_film(entity)) else "in"
                    return question
        question.entity, question.predicate, question.error = candidates[0], predicates[0], "no_facts"
        return question

    def _find_predicates(self, text: str) -> List[str]:
        matches = sorted(self.phrase_pattern.findall(text), key=len, reverse=True)
        predicates = [p for m in matches for p in self.phrases[m.lower()]]
        return list(dict.fromkeys(predicates))

    def _find_entity(self, text: str) -> Tuple[Tuple[int, int], List[str]]:
        """The (start, end) of the entity in the text and its candidate Q-ids, best first."""
        # greedy first: "'The Cat o' Nine Tails'"; quotes never touch a letter on their outer side ("didn't", "Don't")
        for pattern in (r"(?<!\w)'(.+)'(?!\w)", r"(?<!\w)'(.+?)'(?!\w)", r'"(.+?)"'):
            for match in re.finditer(pattern, text):
                if match.group(1).lower() in self.lex.lbl2ent:
                    return match.span(1), self._rank(self.lex.lbl2ent[match.group(1).lower()])

        words = [(m.start(), m.end()) for m in re.finditer(r"[\w'&:.!?-]+", text)]
        for needs_capital in (True, False):  # "the box office of Interstellar": prefer the capitalised title
            for n in range(min(len(words), 10), 0, -1):
                for i in range(len(words) - n + 1):
                    start, end = words[i][0], words[i + n - 1][1]
                    raw = text[start:end].rstrip(",")
                    # "Who Am I?" and "Them!" keep their punctuation, "Inception?" loses it
                    for phrase in dict.fromkeys((raw, raw.rstrip("?."), raw.rstrip("?.!'").removesuffix("'s"))):
                        tokens = phrase.split()
                        capitalised = any(t[0].isupper() or t[0].isdigit() for t in tokens)
                        # "Or", "Her": a capitalised film title made of common words, but not the first word
                        if all(t.lower().strip("?!.") in STOPWORDS for t in tokens) and (i == 0 or not capitalised):
                            continue
                        if (needs_capital and not capitalised) or (n == 1 and not capitalised):
                            continue
                        if phrase.lower() in self.lex.lbl2ent:
                            if needs_capital and self._inside_longer_title(text, words, i, i + n - 1):
                                return (0, 0), []  # "Don't Look Up" isn't in the graph; don't answer for "Up"
                            return (start, start + len(phrase)), self._rank(self.lex.lbl2ent[phrase.lower()])
                        if n == 1:
                            surname = self._surname_candidates(phrase)
                            if surname:
                                return (start, start + len(phrase)), surname

        for start, end in reversed(words):  # last resort: a lower-case one-word film title ("who directed her")
            word = text[start:end]
            for phrase in dict.fromkeys((word, word.rstrip("?.,"), word.rstrip("?.!,"))):
                films = [e for e in self.lex.lbl2ent.get(phrase.lower(), []) if self.lex.is_film(e)]
                if films and phrase.lower() not in STOPWORDS:
                    return (start, start + len(phrase)), self._rank(films)

        best = None
        for n in range(1, min(len(words), 6) + 1):
            for i in range(len(words) - n + 1):
                start, end = words[i][0], words[i + n - 1][1]
                phrase = text[start:end].rstrip("?.!,").lower()
                tokens = phrase.split()
                if (len(phrase) < 5 or all(t in STOPWORDS for t in tokens)
                        or tokens[0] in FUZZY_EDGE_NOISE or tokens[-1] in FUZZY_EDGE_NOISE):
                    continue
                match = process.extractOne(phrase, self.fuzzy_labels, scorer=OSA.normalized_similarity,
                                           score_cutoff=0.85)
                if match and (best is None or match[1] > best[1]):
                    best = (match[0], match[1], (start, end))
        if best:
            return best[2], self._rank(self.lex.lbl2ent[best[0]])
        return (0, 0), []

    def _inside_longer_title(self, text: str, words: list, first: int, last: int) -> bool:
        """Whether words[first..last] sit inside a longer run of capitalised words, ignoring the question's
        first word and relation words ("IMDb ID"); "of"/"the" may be inside the run, "and"/"or"/commas end it."""
        relation_spans = [m.span() for m in self.phrase_pattern.finditer(text)]
        word = lambda k: text[words[k][0]:words[k][1]]
        adjacent = lambda a, b: text[words[a][1]:words[b][0]].strip() == ""
        is_relation = lambda k: any(a <= words[k][0] < b for a, b in relation_spans)
        for step, k in ((-1, first - 1), (1, last + 1)):
            while 0 < k < len(words) and adjacent(min(k, k - step), max(k, k - step)) and not is_relation(k):
                if word(k)[0].isupper() or word(k)[0].isdigit():
                    return True
                if word(k).lower() not in STOPWORDS or word(k).lower() in ("and", "or"):
                    break
                k += step
        return False

    def _surname_candidates(self, phrase: str) -> List[str]:
        """A capitalized single word can name a person by surname: "Spielberg" -> Steven first."""
        if " " in phrase or not phrase[:1].isupper():
            return []
        candidates = self.surnames.get(phrase.casefold())
        return self._rank(list(candidates)) if candidates else []

    def _rank(self, entities: List[str]) -> List[str]:
        """Films first, then the entity the graph knows most about."""
        entities = list(dict.fromkeys(entities))[:10]
        if len(entities) == 1:
            return entities
        degree = {e: int(self.kg.query(sb.degree(e)).rows[0][0].value) for e in entities}
        return sorted(entities, key=lambda e: (not self.lex.is_film(e), -degree[e]))
