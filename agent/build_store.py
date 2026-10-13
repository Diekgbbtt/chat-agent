"""
One-time conversion of graph.nt into the on-disk pyoxigraph store.

    python -m agent.build_store            uses GRAPH_PATH / KG_STORE_PATH settings
    python -m agent.build_store --force    rebuild even if a store exists

The bot and CLI also build the store automatically on first start if it is missing.
"""

import argparse
import logging

from agent.config import load_settings
from agent.kg import build_store


def main(argv=None) -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--graph", default=settings.graph_path)
    parser.add_argument("--store", default=settings.store_path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    build_store(args.graph, args.store, force=args.force)


if __name__ == "__main__":
    main()
