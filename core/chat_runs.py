from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable

logger = logging.getLogger(__name__)


class ChatRun:
    def __init__(self, session_id: str, source: Callable[[], AsyncIterator[str]]):
        self.run_id = uuid.uuid4().hex
        self.session_id = session_id
        self.created_at = time.time()
        self.completed_at: float | None = None
        self.events: list[str] = []
        self.subscribers: set[asyncio.Queue[str | None]] = set()
        self._source = source
        self._task = asyncio.create_task(self._consume())

    @property
    def done(self) -> bool:
        return self._task.done()

    def cancel(self) -> None:
        if not self._task.done():
            self._task.cancel()

    async def _consume(self) -> None:
        try:
            async for event in self._source():
                self.events.append(event)
                for queue in list(self.subscribers):
                    await queue.put(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Chat run failed for session %s", self.session_id)
            event = f'data: {{"type":"error","content":"后台任务异常：{str(exc)}"}}\n\n'
            self.events.append(event)
            for queue in list(self.subscribers):
                await queue.put(event)
        finally:
            self.completed_at = time.time()
            for queue in list(self.subscribers):
                await queue.put(None)

    async def subscribe(self, from_index: int = 0) -> AsyncIterator[str]:
        for event in self.events[max(0, from_index):]:
            yield event
        if self.done:
            return

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self.subscribers.discard(queue)


_active_runs: dict[str, ChatRun] = {}
_stop_requested_sessions: set[str] = set()


def start_chat_run(session_id: str, source: Callable[[], AsyncIterator[str]]) -> ChatRun:
    run = _active_runs.get(session_id)
    if run and not run.done and session_id not in _stop_requested_sessions:
        return run
    if run and not run.done:
        run.cancel()
    _stop_requested_sessions.discard(session_id)
    run = ChatRun(session_id, source)
    _active_runs[session_id] = run
    return run


def is_chat_running(session_id: str) -> bool:
    if session_id in _stop_requested_sessions:
        return False
    run = _active_runs.get(session_id)
    return bool(run and not run.done)


def get_chat_run(session_id: str) -> ChatRun | None:
    return _active_runs.get(session_id)


def cancel_chat_run(session_id: str) -> bool:
    _stop_requested_sessions.add(session_id)
    run = _active_runs.get(session_id)
    if run and not run.done:
        run.cancel()
        return True
    return False
