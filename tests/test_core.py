from agent.core import EMPTY_REPLY, MAX_INPUT_CHARS, Agent, Trace


class Echo:
    name = "echo"

    def can_handle(self, text, session):
        return True

    def handle(self, text, session, trace):
        session.state["count"] = session.state.get("count", 0) + 1
        return f"{text}#{session.state['count']}"


def test_empty_message():
    assert Agent([Echo()]).answer("   ") == EMPTY_REPLY
    assert Agent([Echo()]).answer(None) == EMPTY_REPLY


def test_sessions_are_separate():
    agent = Agent([Echo()])
    assert agent.answer("a", "room-1") == "a#1"
    assert agent.answer("b", "room-1") == "b#2"
    assert agent.answer("c", "room-2") == "c#1"
    agent.reset_session("room-1")
    assert agent.answer("d", "room-1") == "d#1"


def test_input_is_trimmed_and_capped():
    reply = Agent([Echo()]).answer("  " + "x" * (MAX_INPUT_CHARS * 2))
    assert reply == "x" * MAX_INPUT_CHARS + "#1"


def test_trace_names_the_handler():
    trace = Trace()
    Agent([Echo()]).answer("hi", trace=trace)
    assert ("handler", "echo") in trace.steps
