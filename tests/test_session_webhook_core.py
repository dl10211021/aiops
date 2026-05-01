import unittest

from core.session_webhook import (
    SessionWebhookError,
    build_session_webhook_payload,
    validate_webhook_url,
    webhook_payload_preview,
)


class TestSessionWebhookCore(unittest.TestCase):
    def test_validate_webhook_url_rejects_embedded_credentials(self):
        with self.assertRaises(SessionWebhookError) as ctx:
            validate_webhook_url("https://user:pass@example.com/hook")

        self.assertEqual(ctx.exception.status_code, 422)

    def test_validate_webhook_url_requires_private_confirmation(self):
        with self.assertRaises(SessionWebhookError) as ctx:
            validate_webhook_url("http://127.0.0.1:9000/webhook")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("内网", ctx.exception.detail)

    def test_payload_preview_is_bounded(self):
        payload = build_session_webhook_payload(
            "sid-1",
            "profile",
            "generic",
            "测试报告",
            "x" * 3000,
            {"role_label": "Linux 主机"},
        )
        preview = webhook_payload_preview(payload)

        self.assertLessEqual(len(preview["preview"]), 2500)
        self.assertTrue(preview["truncated"])
