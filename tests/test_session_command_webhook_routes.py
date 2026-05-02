import asyncio
import unittest
from unittest.mock import patch

from api import connection_routes, routes


class TestSessionCommandWebhookRoutes(unittest.TestCase):
    def _slash_command_request(self):
        return routes.SlashCommandPayload(
            id="inspect",
            label="巡检",
            prompt_template="请巡检当前资产",
        )

    def _webhook_request(self):
        return routes.SessionWebhookSendRequest(
            webhook_url="https://example.invalid/hook",
            payload_type="markdown",
            channel="generic",
        )

    def test_custom_slash_command_routes_preserve_response_shapes(self):
        command = {"id": "inspect", "label": "巡检"}
        request = self._slash_command_request()

        with patch("api.routes.list_custom_slash_command_records", return_value=[command]):
            list_response = asyncio.run(routes.list_custom_slash_commands())

        with patch("api.routes.save_custom_slash_command_record", return_value=command):
            create_response = asyncio.run(routes.create_custom_slash_command(request))
            update_response = asyncio.run(
                routes.update_custom_slash_command("inspect", request)
            )

        with patch("api.routes.remove_custom_slash_command_record") as remove_command:
            delete_response = asyncio.run(routes.delete_custom_slash_command("inspect"))

        remove_command.assert_called_once()
        self.assertEqual(list_response.status, "success")
        self.assertEqual(list_response.data, {"commands": [command]})
        self.assertEqual(create_response.status, "success")
        self.assertEqual(create_response.message, "快捷命令已保存")
        self.assertEqual(create_response.data, {"command": command})
        self.assertEqual(update_response.status, "success")
        self.assertEqual(update_response.message, "快捷命令已更新")
        self.assertEqual(update_response.data, {"command": command})
        self.assertEqual(delete_response.status, "success")
        self.assertEqual(delete_response.message, "快捷命令已删除")

    def test_session_webhook_routes_preserve_response_shapes(self):
        payload = {"payload_type": "markdown", "target": {"url": "https://example.invalid/hook"}}
        deliveries = [{"id": 1, "status": "success"}]
        request = self._webhook_request()

        with patch("api.routes.send_session_webhook_delivery", return_value=payload):
            send_response = asyncio.run(routes.send_session_webhook("sid-1", request))

        with patch("api.routes.preview_session_webhook_delivery", return_value=payload):
            preview_response = asyncio.run(routes.preview_session_webhook("sid-1", request))

        with patch(
            "api.routes.list_session_webhook_delivery_records",
            return_value=deliveries,
        ):
            history_response = asyncio.run(
                routes.list_session_webhook_history("sid-1", limit=5)
            )

        self.assertEqual(send_response.status, "success")
        self.assertEqual(send_response.message, "Webhook 已发送")
        self.assertEqual(send_response.data, payload)
        self.assertEqual(preview_response.status, "success")
        self.assertEqual(preview_response.data, payload)
        self.assertEqual(history_response.status, "success")
        self.assertEqual(history_response.data, {"deliveries": deliveries})

    def test_close_connection_preserves_response_shape(self):
        with patch.object(connection_routes.ssh_manager, "disconnect", return_value=True):
            response = asyncio.run(connection_routes.close_ssh_connection("sid-1"))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "Connection closed safely")


if __name__ == "__main__":
    unittest.main()
