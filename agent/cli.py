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


def load_agent() -> Agent:
    settings = load_settings()
    kg = KnowledgeGraph.open(settings.graph_path, settings.store_path, query_timeout_s=settings.query_timeout_s,
                             max_fetch_rows=settings.max_fetch_rows, workers=settings.workers)
    return build_agent(kg)


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
