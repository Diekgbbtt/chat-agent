"""A thin OpenAI SDK client over one local chat-completions endpoint."""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.observability import emit

DEFAULT_TIMEOUT_S = 30.0
log = logging.getLogger("agent.llm.client")


class LLMError(RuntimeError):
    """The endpoint failed or returned a shape the runtime cannot use."""


class ToolCallProtocolError(LLMError):
    """The response did not follow the native tool-call contract."""


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
    reasoning: Optional[str] = None


def _field(value, name: str, default=None):
    """Read a field from an SDK object or a plain mapping."""
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _usage(raw) -> Dict[str, int]:
    if raw is None:
        return {}
    return {name: int(_field(raw, name) or 0)
            for name in ("prompt_tokens", "completion_tokens", "total_tokens")}


def _reasoning(message) -> Optional[str]:
    for name in ("reasoning_content", "reasoning"):
        value = _field(message, name)
        if value:
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    extra = _field(message, "model_extra")
    if isinstance(extra, dict):
        for name in ("reasoning_content", "reasoning"):
            value = extra.get(name)
            if value:
                return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return None


def _arguments(raw, name: str) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    if raw in (None, ""):
        return {}
    try:
        arguments = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise LLMError(f"invalid tool arguments for {name}: {exc}") from exc
    if not isinstance(arguments, dict):
        raise LLMError(f"tool arguments for {name} are not an object")
    return arguments


def _tool_calls(message) -> List[ToolCall]:
    calls = []
    for call in _field(message, "tool_calls", None) or []:
        function = _field(call, "function")
        name = _field(function, "name", "")
        calls.append(ToolCall(id=_field(call, "id", ""), name=name,
                              arguments=_arguments(_field(function, "arguments", ""), name)))
    return calls


def _tool_names(tools) -> list:
    names = []
    for tool in tools or []:
        function = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = function.get("name")
        if name:
            names.append(name)
    return names


class LLMClient:
    """Calls one local endpoint with the OpenAI chat-completions shape."""

    def __init__(self, base_url: str, model: str, api_key: str = "local",
                 timeout_s: float = DEFAULT_TIMEOUT_S, transport=None, log_payloads: bool = True):
        self.base_url = base_url
        self.model = model
        self.timeout_s = timeout_s
        self.log_payloads = log_payloads
        self.transport = transport or self._build_transport(base_url, api_key, timeout_s)

    @staticmethod
    def _build_transport(base_url: str, api_key: str, timeout_s: float):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise LLMError("the openai package is required for model mode") from exc
        return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_s)

    def _request_detail(self, messages, tools, tool_choice, max_tokens, temperature) -> dict:
        base = {"model": self.model, "base_url": self.base_url}
        if self.log_payloads:
            return {**base, "messages": messages, "tools": tools, "tool_choice": tool_choice,
                    "max_tokens": max_tokens, "temperature": temperature}
        return {**base, "message_count": len(messages), "tool_names": _tool_names(tools),
                "tool_choice": tool_choice, "max_tokens": max_tokens, "temperature": temperature}

    def _response_detail(self, response: LLMResponse, latency_ms: float) -> dict:
        base = {"latency_ms": latency_ms, "finish_reason": response.finish_reason,
                "usage": response.usage}
        if self.log_payloads:
            return {**base, "content": response.content, "reasoning": response.reasoning,
                    "tool_calls": response.tool_calls}
        return {**base, "content_chars": len(response.content or ""),
                "reasoning_chars": len(response.reasoning or ""),
                "tool_calls": [{"name": call.name, "arguments": call.arguments}
                               for call in response.tool_calls]}

    def chat(self, messages, tools=None, tool_choice=None, max_tokens: Optional[int] = None,
             temperature: float = 0.0, parallel_tool_calls: bool = False,
             require_tool_call: bool = False) -> LLMResponse:
        if require_tool_call and not tools:
            raise LLMError("require_tool_call needs at least one tool")
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "parallel_tool_calls": parallel_tool_calls,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if require_tool_call and tool_choice in (None, "auto"):
            kwargs["tool_choice"] = "required"
        elif tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        last_error = None
        for attempt in (1, 2):
            started = time.perf_counter()
            emit(log, "llm.request", attempt=attempt,
                 **self._request_detail(messages, tools, kwargs.get("tool_choice"),
                                        max_tokens, temperature))
            try:
                raw = self.transport.chat.completions.create(**kwargs)
                choices = _field(raw, "choices", None) or []
                if not choices:
                    raise LLMError("model response has no choices")
                choice = choices[0]
                message = _field(choice, "message")
                if message is None:
                    raise LLMError("model response has no message")
                response = LLMResponse(
                    content=_field(message, "content"),
                    tool_calls=_tool_calls(message),
                    finish_reason=_field(choice, "finish_reason"),
                    usage=_usage(_field(raw, "usage")),
                    reasoning=_reasoning(message),
                )
                emit(log, "llm.response", attempt=attempt,
                     **self._response_detail(response, round((time.perf_counter() - started) * 1000.0, 1)))
                if require_tool_call and not response.tool_calls:
                    raise ToolCallProtocolError("the model returned no native tool call")
                return response
            except LLMError as exc:
                emit(log, "llm.error", level=logging.ERROR, attempt=attempt,
                     latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
                     error=f"{type(exc).__name__}: {exc}")
                raise
            except Exception as exc:  # noqa: BLE001 - converted into a typed runtime error
                last_error = exc
                emit(log, "llm.error", level=logging.WARNING, attempt=attempt,
                     latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
                     error=f"{type(exc).__name__}: {exc}", retrying=attempt == 1)
        raise LLMError(f"model call failed: {last_error}") from last_error
