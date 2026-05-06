import unittest
from unittest.mock import patch

from core.chat_session_service import (
    ChatSessionServiceError,
    STOP_AUDIT_MEMORY_TYPE,
    request_session_stop,
    start_session_chat_run,
)


async def fake_stream():
    yield "data: {}\n\n"


class FakeMemoryDB:
    def __init__(self):
        self.messages = []

    def append_message(self, session_id, message):
        self.messages.append((session_id, message))
        return len(self.messages)


class TestChatSessionService(unittest.TestCase):
    def test_start_session_chat_run_updates_last_active_and_starts_run(self):
        active_sessions = {"sid-1": {"info": {"last_active": 0}}}
        calls = []
        fake_run = object()

        def fake_start_run(session_id, stream_factory):
            calls.append((session_id, stream_factory))
            return fake_run

        run = start_session_chat_run(
            active_sessions,
            "sid-1",
            fake_stream,
            start_run=fake_start_run,
            now=lambda: 123.45,
        )

        self.assertIs(run, fake_run)
        self.assertEqual(active_sessions["sid-1"]["info"]["last_active"], 123.45)
        self.assertEqual(calls, [("sid-1", fake_stream)])

    def test_start_session_chat_run_rejects_missing_session(self):
        with self.assertRaises(ChatSessionServiceError) as ctx:
            start_session_chat_run({}, "missing", fake_stream)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "会话已过期或不存在，请重新连接")

    def test_request_session_stop_sets_cancel_flag_and_stops_run(self):
        cancel_flags = {}
        stopped = []
        active_sessions = {"sid-1": {"info": {"pending_messages": []}}}
        memory_db = FakeMemoryDB()

        audit_message = request_session_stop(
            "sid-1",
            cancel_flags=cancel_flags,
            active_sessions=active_sessions,
            memory_db=memory_db,
            now=lambda: 123.456,
            stop_run=lambda session_id: stopped.append(session_id) or True,
        )

        self.assertTrue(cancel_flags["sid-1"])
        self.assertEqual(stopped, ["sid-1"])
        self.assertIsNotNone(audit_message)
        self.assertEqual(audit_message["role"], "system")
        self.assertEqual(audit_message["memory_type"], STOP_AUDIT_MEMORY_TYPE)
        self.assertTrue(audit_message["visible_to_user"])
        self.assertEqual(audit_message["timestamp"], 123456)
        self.assertEqual(active_sessions["sid-1"]["info"]["pending_messages"], [audit_message])
        self.assertEqual(memory_db.messages, [("sid-1", audit_message)])

    def test_request_session_stop_uses_default_cancel_flags(self):
        cancel_flags = {}

        with patch("core.agent.cancel_flags", cancel_flags):
            request_session_stop("sid-default")

        self.assertTrue(cancel_flags["sid-default"])
