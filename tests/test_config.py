import os

from agent.config import load_dotenv, parse_dotenv


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
