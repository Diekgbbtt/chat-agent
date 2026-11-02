"""Typed parts and the validated agent result."""

from dataclasses import dataclass
from typing import Tuple

PART_KINDS = ("factual_answer", "general_answer", "capability_limit",
              "refusal", "clarification", "boundary")


@dataclass(frozen=True)
class Part:
    verbatim_index: int
    kind: str
    text: str
    evidence_row_ids: Tuple[str, ...] = ()
    addressed_safety_types: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentResult:
    parts: Tuple[Part, ...]
    text: str
    evidence: Tuple[str, ...] = ()
    fallback_reason: str = ""
