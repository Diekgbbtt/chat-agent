"""Endpoint health probes used at startup."""

import time
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Health:
    ok: bool
    latency_s: float
    error: str = ""


def probe(client, timeout_s: float = 5.0) -> Health:
    start = time.perf_counter()
    try:
        client.transport.models.list()
        return Health(True, time.perf_counter() - start)
    except Exception as exc:  # noqa: BLE001 - health is a status, not an exception path
        return Health(False, time.perf_counter() - start, str(exc) or exc.__class__.__name__)


def check(clients: Dict[str, object]) -> Dict[str, Health]:
    return {role: probe(client) for role, client in clients.items()}
