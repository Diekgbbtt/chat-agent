"""Build the guard and QA clients from local settings."""

from dataclasses import dataclass

from agent.llm.client import LLMClient


@dataclass(frozen=True)
class Clients:
    guard: object
    qa: object


def clients_from_settings(settings) -> Clients:
    payloads = getattr(settings, "agent_log_payloads", True)
    return Clients(
        guard=LLMClient(settings.guard_base_url, settings.guard_model,
                        api_key=settings.guard_api_key, timeout_s=settings.model_timeout_s,
                        log_payloads=payloads),
        qa=LLMClient(settings.qa_base_url, settings.qa_model,
                     api_key=settings.qa_api_key, timeout_s=settings.model_timeout_s,
                     log_payloads=payloads),
    )
