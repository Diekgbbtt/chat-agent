"""Stage 3: the LLM turns one movie question into structured requests; code checks every field."""

import json
import re
from typing import List

from agent.query import QueryEngine, Request

MAX_REQUESTS = 3
OPS = ("<", "<=", ">", ">=", "=")
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
NEGATION = re.compile(r"\b(?:not|never)\b|\b(?:did|does|do|is|was|were|are|has|have|had|could|would|ca|wo)n'?t\b",
                      re.IGNORECASE)
# "not not direct", "didn't not direct": two adjacent negations cancel; the small model misses that
DOUBLE_NEGATION = re.compile(r"\b(not|never)\s+(not|never)\b|\b(did|does|do|is|was|were|are|has|have|had)n'?t\s+not\b",
                             re.IGNORECASE)

INSTRUCTIONS = """You turn one question about movies into requests for a knowledge graph. \
Never answer the question yourself.

Answer with JSON only: {"requests": [...]}, one request per thing asked (at most 3).

Request kinds:
- lookup: {"kind": "lookup", "entity": NAME, "property": ID or [ID, ...], "direction": "out" or "in", \
"negated": false}
  "out": the entity has the property ("Who directed Coco?": entity "Coco", P57, "out").
  "in": the answers have the property pointing to the entity ("Which films did Lee Unkrich direct?": \
entity "Lee Unkrich", P57, "in").
  "negated": true when the question asks what is NOT linked ("Who did not direct Coco?"). Two negations cancel.
- count: the same fields as lookup; counts the answers ("How many films did Lee Unkrich direct?").
- claim: a yes/no question: {"kind": "claim", "entity": NAME, "property": ID, "value": NAME or VALUE}.
- superlative: {"kind": "superlative", "entity": NAME, "property": ID, "direction": "out" or "in", \
"order_by": ID, "pick": "max" or "min"}: among the items linked to the entity, the one with the highest or \
lowest order_by value.
- filter: {"kind": "filter", "property": ID, "op": "<", "<=", ">", ">=" or "=", "value": "YYYY-MM-DD" or \
a number}: everything whose property value compares to the value. Put any negation into the operator \
yourself ("not above 5" is "<=" 5).
- chain: {"kind": "chain", "entity": NAME, "path": [ID, ID]}: follow properties step by step \
("Where was the director of Coco born?": path [P57, P19]).

Rules:
- NAME is the movie, person or thing as written in the question, spelling kept, without quotes.
- Use only property IDs from the list below. If several could fit, give a list of up to 3.
"""

EXAMPLES = [
    ("Who edited 'Lady Bird'?",
     [{"kind": "lookup", "entity": "Lady Bird", "property": "P1040", "direction": "out", "negated": False}]),
    ("which movies did greta gerwig write and who distributed Paddington 2",
     [{"kind": "lookup", "entity": "greta gerwig", "property": "P58", "direction": "in", "negated": False},
      {"kind": "lookup", "entity": "Paddington 2", "property": "P750", "direction": "out", "negated": False}]),
    ("Who didnt compose the music for Coco?",
     [{"kind": "lookup", "entity": "Coco", "property": "P86", "direction": "out", "negated": True}]),
    ("Did Ennio Morricone compose the score of The Mission?",
     [{"kind": "claim", "entity": "The Mission", "property": "P86", "value": "Ennio Morricone"}]),
    ("What is the lowest rated film starring Nicolas Cage?",
     [{"kind": "superlative", "entity": "Nicolas Cage", "property": "P161", "direction": "in",
       "order_by": "ddis:rating", "pick": "min"}]),
    ("Which films came out before 1903?",
     [{"kind": "filter", "property": "P577", "op": "<", "value": "1903"}]),
]


def _prompt(engine: QueryEngine) -> str:
    lines = [f"{p.id}: {p.label} [{p.shape}]" for p in engine.properties.values()]
    return INSTRUCTIONS + "\nProperties (ID: label [value type]):\n" + "\n".join(lines)


class PlanError(ValueError):
    pass


class Planner:
    def __init__(self, llm, engine: QueryEngine):
        self.llm = llm
        self.engine = engine
        self.system = _prompt(engine)

    def plan(self, question: str, feedback: str = "") -> List[Request]:
        """Checked requests for the question; raises PlanError if the LLM's output doesn't fit."""
        question = re.sub(r"\s+", " ", DOUBLE_NEGATION.sub(lambda m: m.group(3) or "", question)).strip()
        messages = [{"role": "system", "content": self.system}]
        for example, requests in EXAMPLES:
            messages += [{"role": "user", "content": example},
                         {"role": "assistant", "content": json.dumps({"requests": requests})}]
        messages.append({"role": "user", "content": question + (f"\n\n{feedback}" if feedback else "")})
        raw = self.llm.chat(messages, max_new_tokens=200)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group(0))
        except (AttributeError, ValueError):
            raise PlanError(f"not JSON: {raw[:200]!r}")
        items = data.get("requests") if isinstance(data, dict) else None
        if not isinstance(items, list) or not items:
            raise PlanError("no requests")
        requests = [self._check(item) for item in items[:MAX_REQUESTS]]
        if not NEGATION.search(question):
            for request in requests:
                request.negated = False  # a negation the question doesn't have
        return requests

    def _property(self, pid) -> str:
        prop = self.engine.properties.get(str(pid).strip())
        if prop is None:
            raise PlanError(f"unknown property {pid!r}")
        return prop.iri

    def _check(self, item) -> Request:
        if not isinstance(item, dict):
            raise PlanError("a request is not an object")
        kind = item.get("kind")
        request = Request(kind=kind, entity=str(item.get("entity") or "").strip(),
                          direction=item.get("direction", "out"), negated=item.get("negated") is True,
                          value=str(item.get("value") if item.get("value") is not None else "").strip())
        if kind not in ("lookup", "count", "claim", "superlative", "filter", "chain"):
            raise PlanError(f"unknown kind {kind!r}")
        if request.direction not in ("out", "in"):
            raise PlanError(f"bad direction {request.direction!r}")
        if kind != "filter" and not request.entity:
            raise PlanError(f"{kind} needs an entity")

        props = item.get("path") if kind == "chain" else item.get("property")
        props = props if isinstance(props, list) else [props]
        if not 1 <= len(props) <= 3 or (kind == "chain" and len(props) < 2):
            raise PlanError("wrong number of properties")
        request.properties = [self._property(p) for p in props]

        if kind == "claim" and not request.value:
            raise PlanError("claim needs a value")
        if kind == "superlative":
            request.order_by = self._property(item.get("order_by"))
            request.pick = item.get("pick", "max")
            if self.engine.by_iri[request.order_by].shape not in ("number", "date") or request.pick not in ("max", "min"):
                raise PlanError("superlative needs a number or date order_by and pick max/min")
        if kind == "filter":
            request.op = item.get("op")
            shape = self.engine.by_iri[request.properties[0]].shape
            pattern = {"date": DATE, "number": NUMBER}.get(shape)
            if request.op not in OPS or pattern is None or not pattern.match(request.value):
                raise PlanError(f"filter needs an operator and a {shape} value that fits the property")
        return request
