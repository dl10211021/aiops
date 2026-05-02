import asyncio
import unittest
from unittest.mock import patch

from api import notification_routes, routes
from api.schemas import NotificationConfigRequest, TestNotificationRequest


class TestNotificationRoutes(unittest.TestCase):
    def test_notification_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/config/notifications", paths)
        self.assertIn("/config/notifications/test", paths)

    def test_get_notification_config_preserves_response_shape(self):
        config = {"wechat_enabled": True, "smtp_port": 465}

        with patch("api.notification_routes.build_notification_config", return_value=config):
            response = asyncio.run(notification_routes.get_notification_config())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, config)

    def test_update_notification_config_preserves_response_shape(self):
        request = NotificationConfigRequest(
            wechat_enabled=True,
            wechat_webhook="https://wechat.example/hook",
            dingtalk_enabled=False,
            dingtalk_webhook="",
            email_enabled=True,
            email_address="ops@example.com",
            smtp_server="smtp.example.com",
            smtp_port=465,
            smtp_user="ops",
            smtp_pass="secret",
        )

        with patch("api.notification_routes.save_notification_config_record") as save_config:
            response = asyncio.run(notification_routes.update_notification_config(request))

        save_config.assert_called_once_with(request.model_dump())
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "告警通道配置已保存并生效")

    def test_test_notification_channel_preserves_response_shape(self):
        with patch(
            "api.notification_routes.send_notification_channel_test",
            return_value="企业微信测试消息发送成功！请查看您的群组。",
        ):
            response = asyncio.run(
                notification_routes.test_notification_channel(
                    TestNotificationRequest(channel="wechat")
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "企业微信测试消息发送成功！请查看您的群组。")


if __name__ == "__main__":
    unittest.main()
