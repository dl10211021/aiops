import asyncio
import unittest

from core.session_webhook_service import (
    SessionWebhookServiceError,
    preview_session_webhook_delivery,
    resolve_session_webhook_target,
    send_session_webhook_delivery,
)


class FakeWebhookMemory:
    def __init__(self):
        self.deliveries = []

    def get_messages(self, session_id: str, for_ui: bool = True):
        return [
            {"role": "user", "content": "帮我检查磁盘"},
            {"role": "assistant", "content": "磁盘使用率正常"},
        ]

    def append_webhook_delivery(self, record: dict):
        self.deliveries.append(record)


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
                self.memory,
                self.active_sessions,
                session_id="sid-1",
                webhook_url="http://127.0.0.1:9000/webhook",
                payload_type="markdown",
                channel="generic",
                allow_private_targets=True,
            )
        )

        self.assertEqual(payload["payload_type"], "markdown")
        self.assertEqual(payload["channel"], "generic")
        self.assertTrue(payload["target"]["private_target"])
        self.assertIn("帮我检查磁盘", payload["payload"]["preview"])

    def test_send_delivery_records_success(self):
        def poster(url: str, payload: dict):
            return 202, "accepted"

        payload = asyncio.run(
            send_session_webhook_delivery(
                self.memory,
                self.active_sessions,
                session_id="sid-1",
                webhook_url="http://127.0.0.1:9000/webhook",
                payload_type="markdown",
                channel="generic",
                allow_private_targets=True,
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
                    self.memory,
                    self.active_sessions,
                    session_id="sid-1",
                    webhook_url="http://127.0.0.1:9000/webhook",
                    payload_type="markdown",
                    channel="generic",
                    allow_private_targets=True,
                    poster=poster,
                )
            )

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(self.memory.deliveries[0]["status"], "error")
        self.assertEqual(self.memory.deliveries[0]["http_status"], 500)
