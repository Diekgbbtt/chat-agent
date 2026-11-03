"""
The agent: one session per chatroom, and routing of each message to the first handler that accepts it.

`Agent.answer(text, session_id)` is used by the Speakeasy bot, the CLI and the evaluation runner alike.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent.handlers.factual import FactualHandler
from agent.handlers.sparql import SparqlHandler
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon
from agent.observability import (emit, new_request_id, reset_request_id,
                                 set_request_id, to_jsonable)

log = logging.getLogger("agent.core")

MAX_INPUT_CHARS = 5_000
EMPTY_REPLY = "Your message was empty. Ask me something about movies!"


@dataclass
class Session:
    id: str
    state: Dict[str, Any] = field(default_factory=dict)
    turns: List[Dict[str, str]] = field(default_factory=list)


MAX_TURNS = 20


def append_turn(session: Session, user: str, reply: str) -> None:
    session.turns.append({"user": user, "reply": reply})
    del session.turns[:-MAX_TURNS]


class Trace:
    """The full trajectory of one answer.

    ``steps`` keeps the existing (step, detail) pairs so ``dict(trace.steps)``
    still works. ``to_dict`` and ``to_json`` expose the same data
    programmatically. Every step is also emitted at DEBUG level.
    """

    def __init__(self, request_id: str = ""):
        self.request_id = request_id or new_request_id()
        self.session_id = ""
        self.input = ""
        self.handler = ""
        self.reply = ""
        self.error = ""
        self.started_at = time.time()
        self.ended_at = 0.0
        self.steps: List[Tuple[str, Any]] = []

    def add(self, step: str, detail: Any) -> None:
        self.steps.append((step, detail))
        emit(logging.getLogger("agent.trace"), "trace.step", level=logging.DEBUG,
             step=step, detail=detail)

    def duration_ms(self) -> Optional[float]:
        if not self.ended_at:
            return None
        return round((self.ended_at - self.started_at) * 1000.0, 1)

    def to_dict(self) -> dict:
        return to_jsonable({
            "request_id": self.request_id,
            "session_id": self.session_id,
            "input": self.input,
            "handler": self.handler,
            "reply": self.reply,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms(),
            "steps": [{"step": step, "detail": detail} for step, detail in self.steps],
        })

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class Agent:
    def __init__(self, handlers: list):
        self.handlers = handlers
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def session(self, session_id: str) -> Session:
        with self._lock:
            return self._sessions.setdefault(session_id, Session(session_id))

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def answer(self, text: str, session_id: str = "local", trace: Optional[Trace] = None) -> str:
        trace = trace or Trace()
        token = set_request_id(trace.request_id)
        text = (text or "").strip()[:MAX_INPUT_CHARS]
        trace.session_id = session_id
        trace.input = text
        emit(log, "request.start", session_id=session_id, input=text)
        try:
            if not text:
                trace.reply = EMPTY_REPLY
                return EMPTY_REPLY
            session = self.session(session_id)
            for handler in self.handlers:
                if handler.can_handle(text, session):
                    trace.handler = handler.name
                    trace.add("handler", handler.name)
                    trace.reply = handler.handle(text, session, trace)
                    return trace.reply
            trace.reply = EMPTY_REPLY
            return EMPTY_REPLY
        except Exception as exc:
            trace.error = f"{type(exc).__name__}: {exc}"
            emit(log, "request.error", level=logging.ERROR, exc_info=True,
                 session_id=session_id, error=trace.error)
            raise
        finally:
            trace.ended_at = time.time()
            emit(log, "trace", trace=trace.to_dict(), duration_ms=trace.duration_ms())
            reset_request_id(token)


def build_agent(kg: KnowledgeGraph, llm=None, show_labels: bool = False, mode: str = "legacy",
                guard_client=None, qa_client=None, guard_schema=None, schema_card=None,
                max_steps: int = 6, deadline_s: float = 20.0, max_step_tokens: int = 300) -> Agent:
    """Raw SPARQL runs first and stays symbolic.

    ``legacy`` uses the deterministic factual pipeline. ``llm`` uses the
    two-stage guard, policy, and bounded QA tool loop.
    """
    from agent.config import PROJECT_ROOT
    from agent.guard.gate import GuardGate
    from agent.guard.schema import load_schema
    from agent.lexicon import Lexicon

    lexicon = Lexicon(kg)
    if mode == "legacy":
        factual = FactualHandler(kg, lexicon)
        if llm is None:
            return Agent([SparqlHandler(kg), factual])
        from agent.handlers.guarded import GuardedHandler
        return Agent([SparqlHandler(kg), GuardedHandler(factual, llm, show_labels)])
    if mode == "llm":
        from agent.handlers.llm_agent import LLMAgentHandler
        from agent.qa.agent import ResponseAgent
        from agent.qa.prompts import PromptBuilder
        from agent.qa.schema_card import SchemaCard
        from agent.tools.registry import ToolRegistry
        from agent.tools.resolve import ResolveEntityTool
        from agent.tools.sparql import RunSparqlTool
        schema = guard_schema or load_schema(PROJECT_ROOT / "agent" / "data" / "guardrails.json")
        card = schema_card or SchemaCard.load(PROJECT_ROOT / "agent" / "data" / "movie_schema.json")
        registry = ToolRegistry(ResolveEntityTool(kg, lexicon), RunSparqlTool(kg, lexicon))
        gate = GuardGate(guard_client, schema)
        qa_agent = ResponseAgent(qa_client, registry, PromptBuilder(card, schema), schema,
                                 max_steps=max_steps, deadline_s=deadline_s,
                                 max_step_tokens=max_step_tokens)
        return Agent([SparqlHandler(kg), LLMAgentHandler(gate, qa_agent, schema, show_labels)])
    raise ValueError(f"unknown AGENT_MODE: {mode}")
