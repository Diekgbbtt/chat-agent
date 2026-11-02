"""Read-only query enforcement and labelled row observations."""

import json
import re
from dataclasses import dataclass
from typing import Optional

from agent.kg import QueryError, QueryTimeout, SelectResult
from agent.lexicon import qid

MAX_QUERY_CHARS = 4_000
DEFAULT_OBSERVATION_CHARS = 1_200
_FENCE = re.compile(r"^\s*(```(?:sparql)?|'''|\"\"\"|‘’’|’’’)\s*|\s*(```|'''|\"\"\"|‘’’|’’’)\s*$", re.IGNORECASE)
_QUERY_START = re.compile(
    r"^\s*(?:(?:PREFIX\s+[\w.-]*:\s*<[^>]*>|BASE\s*<[^>]*>|#[^\n]*)\s*)*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b",
    re.IGNORECASE,
)
_BANNED = re.compile(r"\b(SERVICE|FROM|WITH|LOAD|INSERT|DELETE|DROP|CLEAR|CREATE|ADD|MOVE|COPY)\b",
                     re.IGNORECASE)
_AGENT_FORMS = {"SELECT", "ASK"}
_RAW_FORMS = _AGENT_FORMS | {"CONSTRUCT", "DESCRIBE"}


class QueryRejected(ValueError):
    """The query is not a read-only query allowed by the runtime."""


def clean_query(text: str) -> str:
    query = (text or "").strip()
    previous = None
    while previous != query:
        previous = query
        query = _FENCE.sub("", query).strip()
    return query


def _mask_literals_and_comments(query: str) -> str:
    """Replace string contents and comments with spaces, keeping offsets stable."""
    out = list(query)
    index, length = 0, len(query)
    while index < length:
        char = query[index]
        if char == "#":
            end = query.find("\n", index)
            end = length if end < 0 else end
            for position in range(index, end):
                out[position] = " "
            index = end
            continue
        if char in "'\"":
            quote = char
            triple = query.startswith(quote * 3, index)
            width = 3 if triple else 1
            index += width
            while index < length:
                if query.startswith(quote * width, index):
                    index += width
                    break
                if query[index] == "\\":
                    out[index] = " "
                    index += 1
                    if index < length:
                        out[index] = " "
                        index += 1
                    continue
                out[index] = " "
                index += 1
            continue
        index += 1
    return "".join(out)


class QueryGuard:
    def validate(self, text: str, mode: str = "agent") -> str:
        if mode not in ("agent", "raw"):
            raise ValueError(f"unknown query mode: {mode}")
        query = clean_query(text)
        if not query:
            raise QueryRejected("the query is empty")
        if len(query) > MAX_QUERY_CHARS:
            raise QueryRejected(f"the query exceeds {MAX_QUERY_CHARS} characters")
        start = _QUERY_START.match(query)
        if not start:
            raise QueryRejected("the query must start with SELECT, ASK, CONSTRUCT, or DESCRIBE")
        form = start.group(1).upper()
        allowed = _AGENT_FORMS if mode == "agent" else _RAW_FORMS
        if form not in allowed:
            raise QueryRejected(f"{form} is not allowed in {mode} mode")
        banned = _BANNED.search(_mask_literals_and_comments(query))
        if banned:
            raise QueryRejected(f"{banned.group(1).upper()} is not allowed")
        return query


@dataclass(frozen=True)
class Observation:
    rows: tuple
    truncated: bool = False
    error: Optional[str] = None

    @property
    def row_ids(self):
        return tuple(row["row_id"] for row in self.rows)

    def as_json(self) -> str:
        return json.dumps({"rows": list(self.rows), "truncated": self.truncated, "error": self.error},
                          ensure_ascii=False)


def _format_term(term, lexicon) -> Optional[str]:
    if term is None:
        return None
    if term.kind == "iri":
        if term.value.startswith("http://www.wikidata.org/entity/"):
            key = qid(term.value)
            return lexicon.ent2lbl.get(key, key)
        if term.value.startswith("http://www.wikidata.org/prop/direct/"):
            return lexicon.prop2lbl.get(term.value, term.value.rsplit("/", 1)[-1])
        return term.value
    return str(term.value).removesuffix("T00:00:00Z")


class ResultFormatter:
    def __init__(self, lexicon, max_chars: int = DEFAULT_OBSERVATION_CHARS):
        self.lexicon = lexicon
        self.max_chars = max_chars

    def format(self, result, max_chars: Optional[int] = None) -> Observation:
        limit = self.max_chars if max_chars is None else max_chars
        if isinstance(result, bool):
            return Observation(({"row_id": "r0", "boolean": result},))
        assert isinstance(result, SelectResult)
        rows, truncated = [], bool(result.truncated)
        for index, values in enumerate(result.rows):
            row = {"row_id": f"r{index}"}
            for variable, value in zip(result.variables, values):
                row[variable] = _format_term(value, self.lexicon)
            candidate = rows + [row]
            if len(json.dumps(candidate, ensure_ascii=False)) > limit:
                truncated = True
                break
            rows = candidate
        return Observation(tuple(rows), truncated=truncated)


class RunSparqlTool:
    name = "run_sparql"

    def __init__(self, kg, lexicon, max_chars: int = DEFAULT_OBSERVATION_CHARS):
        self.kg = kg
        self.guard = QueryGuard()
        self.formatter = ResultFormatter(lexicon, max_chars=max_chars)

    def run(self, query: str) -> Observation:
        try:
            cleaned = self.guard.validate(query)
            result = self.kg.query(cleaned)
            return self.formatter.format(result)
        except QueryRejected as exc:
            return Observation((), error=str(exc))
        except QueryTimeout as exc:
            return Observation((), error=f"query timed out: {exc}")
        except QueryError as exc:
            return Observation((), error=f"invalid query: {exc}")
        except Exception as exc:  # noqa: BLE001 - the model receives a typed observation
            return Observation((), error=f"query failed: {exc}")
