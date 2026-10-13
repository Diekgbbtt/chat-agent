"""Concurrency and robustness of the Speakeasy layer, using fake rooms and clients."""

import threading
import time

import pytest

from agent.speakeasy_bot import ERROR_REPLY, MAX_REPLY_CHARS, TIMEOUT_REPLY, SpeakeasyBot


class FakeRoom:
    def __init__(self, room_id, fail_posts=0):
        self.room_id = room_id
        self.posts = []
        self.fail_posts = fail_posts
        self.lock = threading.Lock()

    def post_messages(self, message):
        with self.lock:
            if self.fail_posts:
                self.fail_posts -= 1
                raise ConnectionError("post failed")
            self.posts.append((time.perf_counter(), message))


def wait_for(predicate, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def make_bot():
    bots = []

    def factory(answer_fn, **kwargs):
        kwargs.setdefault("workers", 4)
        bot = SpeakeasyBot(answer_fn, **kwargs)
        bots.append(bot)
        return bot

    yield factory
    for bot in bots:
        bot.shutdown()


def test_callback_returns_immediately(make_bot):
    bot = make_bot(lambda text, room: time.sleep(0.5) or "done")
    room = FakeRoom("r1")
    start = time.perf_counter()
    bot.on_message("hi", room)
    assert time.perf_counter() - start < 0.05
    assert wait_for(lambda: room.posts)
    assert room.posts[0][1] == "done"


def test_rooms_are_answered_in_parallel(make_bot):
    bot = make_bot(lambda text, room: time.sleep(0.4) or text)
    rooms = [FakeRoom(f"r{i}") for i in range(4)]
    start = time.perf_counter()
    for room in rooms:
        bot.on_message("hello", room)
    assert wait_for(lambda: all(r.posts for r in rooms))
    assert time.perf_counter() - start < 1.0  # sequential would take 1.6 s


def test_messages_in_one_room_stay_in_order(make_bot):
    delays = {"first": 0.3, "second": 0.0, "third": 0.1}
    bot = make_bot(lambda text, room: time.sleep(delays[text]) or text)
    room = FakeRoom("r1")
    for text in ("first", "second", "third"):
        bot.on_message(text, room)
    assert wait_for(lambda: len(room.posts) == 3)
    assert [m for _, m in room.posts] == ["first", "second", "third"]


def test_exception_gives_error_reply_and_bot_keeps_working(make_bot):
    def answer(text, room):
        if text == "boom":
            raise RuntimeError("bug")
        return "fine"

    bot = make_bot(answer)
    room = FakeRoom("r1")
    bot.on_message("boom", room)
    bot.on_message("ok", room)
    assert wait_for(lambda: len(room.posts) == 2)
    assert [m for _, m in room.posts] == [ERROR_REPLY, "fine"]
    assert bot.stats["errors"] == 1


def test_slow_answer_gets_timeout_reply(make_bot):
    bot = make_bot(lambda text, room: time.sleep(2) or "late", reply_timeout_s=0.2)
    room = FakeRoom("r1")
    bot.on_message("slow", room)
    assert wait_for(lambda: room.posts, timeout=1.0)
    assert room.posts[0][1] == TIMEOUT_REPLY


def test_empty_and_huge_replies(make_bot):
    replies = iter(["", "x" * (MAX_REPLY_CHARS + 100)])
    bot = make_bot(lambda text, room: next(replies))
    room = FakeRoom("r1")
    bot.on_message("a", room)
    bot.on_message("b", room)
    assert wait_for(lambda: len(room.posts) == 2)
    assert room.posts[0][1] == ERROR_REPLY
    assert len(room.posts[1][1]) == MAX_REPLY_CHARS


def test_failed_post_is_retried(make_bot):
    bot = make_bot(lambda text, room: "reply")
    room = FakeRoom("r1", fail_posts=1)
    bot.on_message("hi", room)
    assert wait_for(lambda: room.posts, timeout=3.0)
    assert room.posts[0][1] == "reply"


class FakeClient:
    def __init__(self, bot, behaviour):
        self.bot, self.behaviour = bot, behaviour

    def login(self):
        if self.behaviour == "login_fails":
            raise ConnectionError("login failed")

    def register_callback(self, callback, event_type):
        pass

    def start_listening(self):
        if self.behaviour == "stream_breaks":
            raise ConnectionError("stream broke")
        self.bot.stop()  # "stop" behaviour: end the run loop


def test_run_reconnects_after_failures():
    behaviours = iter(["login_fails", "stream_breaks", "stop"])
    created = []
    bot = SpeakeasyBot(lambda t, r: t, initial_backoff_s=0.01, heartbeat_s=60,
                       client_factory=lambda: created.append(1) or FakeClient(bot, next(behaviours)))
    thread = threading.Thread(target=bot.run, daemon=True)
    thread.start()
    thread.join(timeout=5)
    bot.shutdown()
    assert not thread.is_alive()
    assert len(created) == 3
