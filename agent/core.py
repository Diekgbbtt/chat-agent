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
    turns: List[Dict[str, str]] = field(default_factory=list)


MAX_TURNS = 20


def append_turn(session: Session, user: str, reply: str) -> None:
    session.turns.append({"user": user, "reply": reply})
    del session.turns[:-MAX_TURNS]


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


def build_agent(kg: KnowledgeGraph, llm=None, show_labels: bool = False, mode: str = "legacy",
                guard_client=None, qa_client=None, guard_schema=None, schema_card=None,
                max_steps: int = 6, deadline_s: float = 20.0, max_step_tokens: int = 300) -> Agent:
    """SPARQL queries first (Stage 1); with an LLM, everything else passes the guardrails (Stage 3)
    before the factual pipeline (Stage 2); without one, the agent is the Stage 2 agent."""
    from agent.config import PROJECT_ROOT
    from agent.guard.gate import GuardGate
    from agent.guard.schema import load_schema
    from agent.lexicon import Lexicon

    lexicon = Lexicon(kg)
    factual = FactualHandler(kg, lexicon)
    if mode == "legacy":
        if llm is None:
            return Agent([SparqlHandler(kg), factual])
        from agent.handlers.guarded import GuardedHandler
        return Agent([SparqlHandler(kg), GuardedHandler(factual, llm, show_labels)])
    if mode == "guard_only":
        from agent.handlers.guard_only import GuardOnlyHandler
        schema = guard_schema or load_schema(PROJECT_ROOT / "agent" / "data" / "guardrails.json")
        gate = GuardGate(guard_client, schema)
        return Agent([SparqlHandler(kg), GuardOnlyHandler(factual, gate, schema, show_labels)])
    if mode == "tools":
        from agent.handlers.tool_agent import ToolAgentHandler
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
        return Agent([SparqlHandler(kg), ToolAgentHandler(gate, qa_agent, schema, show_labels)])
    raise ValueError(f"unknown AGENT_MODE: {mode}")
