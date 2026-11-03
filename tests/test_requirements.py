"""Dependency files keep serving, legacy, and agent stacks separate."""

import re
from pathlib import Path

CORE = Path("requirements.txt")
LOCAL = Path("requirements-local.txt")
SERVE = Path("requirements-serve.txt")
LEGACY = Path("requirements-legacy.txt")

HEAVY = {"torch", "transformers", "accelerate", "bitsandbytes", "vllm"}


def names(path: Path) -> set:
    result = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        result.add(re.split(r"[\s<>=!~;\[]", line, maxsplit=1)[0].lower())
    return result


def test_agent_runtime_has_no_model_stack():
    assert not (names(CORE) & HEAVY)


def test_local_development_has_no_model_stack():
    assert not (names(LOCAL) & HEAVY)


def test_serving_needs_only_vllm():
    assert names(SERVE) == {"vllm"}


def test_legacy_is_the_only_place_with_the_in_process_stack():
    assert {"torch", "transformers", "accelerate", "bitsandbytes"} <= names(LEGACY)


def test_legacy_and_local_include_the_agent_runtime():
    assert "-r requirements.txt" in LEGACY.read_text(encoding="utf-8")
    assert "-r requirements.txt" in LOCAL.read_text(encoding="utf-8")
