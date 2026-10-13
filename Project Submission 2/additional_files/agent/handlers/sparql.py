"""Stage 1: runs plain SPARQL queries sent by the user and prints the results."""

import re
import time

from agent.kg import KnowledgeGraph, QueryError, QueryTimeout, SelectResult
from agent.nlg import format_term

MAX_ROWS_SHOWN = 25

# Code fences people (and the course examples) wrap queries in
_FENCE = re.compile(r"^\s*(```(?:sparql)?|'''|\"\"\"|‘’’|’’’)\s*|\s*(```|'''|\"\"\"|‘’’|’’’)\s*$", re.IGNORECASE)
# Optional prologue (PREFIX/BASE declarations, comments), then the query form
_QUERY_START = re.compile(
    r"^\s*(?:(?:PREFIX\s+[\w.-]*:\s*<[^>]*>|BASE\s*<[^>]*>|#[^\n]*)\s*)*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b",
    re.IGNORECASE,
)


def clean_query(text: str) -> str:
    query = text.strip()
    previous = None
    while previous != query:  # fences may be nested or repeated
        previous = query
        query = _FENCE.sub("", query).strip()
    return query


def looks_like_sparql(text: str) -> bool:
    query = clean_query(text)
    return bool(_QUERY_START.match(query)) and "{" in query


def format_result(result) -> str:
    if isinstance(result, bool):
        return "Yes." if result else "No."
    assert isinstance(result, SelectResult)
    if not result.rows:
        return "The query ran fine, but there are no results in the knowledge graph."
    lines = [" | ".join(format_term(t) for t in row) for row in result.rows[:MAX_ROWS_SHOWN]]
    hidden = len(result.rows) - MAX_ROWS_SHOWN
    if hidden > 0 or result.truncated:
        more = f"{hidden}+" if result.truncated else str(hidden)
        lines.append(f"... and {more} more results.")
    return "\n".join(lines)


class SparqlHandler:
    name = "sparql"

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def can_handle(self, text: str, session) -> bool:
        return looks_like_sparql(text)

    def handle(self, text: str, session, trace) -> str:
        query = clean_query(text)
        trace.add("sparql", query)
        start = time.perf_counter()
        try:
            result = self.kg.query(query)
        except QueryTimeout:
            return (f"That query took longer than {self.kg.query_timeout_s:.0f} seconds. "
                    "Could you make it more specific?")
        except QueryError as e:
            first_line = str(e).strip().splitlines()[0][:200] if str(e).strip() else "unknown error"
            return f"I couldn't run that query. The SPARQL seems invalid: {first_line}"
        finally:
            trace.add("query_time_s", f"{time.perf_counter() - start:.3f}")
        if isinstance(result, SelectResult):
            trace.add("rows", len(result.rows))
        return format_result(result)
