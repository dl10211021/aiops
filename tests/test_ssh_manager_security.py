import unittest
from unittest.mock import patch

import paramiko

from connections.ssh_manager import SSHConnectionManager
from core.connection_errors import classify_connection_error


class TestSSHManagerSecurity(unittest.TestCase):
    def test_connection_error_classifier_detects_common_categories(self):
        credential = classify_connection_error("ORA-01017: invalid username/password", "oracle")
        connection = classify_connection_error("Connection refused", "ssh")
        internal = classify_connection_error("unexpected parser crash", "ssh")

        self.assertEqual(credential["category"], "credential")
        self.assertEqual(credential["code"], "credential_invalid")
        self.assertIn("密码错误", credential["message"])
        self.assertEqual(connection["category"], "connection")
        self.assertEqual(connection["code"], "connection_failed")
        self.assertIn("连接失败", connection["message"])
        self.assertEqual(internal["category"], "internal")
        self.assertEqual(internal["code"], "internal_error")

    def test_ssh_auth_failure_returns_structured_error(self):
        manager = SSHConnectionManager()

        with patch("connections.ssh_manager.paramiko.SSHClient") as ssh_client_cls:
            ssh_client = ssh_client_cls.return_value
            ssh_client.connect.side_effect = paramiko.AuthenticationException(
                "Authentication failed."
            )

            result = manager.connect(
                host="192.0.2.10",
                port=22,
                username="ops",
                password="wrong-password",
                asset_type="linux",
                protocol="ssh",
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_category"], "credential")
        self.assertEqual(result["error_code"], "credential_invalid")
        self.assertIn("密码错误", result["message"])

    def test_ssh_network_failure_returns_structured_error(self):
        manager = SSHConnectionManager()

        with patch("connections.ssh_manager.paramiko.SSHClient") as ssh_client_cls:
            ssh_client = ssh_client_cls.return_value
            ssh_client.connect.side_effect = TimeoutError("timed out")

            result = manager.connect(
                host="192.0.2.10",
                port=22,
                username="ops",
                password="secret",
                asset_type="linux",
                protocol="ssh",
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_category"], "connection")
        self.assertEqual(result["error_code"], "connection_failed")
        self.assertIn("连接失败", result["message"])

    def test_virtual_asset_registration_log_redacts_extra_args_credentials(self):
        manager = SSHConnectionManager()
        secret_values = {
            "api_token": "plain-api-token-value",
            "secret_key": "plain-secret-key-value",
            "aws_secret_access_key": "plain-aws-secret-value",
            "nested": {"api_key": "plain-nested-api-key-value"},
        }

        with self.assertLogs("connections.ssh_manager", level="INFO") as logs:
            result = manager.connect(
                host="192.0.2.10",
                port=443,
                username="ops",
                password="managed-password",
                asset_type="harbor",
                protocol="http_api",
                extra_args={**secret_values, "scheme": "https"},
            )

        try:
            self.assertTrue(result["success"])
            joined_logs = "\n".join(logs.output)
            for secret in [
                "plain-api-token-value",
                "plain-secret-key-value",
                "plain-aws-secret-value",
                "plain-nested-api-key-value",
                "managed-password",
            ]:
                self.assertNotIn(secret, joined_logs)
            self.assertIn("'api_token': '***'", joined_logs)
            self.assertIn("'secret_key': '***'", joined_logs)
            self.assertEqual(
                manager.active_sessions[result["session_id"]]["info"]["extra_args"][
                    "api_token"
                ],
                secret_values["api_token"],
            )
        finally:
            manager.disconnect(result["session_id"])

    def test_network_cli_uses_dedicated_client(self):
        manager = SSHConnectionManager()
        pooled_client = object()
        manager.active_sessions["sid-net"] = {
            "client": pooled_client,
            "info": {
                "host": "192.168.100.100",
                "port": 22,
                "username": "admin",
                "password": "secret",
                "asset_type": "h3c_switch",
                "protocol": "ssh",
                "extra_args": {},
            },
        }

        class FakeChannel:
            def __init__(self):
                self.sent = []
                self.closed = False

            def settimeout(self, _timeout):
                pass

            def send(self, data):
                self.sent.append(data)

            def close(self):
                self.closed = True

        class FakeClient:
            def __init__(self):
                self.channel = FakeChannel()
                self.closed = False

            def invoke_shell(self, *args, **kwargs):
                return self.channel

            def close(self):
                self.closed = True

        dedicated_client = FakeClient()
        with (
            patch.object(
                manager,
                "_create_client_from_session_info",
                return_value=dedicated_client,
            ) as create_client,
            patch.object(manager, "_read_cli_until_idle", return_value="ok"),
        ):
            result = manager.execute_network_cli_command(
                "sid-net",
                "display version",
                timeout=5,
            )

        self.assertTrue(result["success"])
        self.assertIs(manager.active_sessions["sid-net"]["client"], pooled_client)
        create_client.assert_called_once()
        self.assertTrue(dedicated_client.closed)
        self.assertIn("display version\n", dedicated_client.channel.sent)

    def test_terminal_channel_closes_dedicated_client(self):
        manager = SSHConnectionManager()
        manager.active_sessions["sid-term"] = {
            "client": object(),
            "info": {
                "host": "192.168.100.100",
                "port": 22,
                "username": "admin",
                "password": "secret",
                "asset_type": "h3c_switch",
                "protocol": "ssh",
                "extra_args": {},
            },
        }

        class FakeChannel:
            def __init__(self):
                self.closed = False

            def settimeout(self, _timeout):
                pass

            def close(self):
                self.closed = True

        class FakeClient:
            def __init__(self):
                self.channel = FakeChannel()
                self.closed = False

            def invoke_shell(self, *args, **kwargs):
                return self.channel

            def close(self):
                self.closed = True

        dedicated_client = FakeClient()
        with patch.object(
            manager,
            "_create_client_from_session_info",
            return_value=dedicated_client,
        ):
            channel = manager.open_terminal_channel("sid-term", width=120, height=40)

        self.assertIs(getattr(channel, "_opscore_client"), dedicated_client)
        manager.close_terminal_channel(channel)
        self.assertTrue(channel.closed)
        self.assertTrue(dedicated_client.closed)


if __name__ == "__main__":
    unittest.main()
