"""The local model launcher prints and checks the shared endpoint."""

from types import SimpleNamespace

from agent import serve


def settings(**overrides):
    base_url = "http://127.0.0.1:8000/v1"
    values = dict(local_model="local/model", local_base_url=base_url,
                  guard_base_url=base_url, qa_base_url=base_url,
                  guard_api_key="local", qa_api_key="local", model_timeout_s=5.0)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_commands_start_one_server_for_the_configured_model():
    commands = serve.commands(settings())

    assert len(commands) == 1
    assert commands[0][:2] == ["vllm", "serve"]
    assert commands[0][2] == "local/model"
    assert commands[0][commands[0].index("--port") + 1] == "8000"
    assert commands[0][commands[0].index("--gpu-memory-utilization") + 1] == "0.85"
    assert commands[0][commands[0].index("--max-num-seqs") + 1] == "8"
    assert "--quantization" not in commands[0]
    assert "--enable-auto-tool-choice" in commands[0]
    assert commands[0][commands[0].index("--tool-call-parser") + 1] == "hermes"


def test_check_probes_the_shared_endpoint_once(monkeypatch):
    seen = []

    def fake_healthy(url, timeout):
        seen.append(url)
        return True

    monkeypatch.setattr(serve, "_healthy", fake_healthy)

    status = serve.check(settings())

    assert status == {"guard": True, "qa": True}
    assert seen == ["http://127.0.0.1:8000/v1"]


def test_check_probes_each_role_override(monkeypatch):
    seen = []

    def fake_healthy(url, timeout):
        seen.append(url)
        return "8002" in url

    monkeypatch.setattr(serve, "_healthy", fake_healthy)

    status = serve.check(settings(guard_base_url="http://127.0.0.1:8001/v1",
                                  qa_base_url="http://127.0.0.1:8002/v1"))

    assert status == {"guard": False, "qa": True}
    assert seen == ["http://127.0.0.1:8001/v1", "http://127.0.0.1:8002/v1"]


def test_check_uses_the_requested_timeout(monkeypatch):
    seen = []

    def fake_healthy(url, timeout):
        seen.append(timeout)
        return True

    monkeypatch.setattr(serve, "_healthy", fake_healthy)

    serve.check(settings(), timeout_s=7.5)

    assert seen == [7.5]
