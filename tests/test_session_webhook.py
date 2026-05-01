import unittest

from fastapi import HTTPException

from api import routes


class TestSessionWebhookHardening(unittest.TestCase):
    def test_webhook_url_rejects_embedded_credentials(self):
        with self.assertRaises(HTTPException) as ctx:
            routes._validate_webhook_url("https://user:pass@example.com/hook")

        self.assertEqual(ctx.exception.status_code, 422)

    def test_webhook_url_rejects_private_target_without_confirmation(self):
        with self.assertRaises(HTTPException) as ctx:
            routes._validate_webhook_url("http://127.0.0.1:9000/webhook")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("内网", ctx.exception.detail)

    def test_webhook_url_allows_private_target_with_confirmation(self):
        url, target = routes._validate_webhook_url(
            "http://127.0.0.1:9000/webhook",
            allow_private_targets=True,
        )

        self.assertEqual(url, "http://127.0.0.1:9000/webhook")
        self.assertTrue(target["private_target"])

    def test_webhook_payload_preview_is_bounded(self):
        payload = routes._build_session_webhook_payload(
            "sid-1",
            "profile",
            "generic",
            "测试报告",
            "x" * 3000,
            {"role_label": "Linux 主机"},
        )
        preview = routes._webhook_payload_preview(payload)

        self.assertLessEqual(len(preview["preview"]), 2500)
        self.assertTrue(preview["truncated"])

