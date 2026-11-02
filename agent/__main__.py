"""Starts the Speakeasy bot: `python -m agent` (or a submission's main.py)."""

import sys

from agent.config import load_settings
from agent.cli import build_runtime
from agent.kg import KnowledgeGraph
from agent.speakeasy_bot import SpeakeasyBot


def setup_logging(log_dir: str):
    from speakeasypy import get_logger

    # Child loggers (agent.kg, agent.bot, ...) propagate into this one.
    return get_logger("agent", log_dir=log_dir)


def main() -> None:
    settings = load_settings() #Loads settings from .env file and other variables.
    logger = setup_logging(settings.log_dir) #Sets up logging for the agent.
    if not settings.username or not settings.password:
        logger.error("BOT_USERNAME and BOT_PASSWORD must be set (environment or .env file)")
        sys.exit(2)

    kg = KnowledgeGraph.open(  #Builds kg_store or loads it from disk if it already exists.
        settings.graph_path,
        settings.store_path,
        query_timeout_s=settings.query_timeout_s,
        max_fetch_rows=settings.max_fetch_rows,
        workers=settings.workers,
    )
    agent = None
    if settings.agent_mode == "legacy":
        agent = build_runtime(kg, settings)
    else:
        if settings.autostart_models:
            from agent.serve import start
            if start(settings):
                kg.close()
                sys.exit(2)
        from agent.llm.factory import clients_from_settings
        from agent.llm.health import check
        clients = clients_from_settings(settings)
        status = check({"guard": clients.guard, "qa": clients.qa})
        if not all(item.ok for item in status.values()):
            details = {role: item.error for role, item in status.items() if not item.ok}
            logger.error("Model endpoints are unhealthy: %s", details)
            kg.close()
            sys.exit(2)
        agent = build_runtime(kg, settings, clients)
    bot = SpeakeasyBot(
        agent.answer,
        username=settings.username,
        password=settings.password,
        host=settings.host,
        workers=settings.workers,
        reply_timeout_s=settings.reply_timeout_s,
        heartbeat_s=settings.heartbeat_s,
        logger=logger.getChild("bot"),
    )
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        bot.shutdown()
        kg.close()


if __name__ == "__main__":
    main()
