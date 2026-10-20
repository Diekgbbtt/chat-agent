"""Normalisation layer for adversarial question forms.

Runs once per message at the Phase 3 seam, before `Parser.parse`. It repairs quote
shapes, strips trailing clauses, resolves title mentions to graph labels, rewrites
recycled relation phrases, and reports the signals the handler needs: negation
(use the complement), two mentions (clarify) and a yes/no claim.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rapidfuzz import process
from rapidfuzz.distance import OSA

from agent import sparql_builder as sb
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.parser import APPROACH_PREFIX, STOPWORDS, Parser

QUOTES = "'\""
CURLY = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
TRIM = " \t\r\n.,?!;:"
CLEAN = " \t\r\n.,?!;:'\""
REWRITE_TRIM = " \t\r\n.,?;:"
TOKEN = re.compile(r"[\w'&:.!?-]+")
NEGATION = re.compile(r"(?:\bnot\b|\bnever\b|n't\b)", re.IGNORECASE)
ARTICLES = ("the ", "an ", "a ")
SENTENCE_END = ".!?"
EDGE_STOPWORDS = STOPWORDS | {
    "i", "i'm", "im", "you", "we", "they", "he", "she", "love", "liked",
    "told", "say", "said", "friend", "friends", "really", "just", "also",
    "watch", "watched", "watching", "see", "seen", "saw",
    "recommend", "recommended", "recommends",
}

FUZZY_CUTOFF = 0.85
SHORT_CORE_LEN = 6
SHORT_FUZZY_CUTOFF = 0.80
FUZZY_MARGIN = 0.05
FUZZY_EPS = 1e-6  # rate borders like 0.80 survive the float conversion inside rapidfuzz
MIN_FUZZY_CHARS = 5
MIN_TAIL_CHARS = 3
SHIELD_TRIM = " \t\r\n.,?!;:"

CLAIM_DID = re.compile(
    r"^\s*(?:did|does|do)\s+(.+?)\s+(direct|directed|write|wrote|written|compose|composed|make|made)"
    r"\s+(.+?)\s*[?.!]*\s*$", re.IGNORECASE)
CLAIM_WAS = re.compile(
    r"^\s*(?:was|were|is|are)\s+(.+?)\s+(directed|written|composed|made)\s+by\s+(.+?)\s*[?.!]*\s*$",
    re.IGNORECASE)
CLAIM_VERBS = {
    "direct": sb.DIRECTOR, "directed": sb.DIRECTOR, "make": sb.DIRECTOR, "made": sb.DIRECTOR,
    "write": sb.SCREENWRITER, "wrote": sb.SCREENWRITER, "written": sb.SCREENWRITER,
    "compose": sb.COMPOSER, "composed": sb.COMPOSER,
}
UNIVERSES = {"actor": "actor", "actors": "actor", "actress": "actor", "actresses": "actor",
             "director": "director", "directors": "director"}
PARAPHRASES = (
    (re.compile(r"\b(?:did|does) the directing (?:for|of|on)\b", re.IGNORECASE), "directed"),
    (re.compile(r"\b(?:was|is|were|are) at the helm of\b", re.IGNORECASE), "directed"),
    (re.compile(r"\b(?:was|is|were|are) behind the camera (?:on|for|of)\b", re.IGNORECASE), "directed"),
    (re.compile(r"\b(?:did|does) the writing (?:for|of|on)\b", re.IGNORECASE), "wrote"),
    (re.compile(r"\b(?:did|does) the composing (?:for|of|on)\b", re.IGNORECASE), "composed"),
)


def strip_article(text: str) -> str:
    """Lower-cased text without a leading English article ("The Matrix" -> "matrix")."""
    text = re.sub(r"\s+", " ", text.strip().casefold())
    for article in ARTICLES:
        if text.startswith(article):
            return text[len(article):]
    return text


@dataclass
class Claim:
    film: str
    predicate: str
    person: str


@dataclass
class Plan:
    text: str
    negated: bool = False
    clarify: bool = False
    claim: Optional[Claim] = None
    universe: Optional[str] = None  # "actor" or "director" when the question names the answer class
    films: List[str] = field(default_factory=list)  # film mentions of a negated question, in text order
    notes: List[str] = field(default_factory=list)


@dataclass
class Resolution:
    qids: List[str]
    source: str
    matched: str


@dataclass
class _Mention:
    start: int
    end: int
    raw: str
    quoted: bool = False
    whole: bool = True
    resolution: Optional[Resolution] = None


class Preprocessor:
    """Normalises one message into a Plan; the handler then answers from the plan."""

    def __init__(self, kg: KnowledgeGraph, lexicon: Lexicon, parser: Parser):
        self.kg = kg
        self.lex = lexicon
        self.parser = parser
        self.core2ent: Dict[str, List[str]] = {}
        for label, qids in lexicon.lbl2ent.items():
            core = strip_article(label)
            bucket = self.core2ent.setdefault(core, [])
            for qid in qids:
                if qid not in bucket:
                    bucket.append(qid)
        self.cores = sorted(self.core2ent)
        self.fuzzy_cores = [core for core in self.cores
                            if any(lexicon.is_film(q) or lexicon.is_human(q) for q in self.core2ent[core])]

    # ---------------------------------------------------------------- public

    def analyze(self, text: str) -> Plan:
        plan = Plan(text=text)
        cleaned = APPROACH_PREFIX.sub("", text).strip()
        cleaned, notes = self._apply_paraphrases(cleaned)
        plan.notes.extend(notes)
        cleaned = self._normalise_quotes(cleaned)
        cleaned = self._strip_trailing_clause(cleaned)
        mentions, clarify = self._scan(cleaned)
        plan.negated = NEGATION.search(self._shield(cleaned, mentions)) is not None
        if plan.negated:
            plan.universe = self._universe(cleaned, mentions)
            if plan.universe is not None:
                # "which actors did not direct X": the noun names the answer class, the verb names the
                # relation; remove the noun so it cannot hijack the relation phrase
                cleaned = self._detach_noun(cleaned, plan.universe)
                plan.notes.append(f"{plan.universe} noun scopes the complement universe")
                mentions, clarify = self._scan(cleaned)
        claim = None if plan.negated else self._detect_claim(cleaned)
        if claim is None and self._two_film_sentences(cleaned, mentions):
            clarify = True
            plan.notes.append("film mentions in two sentences")
        if claim is None and clarify:
            plan.notes.append("ambiguous or partial mention")
        plan.claim = claim
        plan.clarify = claim is None and clarify
        if plan.negated:
            plan.films = self._mentioned_films(mentions)
        plan.text = cleaned if claim is not None else self._rewrite(cleaned, mentions)
        return plan

    # ----------------------------------------------------------- normalising

    def _apply_paraphrases(self, text: str) -> Tuple[str, List[str]]:
        notes = []
        for pattern, word in PARAPHRASES:
            text, count = pattern.subn(word, text)
            if count:
                notes.append(f"{pattern.pattern} -> {word}")
        return text, notes

    def _normalise_quotes(self, text: str) -> str:
        """Straighten curly quotes, collapse doubled quotes, and rewrite known title pairs to their labels."""
        text = "".join(CURLY.get(ch, ch) for ch in text)
        text = re.sub(r"'{2,}", "'", text)
        out: List[str] = []
        positions = [i for i, ch in enumerate(text) if ch in QUOTES]
        last = positions[-1] if positions else -1
        index = 0
        while index < len(text):
            if text[index] not in QUOTES:
                out.append(text[index])
                index += 1
                continue
            known = self._known_close(text, index, positions)
            if known is not None:
                close, canonical = known
                out.append("'" + canonical + "'")
                index = close + 1
                continue
            if index == last:
                canonical = self._canonical(text[index + 1:])
                if canonical is not None:
                    out.append("'" + canonical + "'")
                    index = len(text)
                    continue
            out.append(text[index])
            index += 1
        return "".join(out)

    def _known_close(self, text: str, index: int, positions: List[int]) -> Optional[Tuple[int, str]]:
        """The closing quote and label of the longest known title that opens at `index`, if any."""
        char = text[index]
        if index > 0 and text[index - 1].isalnum():
            return None
        for close in reversed(positions):
            if close <= index:
                break
            if text[close] != char or (close + 1 < len(text) and text[close + 1].isalnum()):
                continue
            canonical = self._canonical(text[index + 1:close])
            if canonical is not None:
                return close, canonical
        return None

    def _canonical(self, inner: str) -> Optional[str]:
        """The graph label for a quoted title, or None when the text is not a known title."""
        if len(inner.strip(TRIM)) < MIN_TAIL_CHARS or not self._known(inner):
            return None
        resolution = self._resolve(inner)
        if resolution is None or not resolution.qids:
            return inner.strip()
        best = next((q for q in resolution.qids
                     if self.lex.is_film(q) or self.lex.is_human(q)), resolution.qids[0])
        return self.lex.label(best)

    def _known(self, text: str) -> bool:
        return any(core in self.core2ent for core in self._cores(text))

    def _strip_trailing_clause(self, text: str) -> str:
        """Drop a trailing ", ..." clause that follows a quoted title."""
        for start, end, content in self._quoted_spans(text):
            if not self._known(content):
                continue
            if not re.match(r"\s*,\s*\S", text[end + 1:]):
                continue
            stripped = text.rstrip()
            punct = stripped[-1] if stripped and stripped[-1] in ".?!" else ""
            return text[:end + 1].rstrip() + punct
        return text

    # -------------------------------------------------------------- scanning

    def _quoted_spans(self, text: str) -> List[Tuple[int, int, str]]:
        spans = []
        index, length = 0, len(text)
        while index < length:
            char = text[index]
            if char not in QUOTES or (index > 0 and text[index - 1].isalnum()):
                index += 1
                continue
            positions = [i for i in range(index + 1, length)
                         if text[i] == char and not (i + 1 < length and text[i + 1].isalnum())]
            target = None
            for close in reversed(positions):
                inner = text[index + 1:close].strip(TRIM)
                if inner and self._known(inner):
                    target = close
                    break
            if target is None and positions:
                target = positions[0]
            if target is None:
                index += 1
                continue
            spans.append((index, target, text[index + 1:target]))
            index = target + 1
        return spans

    def _runs(self, text: str, excluded: List[Tuple[int, int]]) -> List[List[Tuple[int, int, str]]]:
        """Maximal runs of non-relation words, split at relation phrases and punctuation."""
        relation_spans = [m.span() for m in self.parser.phrase_pattern.finditer(text)]
        runs: List[List[Tuple[int, int, str]]] = []
        current: List[Tuple[int, int, str]] = []
        for match in TOKEN.finditer(text):
            start, end = match.span()
            word = match.group(0)
            blocked = any(start < b and end > a for a, b in excluded)
            if not blocked:
                blocked = any(start < b and end > a for a, b in relation_spans)
            if blocked or not any(ch.isalnum() for ch in word):
                if current:
                    runs.append(current)
                    current = []
                continue
            current.append((start, end, word))
        if current:
            runs.append(current)
        return runs

    def _scan(self, text: str) -> Tuple[List[_Mention], bool]:
        mentions: List[_Mention] = []
        clarify = False
        for start, end, content in self._quoted_spans(text):
            mention = _Mention(start, end + 1, content, quoted=True)
            mentions.append(mention)
            resolution = self._resolve(content)
            if resolution is None:
                if self._contained_subrun(content) is not None:
                    clarify = True
                continue
            mention.resolution = resolution
            if not self._interesting(resolution):
                clarify = True
        excluded = [(m.start, m.end) for m in mentions if m.quoted]
        for run in self._runs(text, excluded):
            low, high = 0, len(run)
            while low < high and self._stopword(run[low][2]):
                low += 1
            while high > low and self._stopword(run[high - 1][2]):
                high -= 1
            if low >= high:
                continue
            raw = text[run[low][0]:run[high - 1][1]]
            if all(self._stopword(word) for word in raw.split()):
                continue
            resolution = self._resolve(raw)
            if resolution is None:
                trimmed, trim_start, trim_end = self._trim_negation(raw)
                if trimmed != raw:
                    # exact only: a fuzzy match would turn "don't look up" into the film Lock Up
                    resolution = self._resolve(trimmed, allow_fuzzy=False)
                    if resolution is not None and self._interesting(resolution):
                        mentions.append(_Mention(run[low][0] + trim_start,
                                                 run[low][0] + trim_end, trimmed,
                                                 False, True, resolution))
                        continue
            if resolution is not None:
                if self._interesting(resolution):
                    mentions.append(_Mention(run[low][0], run[high - 1][1], raw, False, True, resolution))
                else:
                    clarify = True
                continue
            if self._lowercase(raw) and self._contained_subrun(raw) is not None:
                clarify = True
                continue
            mentions.extend(self._subrun_mentions(run, low, high, text))
        return mentions, clarify

    def _trim_negation(self, raw: str) -> Tuple[str, int, int]:
        """Strip negation words at the edges so they cannot block an entity mention."""
        matches = list(TOKEN.finditer(raw))
        first, last = 0, len(matches)
        while first < last and self._negation_word(matches[first].group(0)):
            first += 1
        while last > first and self._negation_word(matches[last - 1].group(0)):
            last -= 1
        if first == 0 and last == len(matches) or first >= last:
            return raw, 0, len(raw)
        return (raw[matches[first].start():matches[last - 1].end()],
                matches[first].start(), matches[last - 1].end())

    @staticmethod
    def _negation_word(word: str) -> bool:
        word = word.strip(CLEAN).casefold()
        return word in {"not", "never"} or word.endswith("n't")

    def _contained_subrun(self, text: str) -> Optional[str]:
        """A lower-case strict sub-run of `text` that resolves on its own."""
        matches = list(TOKEN.finditer(text))
        count = len(matches)
        for size in range(count - 1, 0, -1):
            for start in range(0, count - size + 1):
                raw = text[matches[start].start():matches[start + size - 1].end()]
                if not self._lowercase(raw) or all(self._stopword(word) for word in raw.split()):
                    continue
                resolution = self._resolve(raw, allow_fuzzy=False)
                if resolution is not None and self._interesting(resolution):
                    return raw
        return None

    def _subrun_mentions(self, run, low: int, high: int, text: str) -> List[_Mention]:
        """Longest-match mentions inside a run that does not resolve as a whole (never rewritten)."""
        out = []
        index = low
        while index < high:
            matched = False
            for size in range(high - index, 0, -1):
                raw = text[run[index][0]:run[index + size - 1][1]]
                if all(self._stopword(word) for word in raw.split()):
                    continue
                resolution = self._resolve(raw, allow_fuzzy=False)
                if resolution is not None and resolution.qids:
                    out.append(_Mention(run[index][0], run[index + size - 1][1], raw, False, False, resolution))
                    index += size
                    matched = True
                    break
            if not matched:
                index += 1
        return out

    def _two_film_sentences(self, text: str, mentions: List[_Mention]) -> bool:
        film_mentions = [m for m in mentions
                         if m.resolution and any(self.lex.is_film(q) for q in m.resolution.qids)]
        if len(film_mentions) < 2:
            return False
        shielded = self._shield(text, mentions)
        enders = [i for i, ch in enumerate(shielded) if ch in SENTENCE_END]
        sentences = {sum(1 for i in enders if i < m.start) for m in film_mentions}
        return len(sentences) >= 2

    @staticmethod
    def _shield(text: str, mentions: List[_Mention]) -> str:
        chars = list(text)
        for mention in mentions:
            end = mention.end
            while end > mention.start and text[end - 1] in SHIELD_TRIM:
                end -= 1
            for i in range(mention.start, min(end, len(chars))):
                chars[i] = " "
        return "".join(chars)

    def _universe(self, text: str, mentions: List[_Mention]) -> Optional[str]:
        """The person class the question names ("actors", "directors"), outside any title mention."""
        spans = [(m.start, m.end) for m in mentions]
        for match in TOKEN.finditer(text):
            if any(match.start() < b and match.end() > a for a, b in spans):
                continue
            word = match.group(0).strip(CLEAN).casefold()
            if word in UNIVERSES:
                return UNIVERSES[word]
        return None

    def _detach_noun(self, text: str, universe: str) -> str:
        """Remove the universe noun so the verb, not the noun, chooses the relation."""
        words = sorted((w for w, u in UNIVERSES.items() if u == universe), key=len, reverse=True)
        pattern = re.compile(r"\b(" + "|".join(map(re.escape, words)) + r")\b", re.IGNORECASE)
        spans = [(start, end) for start, end, _content in self._quoted_spans(text)]
        out, last = [], 0
        for match in pattern.finditer(text):
            if any(match.start() < b and match.end() > a for a, b in spans):
                continue
            out.append(text[last:match.start()])
            last = match.end()
        out.append(text[last:])
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def _mentioned_films(self, mentions: List[_Mention]) -> List[str]:
        """Every film the mentions resolve to, in text order (a negated question may name several)."""
        films: List[str] = []
        for mention in sorted(mentions, key=lambda m: m.start):
            if mention.resolution is None:
                continue
            qid = next((q for q in mention.resolution.qids if self.lex.is_film(q)), None)
            if qid is not None and qid not in films:
                films.append(qid)
        return films

    # ------------------------------------------------------------ resolution

    def _cores(self, raw: str) -> List[str]:
        """Candidate cores, most literal form first (a kept punctuation variant before the stripped variant)."""
        text = raw.strip().strip(QUOTES).strip()
        cleaned = text.strip(CLEAN)
        return list(dict.fromkeys(core for core in
                                  (strip_article(text), strip_article(cleaned)) if core))

    def _resolve(self, raw: str, allow_fuzzy: bool = True) -> Optional[Resolution]:
        """Best resolution for a mention text, or None when nothing in the graph matches."""
        cores = self._cores(raw)
        if not cores:
            return None
        for core_text in (raw.strip().strip(QUOTES).strip(), raw.strip(CLEAN)):
            norm = re.sub(r"\s+", " ", core_text).casefold()
            if norm.startswith(ARTICLES):
                qids = self.lex.lbl2ent.get(norm)
                if qids:
                    return self._resolution(qids, "label", norm)
        for core in cores:
            qids = self.core2ent.get(core)
            if qids:
                return self._resolution(qids, "family", core)
        fuzzy = strip_article(raw.strip(CLEAN))
        if allow_fuzzy and len(fuzzy) >= MIN_FUZZY_CHARS:
            matched = self._fuzzy_core(fuzzy)
            if matched is not None:
                return self._resolution(self.core2ent[matched], "fuzzy", matched)
        return None

    def _resolution(self, qids: List[str], source: str, matched: str) -> Resolution:
        return Resolution(self.parser._rank(list(dict.fromkeys(qids))), source, matched)

    def _fuzzy_core(self, core: str) -> Optional[str]:
        cutoff = SHORT_FUZZY_CUTOFF if len(core) <= SHORT_CORE_LEN else FUZZY_CUTOFF
        matches = process.extract(core, self.fuzzy_cores, scorer=OSA.normalized_similarity,
                                  limit=2, score_cutoff=cutoff - FUZZY_EPS)
        if not matches:
            return None
        best, score = matches[0][0], matches[0][1]
        second = matches[1][1] if len(matches) > 1 else 0.0
        if score < cutoff - FUZZY_EPS or score - second < FUZZY_MARGIN:
            return None
        return best

    def _interesting(self, resolution: Resolution) -> bool:
        return any(self.lex.is_film(q) or self.lex.is_human(q) for q in resolution.qids)

    @staticmethod
    def _stopword(word: str) -> bool:
        word = word.strip(CLEAN)
        return not word or word.casefold() in EDGE_STOPWORDS

    @staticmethod
    def _lowercase(raw: str) -> bool:
        return raw == raw.lower() and any(ch.isalpha() for ch in raw)

    # ---------------------------------------------------------------- claims

    def _detect_claim(self, text: str) -> Optional[Claim]:
        match = CLAIM_DID.match(text)
        if match:
            person_raw, verb, film_raw = match.group(1), match.group(2), match.group(3)
        else:
            match = CLAIM_WAS.match(text)
            if not match:
                return None
            film_raw, verb, person_raw = match.group(1), match.group(2), match.group(3)
        predicate = CLAIM_VERBS.get(verb.casefold())
        if predicate is None:
            return None
        film = self._resolve_text(film_raw, want_film=True)
        person = self._resolve_text(person_raw, want_film=False)
        if film is None or person is None or film == person:
            return None
        return Claim(film, predicate, person)

    def _resolve_text(self, raw: str, want_film: bool) -> Optional[str]:
        resolution = self._resolve(raw)
        if resolution is None:
            return None
        qids = [q for q in resolution.qids if self.lex.is_film(q) is want_film]
        return qids[0] if qids else None

    # -------------------------------------------------------------- rewriting

    def _rewrite(self, text: str, mentions: List[_Mention]) -> str:
        """Quote the most prominent resolved mentions; lower-ranked words that happen to be titles stay untouched."""
        whole = [m for m in mentions if m.whole and m.resolution and m.resolution.qids]
        if not whole:
            return text
        best = min(self._priority(m) for m in whole)
        out = text
        for mention in sorted((m for m in whole if self._priority(m) == best),
                              key=lambda m: m.start, reverse=True):
            target = next((q for q in mention.resolution.qids
                           if self.lex.is_film(q) or self.lex.is_human(q)), None)
            if target is None:
                continue
            start, end = mention.start, mention.end
            while end > start and text[end - 1] in REWRITE_TRIM:
                end -= 1
            replacement = "'" + self.lex.label(target) + "'"
            if end <= start or out[start:end] == replacement:
                continue
            out = out[:start] + replacement + out[end:]
        return out

    @staticmethod
    def _priority(mention: _Mention) -> int:
        """0 quoted, 1 multi-word, 2 capitalised, 3 lowercase single word."""
        if mention.quoted:
            return 0
        raw = mention.raw.strip(QUOTES).strip()
        if " " in raw:
            return 1
        if raw[:1].isupper() or raw[:1].isdigit():
            return 2
        return 3
