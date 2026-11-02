import os

from agent.config import load_dotenv, load_settings, parse_dotenv


def test_parse_dotenv():
    text = """
# comment
export BOT_USERNAME='my_group'
BOT_PASSWORD="p@ss word!"
GRAPH_PATH=/data/graph.nt
not a pair
"""
    assert parse_dotenv(text) == {
        "BOT_USERNAME": "my_group",
        "BOT_PASSWORD": "p@ss word!",
        "GRAPH_PATH": "/data/graph.nt",
    }


def test_real_environment_wins(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("ATAI_TEST_A=from_file\nATAI_TEST_B=from_file\n")
    monkeypatch.setenv("ATAI_TEST_A", "from_env")
    monkeypatch.delenv("ATAI_TEST_B", raising=False)
    load_dotenv([env, tmp_path / "missing.env"])
    assert os.environ["ATAI_TEST_A"] == "from_env"
    assert os.environ["ATAI_TEST_B"] == "from_file"
    monkeypatch.delenv("ATAI_TEST_B")


def test_agent_defaults_keep_the_legacy_path(monkeypatch):
    for name in ("AGENT_MODE", "LOCAL_BASE_URL", "LOCAL_MODEL", "GUARD_BASE_URL",
                 "GUARD_MODEL", "QA_BASE_URL", "QA_MODEL"):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.agent_mode == "legacy"
    assert settings.local_base_url.endswith(":8000/v1")
    assert settings.guard_base_url == settings.local_base_url
    assert settings.qa_base_url == settings.local_base_url
    assert settings.guard_model == settings.local_model
    assert settings.qa_model == settings.local_model
    assert settings.local_model
    assert settings.max_agent_steps >= 1
    assert settings.history_enabled is False


def test_local_model_and_endpoint_supply_both_role_defaults(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL", "local/model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://127.0.0.1:9000/v1")
    for name in ("GUARD_BASE_URL", "GUARD_MODEL", "QA_BASE_URL", "QA_MODEL", "AGENT_MODE"):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.guard_model == "local/model"
    assert settings.qa_model == "local/model"
    assert settings.guard_base_url == "http://127.0.0.1:9000/v1"
    assert settings.qa_base_url == "http://127.0.0.1:9000/v1"


def test_role_overrides_still_win(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL", "local/model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://127.0.0.1:9000/v1")
    monkeypatch.setenv("GUARD_MODEL", "guard/model")
    monkeypatch.setenv("QA_MODEL", "qa/model")
    monkeypatch.setenv("GUARD_BASE_URL", "http://127.0.0.1:9001/v1")
    monkeypatch.setenv("QA_BASE_URL", "http://127.0.0.1:9002/v1")

    settings = load_settings()

    assert settings.guard_model == "guard/model"
    assert settings.qa_model == "qa/model"
    assert settings.guard_base_url == "http://127.0.0.1:9001/v1"
    assert settings.qa_base_url == "http://127.0.0.1:9002/v1"


def test_agent_mode_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "llm")
    monkeypatch.setenv("MAX_AGENT_STEPS", "9")
    monkeypatch.setenv("HISTORY_ENABLED", "1")

    settings = load_settings()

    assert settings.agent_mode == "llm"
    assert settings.max_agent_steps == 9
    assert settings.history_enabled is True
