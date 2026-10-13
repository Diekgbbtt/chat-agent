"""
Speakeasy connection with concurrency and robustness.

speakeasypy delivers every event from a single SSE loop and calls our callback
inside it, so a slow answer would stall all chatrooms. Here the callback only
enqueues the message:

- dispatch pool: one task per message; holds the room's lock so replies within a
  room stay in order, while different rooms proceed in parallel
- compute pool: runs the actual answer with a deadline; on timeout or error the
  user gets a fallback reply instead of silence
- run(): logs in, listens, and reconnects with exponential backoff on any failure
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Callable, Dict, Optional

TIMEOUT_REPLY = ("Sorry, that is taking me longer than expected. "
                 "Could you try again, or ask a more specific question?")
ERROR_REPLY = "Sorry, something went wrong on my side. Could you try again?"
MAX_REPLY_CHARS = 4_000


def _default_client_factory(host: str, username: str, password: str, logger: logging.Logger):
    from speakeasypy import Speakeasy

    return Speakeasy(host=host, username=username, password=password, logger=logger)


class SpeakeasyBot:
    def __init__(
        self,
        answer_fn: Callable[[str, str], str],
        *,
        username: str = "",
        password: str = "",
        host: str = "https://speakeasy.ifi.uzh.ch",
        workers: int = 8,
        reply_timeout_s: float = 25.0,
        heartbeat_s: float = 300.0,
        initial_backoff_s: float = 1.0,
        max_backoff_s: float = 60.0,
        logger: Optional[logging.Logger] = None,
        client_factory: Optional[Callable[[], object]] = None,
    ):
        self.answer_fn = answer_fn
        self.reply_timeout_s = reply_timeout_s
        self.heartbeat_s = heartbeat_s
        self.initial_backoff_s = initial_backoff_s
        self.max_backoff_s = max_backoff_s
        self.log = logger or logging.getLogger("agent.bot")
        self._client_factory = client_factory or (
            lambda: _default_client_factory(host, username, password, self.log))

        # Dispatch threads mostly wait (on room locks and compute futures), so more of them.
        self._dispatch = ThreadPoolExecutor(max_workers=workers * 4, thread_name_prefix="dispatch")
        self._compute = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="compute")
        self._room_locks: Dict[str, threading.Lock] = {}
        self._room_locks_guard = threading.Lock()
        self._stop = threading.Event()
        self._stats_lock = threading.Lock()
        self.stats = {"received": 0, "answered": 0, "timeouts": 0, "errors": 0, "post_failures": 0}

    # --- message handling ---------------------------------------------------

    def on_message(self, message: str, room) -> None:
        """speakeasypy callback; must return quickly."""
        self._count("received")
        self.log.info("Room [%s] received: %r", room.room_id, (message or "")[:300])
        self._dispatch.submit(self._handle, message, room)

    def _room_lock(self, room_id: str) -> threading.Lock:
        with self._room_locks_guard:
            lock = self._room_locks.get(room_id)
            if lock is None:
                lock = self._room_locks[room_id] = threading.Lock()
            return lock

    def _handle(self, message: str, room) -> None:
        try:
            with self._room_lock(room.room_id):
                started = time.perf_counter()
                reply = self._compute_reply(message, room.room_id)
                self._post(room, reply)
                self.log.info("Room [%s] replied in %.2f s: %r",
                              room.room_id, time.perf_counter() - started, reply[:300])
        except Exception:  # never let a worker die silently
            self.log.exception("Room [%s] unexpected failure while handling a message", room.room_id)

    def _compute_reply(self, message: str, room_id: str) -> str:
        future = self._compute.submit(self.answer_fn, message, room_id)
        try:
            reply = future.result(timeout=self.reply_timeout_s)
        except FuturesTimeout:
            # The computation keeps running in the background; Python can't cancel it.
            self._count("timeouts")
            self.log.warning("Room [%s] answer exceeded %.0f s", room_id, self.reply_timeout_s)
            return TIMEOUT_REPLY
        except Exception:
            self._count("errors")
            self.log.exception("Room [%s] answer failed", room_id)
            return ERROR_REPLY
        self._count("answered")
        reply = (reply or "").strip() or ERROR_REPLY
        return reply if len(reply) <= MAX_REPLY_CHARS else reply[: MAX_REPLY_CHARS - 3] + "..."

    def _post(self, room, reply: str) -> None:
        for attempt in (1, 2):
            try:
                room.post_messages(reply)
                return
            except Exception:
                self.log.exception("Room [%s] posting failed (attempt %d)", room.room_id, attempt)
                if attempt == 1:
                    time.sleep(1.0)
        self._count("post_failures")

    def _count(self, key: str) -> None:
        with self._stats_lock:
            self.stats[key] += 1

    # --- connection lifecycle ----------------------------------------------

    def run(self) -> None:
        """Connects and listens forever, reconnecting with backoff on failures."""
        heartbeat = threading.Thread(target=self._heartbeat, name="heartbeat", daemon=True)
        heartbeat.start()
        backoff = self.initial_backoff_s
        while not self._stop.is_set():
            connected_at = None
            try:
                client = self._client_factory()
                client.login()
                client.register_callback(self.on_message, _message_event_type())
                connected_at = time.time()
                self.log.info("Logged in, listening for messages")
                client.start_listening()  # blocks until the stream ends or fails
                self.log.warning("Event stream ended")
            except KeyboardInterrupt:
                raise
            except Exception:
                self.log.exception("Connection failed")
            if self._stop.is_set():
                break
            # A connection that held for a while resets the backoff.
            if connected_at is not None and time.time() - connected_at > 60:
                backoff = self.initial_backoff_s
            self.log.info("Reconnecting in %.0f s", backoff)
            self._stop.wait(backoff)
            backoff = min(backoff * 2, self.max_backoff_s)

    def _heartbeat(self) -> None:
        while not self._stop.wait(self.heartbeat_s):
            with self._stats_lock:
                stats = dict(self.stats)
            self.log.info("Heartbeat: alive, rooms=%d, %s", len(self._room_locks), stats)

    def stop(self) -> None:
        self._stop.set()

    def shutdown(self) -> None:
        self.stop()
        self._dispatch.shutdown(wait=False, cancel_futures=True)
        self._compute.shutdown(wait=False, cancel_futures=True)


def _message_event_type():
    from speakeasypy import EventType

    return EventType.MESSAGE
