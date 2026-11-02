"""A thin OpenAI SDK client over one local chat-completions endpoint."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_TIMEOUT_S = 30.0


class LLMError(RuntimeError):
    """The endpoint failed or returned a shape the runtime cannot use."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    content: Optional[str]
    tool_calls: List[ToolCall]
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)


def _usage(raw) -> Dict[str, int]:
    if raw is None:
        return {}
    return {name: int(getattr(raw, name) or 0)
            for name in ("prompt_tokens", "completion_tokens", "total_tokens")}


def _tool_calls(message) -> List[ToolCall]:
    calls = []
    for call in getattr(message, "tool_calls", None) or []:
        function = getattr(call, "function", None)
        name = getattr(function, "name", "")
        raw = getattr(function, "arguments", "") or "{}"
        try:
            arguments = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise LLMError(f"invalid tool arguments for {name}: {exc}") from exc
        if not isinstance(arguments, dict):
            raise LLMError(f"tool arguments for {name} are not an object")
        calls.append(ToolCall(id=getattr(call, "id", ""), name=name, arguments=arguments))
    return calls


class LLMClient:
    """Calls one local endpoint with the OpenAI chat-completions shape."""

    def __init__(self, base_url: str, model: str, api_key: str = "local",
                 timeout_s: float = DEFAULT_TIMEOUT_S, transport=None):
        self.base_url = base_url
        self.model = model
        self.timeout_s = timeout_s
        self.transport = transport or self._build_transport(base_url, api_key, timeout_s)

    @staticmethod
    def _build_transport(base_url: str, api_key: str, timeout_s: float):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise LLMError("the openai package is required for model mode") from exc
        return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_s)

    def chat(self, messages, tools=None, tool_choice=None, max_tokens: Optional[int] = None,
             temperature: float = 0.0, parallel_tool_calls: bool = False) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "parallel_tool_calls": parallel_tool_calls,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        last_error = None
        for _ in range(2):
            try:
                raw = self.transport.chat.completions.create(**kwargs)
                choice = raw.choices[0]
                message = choice.message
                return LLMResponse(
                    content=getattr(message, "content", None),
                    tool_calls=_tool_calls(message),
                    finish_reason=getattr(choice, "finish_reason", None),
                    usage=_usage(getattr(raw, "usage", None)),
                )
            except LLMError:
                raise
            except Exception as exc:  # noqa: BLE001 - converted into a typed runtime error
                last_error = exc
        raise LLMError(f"model call failed: {last_error}") from last_error
