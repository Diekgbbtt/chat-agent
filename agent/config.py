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
DEFAULT_LOCAL_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_LOCAL_MODEL = "Qwen/Qwen3-4B-Instruct-2507"


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


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


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
    llm_model: str  # Hugging Face model id
    llm_4bit: bool  # 4-bit loading for small GPUs (local 6 GB card); off on Nuvolos (fp16)
    show_guardrail_labels: bool  # prefix replies with "[label]"; off = labels only in the log
    agent_mode: str = "legacy"  # legacy | llm
    local_base_url: str = DEFAULT_LOCAL_BASE_URL
    local_model: str = DEFAULT_LOCAL_MODEL
    guard_base_url: str = DEFAULT_LOCAL_BASE_URL
    guard_model: str = DEFAULT_LOCAL_MODEL
    guard_api_key: str = "local"
    qa_base_url: str = DEFAULT_LOCAL_BASE_URL
    qa_model: str = DEFAULT_LOCAL_MODEL
    qa_api_key: str = "local"
    guard_schema_path: str = str(PROJECT_ROOT / "agent" / "data" / "guardrails.json")
    model_timeout_s: float = 30.0
    agent_deadline_s: float = 20.0
    max_agent_steps: int = 6
    max_submit_repairs: int = 3
    max_tool_rows: int = 50
    max_observation_chars: int = 1_200
    max_step_tokens: int = 300
    max_prompt_tokens: int = 2_200
    history_enabled: bool = False
    max_answer_chars: int = 400
    max_refusal_chars: int = 300
    max_boundary_chars: int = 160
    max_clarification_chars: int = 300
    max_capability_chars: int = 300
    max_general_chars: int = 400
    autostart_models: bool = False
    resolve_fuzzy: bool = False
    agent_log_level: str = "INFO"
    agent_log_payloads: bool = True
    agent_log_file: str = ""


def load_settings() -> Settings:
    load_dotenv()
    local_model = os.environ.get("LOCAL_MODEL") or DEFAULT_LOCAL_MODEL
    local_base_url = os.environ.get("LOCAL_BASE_URL") or DEFAULT_LOCAL_BASE_URL
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
        # Empty by default: the in-process model is opt-in (requirements-legacy.txt).
        llm_model=os.environ.get("LLM_MODEL") or "",
        llm_4bit=_bool_env("LLM_4BIT", False),
        show_guardrail_labels=_bool_env("SHOW_GUARDRAIL_LABELS", False),
        agent_mode=os.environ.get("AGENT_MODE", "legacy"),
        local_base_url=local_base_url,
        local_model=local_model,
        guard_base_url=os.environ.get("GUARD_BASE_URL") or local_base_url,
        guard_model=os.environ.get("GUARD_MODEL") or local_model,
        guard_api_key=os.environ.get("GUARD_API_KEY") or "local",
        qa_base_url=os.environ.get("QA_BASE_URL") or local_base_url,
        qa_model=os.environ.get("QA_MODEL") or local_model,
        qa_api_key=os.environ.get("QA_API_KEY") or "local",
        guard_schema_path=os.environ.get("GUARD_SCHEMA_PATH")
        or str(PROJECT_ROOT / "agent" / "data" / "guardrails.json"),
        model_timeout_s=_float_env("MODEL_TIMEOUT_S", 30.0),
        agent_deadline_s=_float_env("AGENT_DEADLINE_S", 20.0),
        max_agent_steps=max(1, _int_env("MAX_AGENT_STEPS", 6)),
        max_submit_repairs=max(1, _int_env("MAX_SUBMIT_REPAIRS", 3)),
        max_tool_rows=max(1, _int_env("MAX_TOOL_ROWS", 50)),
        max_observation_chars=max(1, _int_env("MAX_OBSERVATION_CHARS", 1_200)),
        max_step_tokens=max(1, _int_env("MAX_STEP_TOKENS", 300)),
        max_prompt_tokens=max(1, _int_env("MAX_PROMPT_TOKENS", 2_200)),
        history_enabled=_bool_env("HISTORY_ENABLED", False),
        max_answer_chars=max(1, _int_env("MAX_ANSWER_CHARS", 400)),
        max_refusal_chars=max(1, _int_env("MAX_REFUSAL_CHARS", 300)),
        max_boundary_chars=max(1, _int_env("MAX_BOUNDARY_CHARS", 160)),
        max_clarification_chars=max(1, _int_env("MAX_CLARIFICATION_CHARS", 300)),
        max_capability_chars=max(1, _int_env("MAX_CAPABILITY_CHARS", 300)),
        max_general_chars=max(1, _int_env("MAX_GENERAL_CHARS", 400)),
        autostart_models=_bool_env("AUTOSTART_MODELS", False),
        resolve_fuzzy=_bool_env("RESOLVE_FUZZY", False),
        agent_log_level=(os.environ.get("AGENT_LOG_LEVEL") or "INFO").upper(),
        agent_log_payloads=_bool_env("AGENT_LOG_PAYLOADS", True),
        agent_log_file=os.environ.get("AGENT_LOG_FILE") or "",
    )
