import asyncio
import json
import unittest
from unittest.mock import patch

from core.dispatcher_utility_tools import execute_utility_tool, filter_assets_by_tags


class DispatcherUtilityToolsTest(unittest.TestCase):
    def test_filter_assets_by_tags_hides_sensitive_fields(self):
        assets = [
            {
                "id": 1,
                "host": "10.0.0.1",
                "port": 22,
                "username": "ops",
                "password": "secret",
                "asset_type": "linux",
                "protocol": "ssh",
                "remark": "prod",
                "tags": ["prod", "db"],
            },
            {
                "id": 2,
                "host": "10.0.0.2",
                "password": "secret",
                "asset_type": "linux",
                "protocol": "ssh",
                "tags": ["dev"],
            },
        ]

        matched = filter_assets_by_tags(assets, ["prod", "db"])

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["host"], "10.0.0.1")
        self.assertNotIn("password", matched[0])

    def test_send_notification_delegates_to_notifier(self):
        with patch("core.notifier.send_notification") as send_notification:
            send_notification.return_value = {"success": True}
            result = asyncio.run(
                execute_utility_tool(
                    "send_notification",
                    {"channel": "wechat", "title": "巡检", "content": "完成"},
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        send_notification.assert_called_once_with("wechat", "巡检", "完成")


if __name__ == "__main__":
    unittest.main()
