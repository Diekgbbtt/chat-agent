import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.core import build_agent  # noqa: E402
from agent.kg import KnowledgeGraph  # noqa: E402

MINI_GRAPH = ROOT / "tests" / "fixtures" / "mini.nt"
MOVIES_GRAPH = ROOT / "tests" / "fixtures" / "movies.nt"


@pytest.fixture
def kg(tmp_path):
    graph = KnowledgeGraph.open(MINI_GRAPH, tmp_path / "store", query_timeout_s=5)
    yield graph
    graph.close()


@pytest.fixture(scope="module")
def movies_kg(tmp_path_factory):
    graph = KnowledgeGraph.open(MOVIES_GRAPH, tmp_path_factory.mktemp("movies") / "store", query_timeout_s=5)
    yield graph
    graph.close()


@pytest.fixture(scope="module")
def factual_agent(movies_kg):
    return build_agent(movies_kg)
