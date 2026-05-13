import unittest

from core.notification_config import (
    MASKED_VALUE,
    build_notification_channel_statuses,
    build_notification_config,
    build_notification_env_values,
    env_or_existing,
    save_notification_config,
)


class TestNotificationConfig(unittest.TestCase):
    def test_build_notification_config_masks_sensitive_values(self):
        config = build_notification_config(
            {
                "WECHAT_ENABLED": "0",
                "WECHAT_WEBHOOK_URL": "https://qy.example/webhook",
                "DINGTALK_ENABLED": "1",
                "DINGTALK_WEBHOOK_URL": "",
                "EMAIL_ENABLED": "0",
                "ALERT_EMAIL_ADDRESS": "ops@example.com",
                "SMTP_SERVER": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "ops",
                "SMTP_PASS": "secret",
            }
        )

        self.assertFalse(config["wechat_enabled"])
        self.assertEqual(config["wechat_webhook"], MASKED_VALUE)
        self.assertTrue(config["dingtalk_enabled"])
        self.assertEqual(config["dingtalk_webhook"], "")
        self.assertFalse(config["email_enabled"])
        self.assertEqual(config["email_address"], "ops@example.com")
        self.assertEqual(config["smtp_port"], 587)
        self.assertEqual(config["smtp_pass"], MASKED_VALUE)
        self.assertEqual(config["channels"][0]["channel"], "wechat")
        self.assertEqual(config["channels"][0]["status"], "disabled")
        self.assertFalse(config["channels"][0]["ready"])

    def test_build_notification_config_uses_existing_defaults(self):
        config = build_notification_config({})

        self.assertTrue(config["wechat_enabled"])
        self.assertTrue(config["dingtalk_enabled"])
        self.assertTrue(config["email_enabled"])
        self.assertEqual(config["smtp_port"], 465)
        self.assertEqual(config["smtp_pass"], "")
        self.assertEqual(config["channels"][0]["status"], "missing_config")

    def test_build_notification_channel_statuses_marks_ready_channels(self):
        channels = build_notification_channel_statuses(
            {
                "WECHAT_ENABLED": "1",
                "WECHAT_WEBHOOK_URL": "https://qy.example/hook",
                "DINGTALK_ENABLED": "1",
                "DINGTALK_WEBHOOK_URL": "",
                "EMAIL_ENABLED": "1",
                "ALERT_EMAIL_ADDRESS": "ops@example.com",
                "SMTP_SERVER": "smtp.example.com",
                "SMTP_USER": "ops",
                "SMTP_PASS": "secret",
            }
        )

        by_channel = {item["channel"]: item for item in channels}
        self.assertEqual(by_channel["wechat"]["status"], "ready")
        self.assertTrue(by_channel["wechat"]["ready"])
        self.assertEqual(by_channel["dingtalk"]["status"], "missing_config")
        self.assertEqual(by_channel["email"]["status"], "ready")

    def test_env_or_existing_preserves_masked_secret(self):
        self.assertEqual(
            env_or_existing(MASKED_VALUE, "SMTP_PASS", {"SMTP_PASS": "old-secret"}),
            "old-secret",
        )
        self.assertEqual(
            env_or_existing("new-secret", "SMTP_PASS", {"SMTP_PASS": "old-secret"}),
            "new-secret",
        )

    def test_build_notification_env_values_preserves_masked_fields(self):
        env_values = build_notification_env_values(
            {
                "wechat_enabled": False,
                "wechat_webhook": MASKED_VALUE,
                "dingtalk_enabled": True,
                "dingtalk_webhook": "https://dingtalk.example/hook",
                "email_enabled": False,
                "email_address": "alerts@example.com",
                "smtp_server": "smtp.example.com",
                "smtp_port": 2525,
                "smtp_user": "alerts",
                "smtp_pass": MASKED_VALUE,
            },
            {
                "WECHAT_WEBHOOK_URL": "https://old-wechat.example/hook",
                "SMTP_PASS": "old-password",
            },
        )

        self.assertEqual(env_values["WECHAT_ENABLED"], "0")
        self.assertEqual(
            env_values["WECHAT_WEBHOOK_URL"],
            "https://old-wechat.example/hook",
        )
        self.assertEqual(env_values["DINGTALK_ENABLED"], "1")
        self.assertEqual(env_values["DINGTALK_WEBHOOK_URL"], "https://dingtalk.example/hook")
        self.assertEqual(env_values["EMAIL_ENABLED"], "0")
        self.assertEqual(env_values["ALERT_EMAIL_ADDRESS"], "alerts@example.com")
        self.assertEqual(env_values["SMTP_PORT"], "2525")
        self.assertEqual(env_values["SMTP_PASS"], "old-password")

    def test_save_notification_config_updates_env_and_persists_values(self):
        persisted = []
        env = {"SMTP_PASS": "old-password"}

        values = save_notification_config(
            {
                "wechat_enabled": True,
                "wechat_webhook": "https://wechat.example/hook",
                "dingtalk_enabled": False,
                "dingtalk_webhook": "",
                "email_enabled": True,
                "email_address": "ops@example.com",
                "smtp_server": "smtp.example.com",
                "smtp_port": 465,
                "smtp_user": "ops",
                "smtp_pass": MASKED_VALUE,
            },
            env=env,
            persist=persisted.append,
        )

        self.assertEqual(env["WECHAT_WEBHOOK_URL"], "https://wechat.example/hook")
        self.assertEqual(env["SMTP_PASS"], "old-password")
        self.assertEqual(values["DINGTALK_ENABLED"], "0")
        self.assertEqual(persisted, [values])
