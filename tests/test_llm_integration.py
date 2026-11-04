"""The real OpenAI SDK over HTTP against an OpenAI-compatible tool-call server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent.llm.client import LLMClient, ToolCallProtocolError


class Handler(BaseHTTPRequestHandler):
    responses = []
    requests = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        type(self).requests.append(body)
        response = type(self).responses.pop(0)
        data = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    Handler.responses = []
    Handler.requests = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd, Handler
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def completion(message, finish_reason="tool_calls"):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1,
        "model": "test-model",
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }


def client(server):
    httpd, _ = server
    return LLMClient(base_url=f"http://127.0.0.1:{httpd.server_address[1]}/v1",
                     model="test-model", api_key="local", timeout_s=5)


def test_real_sdk_parses_native_tool_call(server):
    _, handler = server
    handler.responses.append(completion({
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call-1",
            "type": "function",
            "function": {"name": "submit_response", "arguments": '{"parts": []}'},
        }],
    }))

    response = client(server).chat(
        [{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "submit_response"}}],
        require_tool_call=True,
    )

    assert response.tool_calls[0].name == "submit_response"
    assert response.tool_calls[0].arguments == {"parts": []}
    assert response.finish_reason == "tool_calls"
    assert handler.requests[0]["tool_choice"] == "required"


def test_real_sdk_content_only_response_is_a_protocol_error(server):
    _, handler = server
    handler.responses.append(completion({
        "role": "assistant",
        "content": 'submit_response([{"parts": []}])',
    }, finish_reason="stop"))

    with pytest.raises(ToolCallProtocolError, match="native tool call"):
        client(server).chat(
            [{"role": "user", "content": "hi"}],
            tools=[{"type": "function", "function": {"name": "submit_response"}}],
            require_tool_call=True,
        )


def test_qa_loop_executes_native_tool_calls_end_to_end(server, movies_kg):
    from tests.guard_factory import SCHEMA, SpanSpec, verdict_and_decision

    from agent.lexicon import Lexicon
    from agent.qa.agent import ResponseAgent
    from agent.qa.prompts import PromptBuilder
    from agent.qa.schema_card import SchemaCard
    from agent.tools.discover import DiscoverTool
    from agent.tools.registry import ToolRegistry
    from agent.tools.resolve import ResolveEntityTool
    from agent.tools.sparql import RunSparqlTool

    _, handler = server
    handler.responses.extend([
        completion({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "run_sparql",
                    "arguments": json.dumps({"query": "SELECT ?d WHERE { wd:Q47703 wdt:P57 ?d }"}),
                },
            }],
        }),
        completion({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call-2",
                "type": "function",
                "function": {
                    "name": "submit_response",
                    "arguments": json.dumps({"parts": [{
                        "verbatim_index": 0,
                        "kind": "factual_answer",
                        "text": "The Godfather was directed by Francis Ford Coppola.",
                        "evidence_row_ids": ["r0"],
                        "addressed_safety_types": [],
                    }]}),
                },
            }],
        }),
    ])

    text = "Who directed The Godfather?"
    verdict, choice = verdict_and_decision(text, [SpanSpec(text)])
    lexicon = Lexicon(movies_kg)
    registry = ToolRegistry(ResolveEntityTool(movies_kg, lexicon),
                            DiscoverTool(movies_kg, lexicon),
                            RunSparqlTool(movies_kg, lexicon))
    card = SchemaCard.load("agent/data/movie_schema.json")
    agent = ResponseAgent(client(server), registry, PromptBuilder(card, SCHEMA), SCHEMA, max_steps=2)

    result = agent.respond(verdict, choice)

    assert result.text == "The Godfather was directed by Francis Ford Coppola."
    assert handler.requests[0]["tool_choice"] == "required"
    tool_messages = [message for message in handler.requests[1]["messages"]
                     if message["role"] == "tool"]
    assert "Francis Ford Coppola" in tool_messages[-1]["content"]
