import datetime
import unittest
from unittest.mock import patch

from core.notification_test import (
    NotificationTestError,
    build_notification_test_content,
    build_notification_webhook_payload,
    send_notification_channel_test,
)


class TestNotificationTest(unittest.TestCase):
    def test_build_notification_test_content_uses_supplied_time(self):
        title, content = build_notification_test_content(
            datetime.datetime(2026, 5, 1, 9, 30, 15)
        )

        self.assertEqual(title, "SkillOps 平台连通性测试")
        self.assertIn("2026-05-01 09:30:15", content)

    def test_build_webhook_payload_matches_channel_shape(self):
        wechat = build_notification_webhook_payload("wechat", "标题", "内容")
        dingtalk = build_notification_webhook_payload("dingtalk", "标题", "内容")

        self.assertEqual(wechat["markdown"]["content"], "## 标题\n内容")
        self.assertEqual(dingtalk["markdown"]["title"], "标题")
        self.assertEqual(dingtalk["markdown"]["text"], "## 标题\n内容")

    def test_missing_channel_config_raises_typed_error(self):
        with self.assertRaises(NotificationTestError) as ctx:
            send_notification_channel_test("wechat", {})

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "请先配置企业微信 Webhook 地址")

    def test_wechat_test_posts_payload(self):
        fixed_now = datetime.datetime(2026, 5, 1, 9, 30, 15)
        with patch("urllib.request.urlopen") as urlopen:
            message = send_notification_channel_test(
                "wechat",
                {"WECHAT_WEBHOOK_URL": "https://example.invalid/webhook"},
                fixed_now,
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(message, "企业微信测试消息发送成功！请查看您的群组。")
        self.assertEqual(request.full_url, "https://example.invalid/webhook")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)
