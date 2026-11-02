"""Runtime construction from settings, without opening a model connection."""

from types import SimpleNamespace

from agent.cli import build_runtime
from agent.llm.client import LLMClient
from agent.llm.factory import Clients, clients_from_settings


def settings(**overrides):
    values = dict(agent_mode="legacy", show_guardrail_labels=False,
                  guard_base_url="http://127.0.0.1:8001/v1", guard_model="guard",
                  guard_api_key="g", qa_base_url="http://127.0.0.1:8002/v1",
                  qa_model="qa", qa_api_key="q", model_timeout_s=9.0,
                  guard_schema_path="agent/data/guardrails.json",
                  max_agent_steps=4, agent_deadline_s=5.0, max_step_tokens=100)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_clients_from_settings_point_at_both_endpoints():
    clients = clients_from_settings(settings())

    assert isinstance(clients.guard, LLMClient)
    assert clients.guard.base_url.endswith(":8001/v1")
    assert clients.qa.base_url.endswith(":8002/v1")
    assert clients.guard.model == "guard"
    assert clients.qa.model == "qa"


class Fake:
    def chat(self, **kwargs):
        raise AssertionError("no model call during construction")


def test_build_runtime_selects_llm(movies_kg):
    agent = build_runtime(movies_kg, settings(agent_mode="llm"), Clients(Fake(), Fake()))

    assert [handler.name for handler in agent.handlers] == ["sparql", "llm"]


def test_build_runtime_rejects_an_unknown_mode(movies_kg):
    try:
        build_runtime(movies_kg, settings(agent_mode="nope"), Clients(Fake(), Fake()))
    except ValueError as exc:
        assert "AGENT_MODE" in str(exc)
    else:
        raise AssertionError("expected ValueError")
