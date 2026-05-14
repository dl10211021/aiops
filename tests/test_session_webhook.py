import asyncio
import unittest
from unittest.mock import patch

from core.session_webhook_service import (
    SessionWebhookServiceError,
    build_session_webhook_markdown,
    list_session_webhook_delivery_records,
    preview_session_webhook_delivery,
    resolve_session_webhook_target,
    send_session_webhook_delivery,
)


class FakeWebhookMemory:
    def __init__(self):
        self.deliveries = []
        self.messages = [
            {"role": "user", "content": "帮我检查磁盘"},
            {"role": "assistant", "content": "磁盘使用率正常"},
        ]

    def get_messages(self, session_id: str, for_ui: bool = True):
        return self.messages

    def append_webhook_delivery(self, record: dict):
        self.deliveries.append(record)

    def list_webhook_deliveries(self, session_id: str, limit: int):
        self.list_args = (session_id, limit)
        return self.deliveries[:limit]


class TestSessionWebhookService(unittest.TestCase):
    def setUp(self):
        self.memory = FakeWebhookMemory()
        self.active_sessions = {"sid-1": {"info": {"remark": "生产数据库"}}}

    def test_webhook_url_rejects_embedded_credentials(self):
        with self.assertRaises(SessionWebhookServiceError) as ctx:
            resolve_session_webhook_target("https://user:pass@example.com/hook")

        self.assertEqual(ctx.exception.status_code, 422)

    def test_webhook_url_rejects_private_target_without_confirmation(self):
        with self.assertRaises(SessionWebhookServiceError) as ctx:
            resolve_session_webhook_target("http://127.0.0.1:9000/webhook")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("内网", ctx.exception.detail)

    def test_webhook_url_allows_private_target_with_confirmation(self):
        url, target = resolve_session_webhook_target(
            "http://127.0.0.1:9000/webhook",
            allow_private_targets=True,
        )

        self.assertEqual(url, "http://127.0.0.1:9000/webhook")
        self.assertTrue(target["private_target"])

    def test_preview_delivery_uses_session_history_markdown(self):
        payload = asyncio.run(
            preview_session_webhook_delivery(
                self.active_sessions,
                session_id="sid-1",
                webhook_url="http://127.0.0.1:9000/webhook",
                payload_type="markdown",
                channel="generic",
                allow_private_targets=True,
                memory_db=self.memory,
            )
        )

        self.assertEqual(payload["payload_type"], "markdown")
        self.assertEqual(payload["channel"], "generic")
        self.assertTrue(payload["target"]["private_target"])
        self.assertIn("帮我检查磁盘", payload["payload"]["preview"])

    def test_summary_delivery_includes_execution_audit_excerpt_before_truncated_history(self):
        self.memory.messages = [
            {"role": "user", "content": "请做一次审计\n" + ("长内容" * 700)},
            {
                "role": "assistant",
                "content": "查询完成",
                "exec_trace": [
                    {
                        "tool": "db_execute_query",
                        "status": "done",
                        "args": "select 1 from dual",
                        "result": '{"success": true}',
                        "resultMeta": {
                            "tool_policy": {
                                "operation_mode": "read_write",
                                "approval_policy": "guarded_write",
                                "evidence_family": "database",
                            }
                        },
                        "evidenceId": "tev-sid-1-call-1",
                    }
                ],
            },
        ]
        with (
            patch("core.session_profile.get_session_profile", return_value={"id": "sid-1"}),
            patch("core.session_profile.profile_to_markdown", return_value="# 会话画像\n\n生产数据库"),
        ):
            markdown, profile = asyncio.run(
                build_session_webhook_markdown(
                    self.active_sessions,
                    "sid-1",
                    "summary",
                    memory_db=self.memory,
                )
            )

        self.assertEqual(profile, {"id": "sid-1"})
        self.assertIn("## 执行审计摘要", markdown)
        self.assertIn("- Step 1: 数据库 SQL 执行 (`db_execute_query`) [done]", markdown)
        self.assertIn("  - Policy: 读写受控；写入受控；数据库证据", markdown)
        self.assertIn("  - Evidence: tev-sid-1-call-1", markdown)
        self.assertIn("## 会话摘要", markdown)

    def test_send_delivery_records_success(self):
        def poster(url: str, payload: dict):
            return 202, "accepted"

        payload = asyncio.run(
            send_session_webhook_delivery(
                self.active_sessions,
                session_id="sid-1",
                webhook_url="http://127.0.0.1:9000/webhook",
                payload_type="markdown",
                channel="generic",
                allow_private_targets=True,
                memory_db=self.memory,
                poster=poster,
            )
        )

        self.assertEqual(payload["http_status"], 202)
        self.assertEqual(payload["response_preview"], "accepted")
        self.assertEqual(self.memory.deliveries[0]["status"], "success")

    def test_send_delivery_records_http_error_before_raising(self):
        def poster(url: str, payload: dict):
            return 500, "failed"

        with self.assertRaises(SessionWebhookServiceError) as ctx:
            asyncio.run(
                send_session_webhook_delivery(
                    self.active_sessions,
                    session_id="sid-1",
                    webhook_url="http://127.0.0.1:9000/webhook",
                    payload_type="markdown",
                    channel="generic",
                    allow_private_targets=True,
                    memory_db=self.memory,
                    poster=poster,
                )
            )

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(self.memory.deliveries[0]["status"], "error")
        self.assertEqual(self.memory.deliveries[0]["http_status"], 500)

    def test_list_delivery_records_delegates_to_memory_db(self):
        self.memory.deliveries = [{"id": 1}, {"id": 2}]

        deliveries = asyncio.run(
            list_session_webhook_delivery_records("sid-1", 1, memory_db=self.memory)
        )

        self.assertEqual(deliveries, [{"id": 1}])
        self.assertEqual(self.memory.list_args, ("sid-1", 1))

    def test_list_delivery_records_maps_storage_errors(self):
        class FailingMemory(FakeWebhookMemory):
            def list_webhook_deliveries(self, *_args):
                raise RuntimeError("db unavailable")

        with self.assertRaises(SessionWebhookServiceError) as ctx:
            asyncio.run(
                list_session_webhook_delivery_records(
                    "sid-1",
                    10,
                    memory_db=FailingMemory(),
                )
            )

        self.assertEqual(ctx.exception.status_code, 500)
