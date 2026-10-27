"""
The agent: one session per chatroom, and routing of each message to the first handler that accepts it.

`Agent.answer(text, session_id)` is used by the Speakeasy bot, the CLI and the evaluation runner alike.
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent.handlers.factual import FactualHandler
from agent.handlers.sparql import SparqlHandler
from agent.kg import KnowledgeGraph
from agent.lexicon import Lexicon

MAX_INPUT_CHARS = 5_000
EMPTY_REPLY = "Your message was empty. Ask me something about movies!"


@dataclass
class Session:
    id: str
    state: Dict[str, Any] = field(default_factory=dict)


class Trace:
    """(step, detail) pairs explaining how an answer was produced; shown by `cli --debug`."""

    def __init__(self):
        self.steps: List[Tuple[str, Any]] = []

    def add(self, step: str, detail: Any) -> None:
        self.steps.append((step, detail))


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
        text = (text or "").strip()[:MAX_INPUT_CHARS]
        if not text:
            return EMPTY_REPLY
        session = self.session(session_id)
        for handler in self.handlers:
            if handler.can_handle(text, session):
                trace.add("handler", handler.name)
                return handler.handle(text, session, trace)
        return EMPTY_REPLY


def build_agent(kg: KnowledgeGraph, llm=None, show_labels: bool = False) -> Agent:
    """SPARQL queries first (Stage 1); with an LLM, everything else passes the guardrails (Stage 3)
    before the factual pipeline (Stage 2); without one, the agent is the Stage 2 agent."""
    factual = FactualHandler(kg, Lexicon(kg))
    if llm is None:
        return Agent([SparqlHandler(kg), factual])
    from agent.handlers.guarded import GuardedHandler
    return Agent([SparqlHandler(kg), GuardedHandler(factual, llm, show_labels)])
