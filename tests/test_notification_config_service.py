import unittest
from unittest.mock import patch

from core.notification_config_service import save_notification_config_record


class TestNotificationConfigService(unittest.TestCase):
    def _config(self):
        return {
            "wechat_enabled": True,
            "wechat_webhook": "https://wechat.example/hook",
            "dingtalk_enabled": False,
            "dingtalk_webhook": "",
            "email_enabled": True,
            "email_address": "ops@example.com",
            "smtp_server": "smtp.example.com",
            "smtp_port": 465,
            "smtp_user": "ops",
            "smtp_pass": "secret",
        }

    def test_save_notification_config_record_uses_injected_persist(self):
        persisted = []

        values = save_notification_config_record(self._config(), persist=persisted.append)

        self.assertEqual(values["WECHAT_WEBHOOK_URL"], "https://wechat.example/hook")
        self.assertEqual(persisted, [values])

    def test_save_notification_config_record_uses_default_env_persist(self):
        with patch("core.notification_config_service.app_config_service.update_env_file_values") as persist:
            values = save_notification_config_record(self._config())

        persist.assert_called_once_with(values)


if __name__ == "__main__":
    unittest.main()
