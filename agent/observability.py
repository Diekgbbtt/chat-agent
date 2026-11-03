"""Structured, request-scoped logging for the agent runtime.

Every answer writes one JSON object per line to ``LOG_DIR/agent.jsonl``.
The final ``trace`` record contains the full trajectory. Each LLM request and
response is a separate ``llm.request`` or ``llm.response`` record with the same
``request_id``. The format is stable enough to read with ``jq`` or Python.
"""

import contextvars
import json
import logging
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

REQUEST_ID = contextvars.ContextVar("agent_request_id", default="")
MAX_LOG_BYTES = 50_000_000
LOG_BACKUPS = 5


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str):
    return REQUEST_ID.set(request_id)


def reset_request_id(token) -> None:
    REQUEST_ID.reset(token)


def iso_time(epoch: float) -> str:
    value = datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="milliseconds")
    return value.replace("+00:00", "Z")


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses, sets, paths, and exceptions into JSON values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Exception):
        return {"type": type(value).__name__, "message": str(value)}
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [to_jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return str(value)


class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": iso_time(record.created),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": getattr(record, "request_id", "") or REQUEST_ID.get(),
            "thread": record.threadName,
        }
        fields = getattr(record, "fields", None)
        if fields:
            payload["fields"] = to_jsonable(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def emit(logger: logging.Logger, event: str, level: int = logging.INFO,
         exc_info: bool = False, **fields) -> None:
    """Emit one structured event. Fields stay nested under ``fields``."""
    logger.log(level, event, extra={"event": event, "fields": fields}, exc_info=exc_info)


def _agent_logger() -> logging.Logger:
    return logging.getLogger("agent")


def _log_path(settings) -> Path:
    configured = getattr(settings, "agent_log_file", "") or ""
    if configured:
        return Path(configured)
    return Path(getattr(settings, "log_dir", "logs")) / "agent.jsonl"


def _level(settings) -> int:
    name = str(getattr(settings, "agent_log_level", "INFO") or "INFO").upper()
    return getattr(logging, name, logging.INFO)


def configure_logging(settings, stream: bool = False) -> logging.Logger:
    """Attach the JSONL file handler once and set the requested level."""
    logger = _agent_logger()
    logger.setLevel(_level(settings))
    path = _log_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    same_file = [handler for handler in logger.handlers
                 if getattr(handler, "_agent_jsonl", False)
                 and getattr(handler, "baseFilename", "") == str(path)]
    if not same_file:
        for handler in list(logger.handlers):
            if getattr(handler, "_agent_jsonl", False):
                logger.removeHandler(handler)
                handler.close()
        handler = RotatingFileHandler(path, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUPS,
                                      encoding="utf-8")
        handler.setFormatter(JsonlFormatter())
        handler._agent_jsonl = True
        logger.addHandler(handler)
    if stream and not any(getattr(handler, "_agent_stream", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonlFormatter())
        handler._agent_stream = True
        logger.addHandler(handler)
    return logger


def reset_logging() -> None:
    """Remove handlers added by :func:`configure_logging`; used by tests."""
    logger = _agent_logger()
    for handler in list(logger.handlers):
        if getattr(handler, "_agent_jsonl", False) or getattr(handler, "_agent_stream", False):
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(logging.NOTSET)
