import asyncio
import json
import unittest
from unittest.mock import patch

from core.dispatcher_session_tools import execute_session_tool


class DispatcherSessionToolsTest(unittest.TestCase):
    def test_linux_tool_rejects_network_asset(self):
        result = asyncio.run(
            execute_session_tool(
                "linux_execute_command",
                {"command": "uname -a"},
                {
                    "session_id": "sid",
                    "asset_type": "switch",
                    "protocol": "ssh",
                    "extra_args": {"category": "network"},
                    "allow_modifications": False,
                },
            )
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("network_cli_execute_command", payload["error"])

    def test_winrm_command_uses_managed_credentials(self):
        context = {
            "asset_type": "windows",
            "protocol": "winrm",
            "host": "win.local",
            "port": 5985,
            "username": "managed_user",
            "password": "managed_secret",
            "extra_args": {},
            "allow_modifications": False,
        }

        with patch("connections.winrm_manager.winrm_executor.execute_command") as execute_command:
            execute_command.return_value = {"success": True, "output": "ok"}
            result = asyncio.run(
                execute_session_tool(
                    "winrm_execute_command",
                    {"username": "bad", "password": "bad", "command": "Get-Date"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_command.assert_called_once_with(
            host="win.local",
            port=5985,
            username="managed_user",
            password="managed_secret",
            command="Get-Date",
            extra_args={},
        )

    def test_snmp_v3_prefers_auth_user(self):
        context = {
            "asset_type": "snmp",
            "protocol": "snmp",
            "host": "192.168.46.30",
            "port": 161,
            "username": "root",
            "extra_args": {
                "snmp_version": "v3",
                "v3_auth_user": "snmp-reader",
                "v3_auth_pass": "auth-secret",
            },
            "allow_modifications": False,
        }

        with patch("connections.snmp_manager.snmp_executor.get") as snmp_get:
            snmp_get.return_value = {"success": True, "data": []}
            result = asyncio.run(
                execute_session_tool(
                    "snmp_get",
                    {"oid": "1.3.6.1.2.1.1.1.0"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        passed_args = snmp_get.call_args.kwargs["extra_args"]
        self.assertEqual(passed_args["v3_username"], "snmp-reader")

    def test_list_active_sessions_hides_sensitive_fields(self):
        from connections.ssh_manager import ssh_manager

        active_sessions = {
            "sid-1": {
                "info": {
                    "host": "10.0.0.1",
                    "remark": "core host",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "agent_profile": "linux",
                    "allow_modifications": False,
                    "password": "secret",
                }
            }
        }
        with patch.object(ssh_manager, "active_sessions", active_sessions):
            result = asyncio.run(execute_session_tool("list_active_sessions", {}, {}))

        payload = json.loads(result)
        self.assertEqual(payload["active_sessions"][0]["session_id"], "sid-1")
        self.assertNotIn("password", payload["active_sessions"][0])


if __name__ == "__main__":
    unittest.main()
