"""
Runtime settings, read from environment variables with `.env` files as fallback.

The online evaluation starts `main.py` without our shell profile, so credentials
and paths can also live in a `.env` file (never committed, see .gitignore).
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# Directory that contains the `agent` package: the repo root during development,
# `additional_files/` inside a submission folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

NUVOLOS_GRAPH_PATH = "/space_mounts/atai-hs26/dataset/graph.nt"
DEFAULT_HOST = "https://speakeasy.ifi.uzh.ch"


def parse_dotenv(text: str) -> dict:
    """Parses KEY=VALUE lines; accepts `export`, comments and quoted values."""
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key] = value
    return values


def dotenv_candidates() -> list:
    # cwd, the project root, and the submission folder that holds additional_files/
    return [Path.cwd() / ".env", PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"]


def load_dotenv(paths: Optional[Iterable[Path]] = None) -> None:
    """Fills missing environment variables from .env files; real env vars win."""
    for path in paths if paths is not None else dotenv_candidates():
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
        for key, value in parse_dotenv(text).items():
            os.environ.setdefault(key, value)


def _default_graph_path() -> str:
    local = PROJECT_ROOT / "dataset" / "graph.nt"
    return str(local) if local.exists() else NUVOLOS_GRAPH_PATH


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    host: str
    username: Optional[str]
    password: Optional[str]
    graph_path: str
    store_path: str
    workers: int  # concurrent answer computations
    reply_timeout_s: float  # max time before the user gets a fallback reply
    query_timeout_s: float  # max time for a single SPARQL query
    max_fetch_rows: int  # rows materialised per query before truncating
    log_dir: str
    heartbeat_s: float


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        host=os.environ.get("SPEAKEASY_HOST", DEFAULT_HOST),
        username=os.environ.get("BOT_USERNAME"),
        password=os.environ.get("BOT_PASSWORD"),
        graph_path=os.environ.get("GRAPH_PATH") or _default_graph_path(),
        store_path=os.environ.get("KG_STORE_PATH") or str(PROJECT_ROOT / "kg_store"),
        workers=max(1, _int_env("AGENT_WORKERS", 8)),
        reply_timeout_s=_float_env("REPLY_TIMEOUT_S", 25.0),
        query_timeout_s=_float_env("QUERY_TIMEOUT_S", 20.0),
        max_fetch_rows=max(1, _int_env("MAX_FETCH_ROWS", 10_000)),
        log_dir=os.environ.get("LOG_DIR") or str(PROJECT_ROOT / "logs"),
        heartbeat_s=_float_env("HEARTBEAT_S", 300.0),
    )
