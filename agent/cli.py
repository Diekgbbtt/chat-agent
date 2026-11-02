"""
Talk to the agent without Speakeasy.

    python -m agent.cli "Who directed 'Inception'?"     one question
    python -m agent.cli --debug "..."                   also show how the answer was produced
    python -m agent.cli                                 interactive chat (:quit to leave)
"""

import argparse
import logging

from agent.config import load_settings
from agent.core import Agent, Trace, build_agent
from agent.kg import KnowledgeGraph


def load_agent(mode: str = "") -> Agent:
    settings = load_settings()
    if mode:
        from dataclasses import replace
        settings = replace(settings, agent_mode=mode)
    kg = KnowledgeGraph.open(settings.graph_path, settings.store_path, query_timeout_s=settings.query_timeout_s,
                             max_fetch_rows=settings.max_fetch_rows, workers=settings.workers)
    return build_runtime(kg, settings)


def build_runtime(kg, settings, clients=None) -> Agent:
    mode = settings.agent_mode
    if mode == "legacy":
        return build_agent(kg, load_llm(settings), settings.show_guardrail_labels)
    if mode not in ("guard_only", "tools"):
        raise ValueError(f"unknown AGENT_MODE: {mode}")

    from agent.config import PROJECT_ROOT
    from agent.guard.schema import load_schema
    from agent.llm.factory import clients_from_settings

    clients = clients or clients_from_settings(settings)
    schema = load_schema(settings.guard_schema_path)
    if mode == "guard_only":
        return build_agent(kg, mode="guard_only", guard_client=clients.guard,
                           guard_schema=schema, show_labels=settings.show_guardrail_labels)
    from agent.qa.schema_card import SchemaCard
    card = SchemaCard.load(PROJECT_ROOT / "agent" / "data" / "movie_schema.json")
    return build_agent(kg, mode="tools", guard_client=clients.guard, qa_client=clients.qa,
                       guard_schema=schema, schema_card=card,
                       show_labels=settings.show_guardrail_labels,
                       max_steps=settings.max_agent_steps,
                       deadline_s=settings.agent_deadline_s,
                       max_step_tokens=settings.max_step_tokens)


def load_llm(settings):
    if not settings.llm_model:
        return None
    from agent.llm.legacy import LLM  # imports torch, so only when an LLM is configured
    return LLM(settings.llm_model, four_bit=settings.llm_4bit)


def ask(agent: Agent, text: str, debug: bool) -> str:
    trace = Trace()
    reply = agent.answer(text, "cli", trace)
    if debug:
        for step, detail in trace.steps:
            print(f"  [{step}] {detail}")
    return reply


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", nargs="*")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.debug else logging.WARNING)

    agent = load_agent()
    if args.question:
        print(ask(agent, " ".join(args.question), args.debug))
        return
    while True:
        try:
            text = input("you> ")
        except (EOFError, KeyboardInterrupt):
            return
        if text.strip() == ":quit":
            return
        print("bot> " + ask(agent, text, args.debug))


if __name__ == "__main__":
    main()
