"""The deterministic composer assigns distinct observations to answer parts."""

from tests.guard_factory import SCHEMA, SpanSpec, verdict_and_decision

from agent.qa.composer import Composer
from agent.qa.renderer import RowRenderer
from agent.qa.state import AgentState
from agent.tools.registry import ExecutedTool
from agent.tools.sparql import Observation


def _executed(rows):
    return ExecutedTool("run_sparql", {"query": "SELECT"}, Observation(tuple(rows)))


def test_each_answer_part_receives_its_own_observation():
    text = "Who directed Inception? Who starred in Inception?"
    verdict, decision = verdict_and_decision(text, [
        SpanSpec("Who directed Inception?"),
        SpanSpec("Who starred in Inception?"),
    ])
    state = AgentState(verdict, decision, observations=[
        _executed([{"row_id": "r0", "director": "Christopher Nolan"}]),
        _executed([{"row_id": "r1", "actor": "Leonardo DiCaprio"}]),
    ])

    result = Composer(RowRenderer(SCHEMA), SCHEMA).compose(decision, state, "step budget")

    assert "Christopher Nolan" in result.parts[0].text
    assert "Leonardo DiCaprio" in result.parts[1].text
    assert result.parts[0].evidence_row_ids == ("r0",)
    assert result.parts[1].evidence_row_ids == ("r1",)


def test_one_observation_is_reused_when_it_is_the_only_source():
    text = "Who directed Inception? Who starred in Inception?"
    verdict, decision = verdict_and_decision(text, [
        SpanSpec("Who directed Inception?"),
        SpanSpec("Who starred in Inception?"),
    ])
    state = AgentState(verdict, decision, observations=[
        _executed([{"row_id": "r0", "answer": "Christopher Nolan"}]),
    ])

    result = Composer(RowRenderer(SCHEMA), SCHEMA).compose(decision, state, "step budget")

    assert all("Christopher Nolan" in part.text for part in result.parts)


def test_negated_answer_does_not_render_the_positive_observation():
    text = "Who did not direct Jaws?"
    verdict, decision = verdict_and_decision(text, [SpanSpec(text)])
    state = AgentState(verdict, decision, observations=[
        _executed([{"row_id": "r0", "director": "Steven Spielberg"}]),
    ])

    result = Composer(RowRenderer(SCHEMA), SCHEMA).compose(decision, state, "protocol error")

    assert "Steven Spielberg" not in result.text
    assert result.parts[0].kind == "general_answer"
    assert result.parts[0].evidence_row_ids == ()
