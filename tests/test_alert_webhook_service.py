import asyncio
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core.alert_webhook_service import (
    ACTIVE_ALERT_MESSAGE_TEMPLATE,
    NO_ACTIVE_ALERT_MESSAGE,
    affected_alert_sessions,
    handle_alert_webhook,
    read_alert_webhook_payload,
)


class FakeMemory:
    def __init__(self):
        self.messages = []

    def append_message(self, session_id: str, message: dict):
        self.messages.append((session_id, message))


class TestAlertWebhookService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_alert_webhook_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_alert_webhook_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "alerts.json"

    def test_affected_sessions_match_host_all_and_localhost_fallback(self):
        sessions = {
            "sid-db": {"info": {"host": "db.local"}},
            "sid-manager": {"info": {"host": "localhost"}},
            "sid-web": {"info": {"host": "web.local"}},
        }

        self.assertEqual(affected_alert_sessions(sessions, "db.local"), ["sid-db", "sid-manager"])
        self.assertEqual(affected_alert_sessions(sessions, "all"), ["sid-db", "sid-manager", "sid-web"])

    def test_handle_alert_with_no_active_session_only_persists_event(self):
        from core import alert_events

        with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("none")):
            result = asyncio.run(
                handle_alert_webhook(
                    {"host": "db.local", "alert_name": "DiskFull", "severity": "critical"},
                    {},
                    {},
                    object(),
                    lambda *_args, **_kwargs: None,
                    memory_db=FakeMemory(),
                )
            )

        self.assertEqual(result["message"], NO_ACTIVE_ALERT_MESSAGE)
        self.assertEqual(result["data"]["injected_count"], 0)
        self.assertEqual(result["data"]["alert"]["host"], "db.local")

    def test_read_alert_webhook_payload_returns_json_reader_result(self):
        async def json_reader():
            return {"host": "db.local", "alert_name": "DiskFull"}

        payload = asyncio.run(read_alert_webhook_payload(json_reader))

        self.assertEqual(payload["host"], "db.local")

    def test_read_alert_webhook_payload_falls_back_to_empty_payload_on_bad_json(self):
        async def json_reader():
            raise ValueError("invalid json")

        self.assertEqual(asyncio.run(read_alert_webhook_payload(json_reader)), {})

    def test_busy_session_appends_alert_to_context_without_scheduling_task(self):
        from core import alert_events

        memory = FakeMemory()
        scheduled = []
        active_sessions = {"sid-1": {"info": {"host": "db.local", "heartbeat_in_progress": True}}}

        def task_factory(coro):
            scheduled.append(coro)
            coro.close()

        with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("busy")):
            result = asyncio.run(
                handle_alert_webhook(
                    {"host": "db.local", "alert_name": "DiskFull", "severity": "critical"},
                    active_sessions,
                    {},
                    object(),
                    lambda *_args, **_kwargs: None,
                    memory_db=memory,
                    task_factory=task_factory,
                )
            )

        self.assertEqual(result["message"], ACTIVE_ALERT_MESSAGE_TEMPLATE.format(count=1))
        self.assertEqual(result["data"]["injected_count"], 1)
        self.assertEqual(scheduled, [])
        self.assertEqual(memory.messages[0][0], "sid-1")
        self.assertIn("DiskFull", memory.messages[0][1]["content"])

    def test_idle_session_sets_heartbeat_flag_and_schedules_task(self):
        from core import alert_events

        memory = FakeMemory()
        active_sessions = {"sid-1": {"info": {"host": "db.local"}}}
        runner_calls = []
        scheduled = []

        def heartbeat_runner(*args, **kwargs):
            runner_calls.append((args, kwargs))

            async def noop():
                return None

            return noop()

        def task_factory(coro):
            scheduled.append(coro)
            coro.close()

        with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("idle")):
            result = asyncio.run(
                handle_alert_webhook(
                    {"host": "db.local", "alert_name": "DiskFull", "severity": "critical"},
                    active_sessions,
                    {},
                    "dispatcher",
                    heartbeat_runner,
                    memory_db=memory,
                    task_factory=task_factory,
                )
            )

        self.assertEqual(result["data"]["injected_count"], 1)
        self.assertTrue(active_sessions["sid-1"]["info"]["heartbeat_in_progress"])
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(runner_calls[0][0][0], "sid-1")
        self.assertEqual(runner_calls[0][0][3], "dispatcher")
        self.assertIn("DiskFull", runner_calls[0][1]["trigger_msg"])

    def test_busy_session_uses_default_memory_db_when_not_injected(self):
        from core import alert_events

        memory = FakeMemory()
        active_sessions = {"sid-1": {"info": {"host": "db.local", "heartbeat_in_progress": True}}}

        with (
            patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("default_memory")),
            patch("core.memory.memory_db", memory),
        ):
            result = asyncio.run(
                handle_alert_webhook(
                    {"host": "db.local", "alert_name": "DiskFull", "severity": "critical"},
                    active_sessions,
                    {},
                    object(),
                    lambda *_args, **_kwargs: None,
                )
            )

        self.assertEqual(result["data"]["injected_count"], 1)
        self.assertEqual(memory.messages[0][0], "sid-1")
