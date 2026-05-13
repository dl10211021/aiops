import asyncio
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core.alert_webhook_service import (
    ACTIVE_ALERT_MESSAGE_TEMPLATE,
    NO_ACTIVE_ALERT_MESSAGE,
    RECORD_ONLY_ALERT_MESSAGE,
    affected_alert_sessions,
    handle_alert_webhook,
    read_alert_webhook_payload,
    resolve_alert_notification_channels,
    run_alert_analysis_task,
    send_alert_analysis_notifications,
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
            return coro

        async def scenario():
            with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("idle")):
                result = await handle_alert_webhook(
                    {"host": "db.local", "alert_name": "DiskFull", "severity": "critical"},
                    active_sessions,
                    {},
                    "dispatcher",
                    heartbeat_runner,
                    memory_db=memory,
                    task_factory=task_factory,
                    notification_sender=lambda *_args: {"status": "SUCCESS", "message": "sent"},
                )
            self.assertTrue(active_sessions["sid-1"]["info"]["heartbeat_in_progress"])
            for coro in scheduled:
                await coro
            return result

        result = asyncio.run(scenario())

        self.assertEqual(result["data"]["injected_count"], 1)
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(runner_calls[0][0][0], "sid-1")
        self.assertEqual(runner_calls[0][0][3], "dispatcher")
        self.assertIn("DiskFull", runner_calls[0][1]["trigger_msg"])
        self.assertTrue(result["data"]["automation"]["notification_scheduled"])

    def test_batch_alertmanager_payload_persists_all_alerts_and_injects_once(self):
        from core import alert_events

        memory = FakeMemory()
        active_sessions = {
            "sid-db": {"info": {"host": "db.local"}},
            "sid-manager": {"info": {"host": "localhost"}},
        }
        runner_calls = []
        scheduled = []

        def heartbeat_runner(*args, **kwargs):
            runner_calls.append((args, kwargs))

            async def noop():
                return None

            return noop()

        def task_factory(coro):
            scheduled.append(coro)
            return coro

        payload = {
            "receiver": "alertmanager",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "DBDown", "instance": "db.local", "severity": "critical"},
                    "annotations": {"summary": "database target down"},
                    "fingerprint": "fp-db",
                },
                {
                    "status": "firing",
                    "labels": {"alertname": "WebLatency", "instance": "web.local", "severity": "warning"},
                    "annotations": {"summary": "web latency high"},
                    "fingerprint": "fp-web",
                },
            ],
        }

        async def scenario():
            with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("batch")):
                result = await handle_alert_webhook(
                    payload,
                    active_sessions,
                    {},
                    "dispatcher",
                    heartbeat_runner,
                    memory_db=memory,
                    task_factory=task_factory,
                    notification_sender=lambda *_args: {"status": "SUCCESS", "message": "sent"},
                )
            for coro in scheduled:
                await coro
            return result

        result = asyncio.run(scenario())

        self.assertEqual(len(result["data"]["alerts"]), 2)
        self.assertEqual(result["data"]["alert"]["fingerprint"], "fp-db")
        self.assertEqual(result["data"]["injected_count"], 2)
        self.assertEqual(len(scheduled), 2)
        self.assertIn("批量触发告警", runner_calls[0][1]["trigger_msg"])
        self.assertIn("DBDown", runner_calls[0][1]["trigger_msg"])
        self.assertIn("WebLatency", runner_calls[0][1]["trigger_msg"])
        self.assertTrue(result["data"]["automation"]["notification_scheduled"])

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

    def test_idle_session_uses_default_dispatcher_and_heartbeat_runner(self):
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
            return coro

        async def scenario():
            with (
                patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("default_runtime")),
                patch("core.alert_webhook_service.dispatcher_module.dispatcher", "default-dispatcher"),
                patch("core.alert_webhook_service.heartbeat_module.run_single_heartbeat", heartbeat_runner),
            ):
                result = await handle_alert_webhook(
                    {"host": "db.local", "alert_name": "DiskFull", "severity": "critical"},
                    active_sessions,
                    {},
                    memory_db=memory,
                    task_factory=task_factory,
                    notification_sender=lambda *_args: {"status": "SUCCESS", "message": "sent"},
                )
            for coro in scheduled:
                await coro
            return result

        result = asyncio.run(scenario())

        self.assertEqual(result["data"]["injected_count"], 1)
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(runner_calls[0][0][0], "sid-1")
        self.assertEqual(runner_calls[0][0][3], "default-dispatcher")

    def test_info_alert_is_recorded_without_ai_trigger(self):
        from core import alert_events

        with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("record_only")):
            result = asyncio.run(
                handle_alert_webhook(
                    {"host": "db.local", "alert_name": "FYI", "severity": "info"},
                    {"sid-1": {"info": {"host": "db.local"}}},
                    {},
                    object(),
                    lambda *_args, **_kwargs: None,
                    memory_db=FakeMemory(),
                )
            )

        self.assertEqual(result["message"], RECORD_ONLY_ALERT_MESSAGE)
        self.assertEqual(result["data"]["injected_count"], 0)
        self.assertFalse(result["data"]["automation"]["ai_triggered"])
        self.assertEqual(result["data"]["alert"]["noise_action"], "record_only")

    def test_alert_analysis_task_sends_backend_notification_after_report(self):
        sent = []

        async def heartbeat_runner(*_args, **_kwargs):
            return "根因：磁盘满；建议：扩容。"

        with patch.dict(
            "os.environ",
            {
                "WECHAT_ENABLED": "1",
                "WECHAT_WEBHOOK_URL": "https://wechat.example/hook",
                "DINGTALK_ENABLED": "1",
                "DINGTALK_WEBHOOK_URL": "https://dingtalk.example/hook",
                "EMAIL_ENABLED": "1",
                "ALERT_EMAIL_ADDRESS": "ops@example.com",
                "SMTP_SERVER": "smtp.example.com",
                "SMTP_USER": "ops@example.com",
                "SMTP_PASS": "secret",
            },
            clear=True,
        ):
            result = asyncio.run(
                run_alert_analysis_task(
                    session_id="sid-1",
                    info={},
                    store=FakeMemory(),
                    dispatcher="dispatcher",
                    heartbeat_runner=heartbeat_runner,
                    trigger_msg="alert",
                    alert_events=[
                        {
                            "alert_name": "DiskFull",
                            "host": "db.local",
                            "source_family": "zabbix",
                            "priority": "p0",
                            "notification_plan": {"targets": ["wechat", "dingtalk", "email"]},
                        }
                    ],
                    notify_after_analysis=True,
                    notification_sender=lambda channel, title, content: sent.append((channel, title, content))
                    or {"status": "SUCCESS", "message": "sent"},
                )
            )

        self.assertEqual(result, "根因：磁盘满；建议：扩容。")
        self.assertEqual([item[0] for item in sent], ["wechat", "dingtalk", "email"])
        self.assertIn("告警分析完成", sent[0][1])
        self.assertIn("根因：磁盘满", sent[0][2])

    def test_alert_notification_channels_only_use_ready_configured_targets(self):
        alert_events = [{"notification_plan": {"targets": ["wechat", "dingtalk", "email"]}}]
        env = {
            "WECHAT_ENABLED": "1",
            "WECHAT_WEBHOOK_URL": "https://wechat.example/hook",
            "DINGTALK_ENABLED": "1",
            "DINGTALK_WEBHOOK_URL": "",
            "EMAIL_ENABLED": "0",
            "ALERT_EMAIL_ADDRESS": "ops@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_USER": "ops@example.com",
            "SMTP_PASS": "secret",
        }

        self.assertEqual(resolve_alert_notification_channels(alert_events, env=env), ["wechat"])

    def test_alert_notification_returns_skipped_when_no_channel_ready(self):
        result = send_alert_analysis_notifications(
            [{"alert_name": "DiskFull", "notification_plan": {"targets": ["wechat"]}}],
            "sid-1",
            "report",
            env={},
        )

        self.assertEqual(result[0]["status"], "SKIPPED")
