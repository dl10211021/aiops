import asyncio
import json
import unittest
from unittest.mock import patch

from core.dispatcher import SkillDispatcher


def tool_names(tools):
    return {tool["function"]["name"] for tool in tools}


class TestDispatcherProtocolTools(unittest.TestCase):
    def test_windows_session_exposes_winrm_not_linux_or_db(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "windows",
                "protocol": "winrm",
                "extra_args": {},
            }
        )

        names = tool_names(tools)
        self.assertIn("winrm_execute_command", names)
        self.assertNotIn("linux_execute_command", names)
        self.assertNotIn("db_execute_query", names)
        self.assertNotIn("local_execute_script", names)

    def test_mysql_session_exposes_database_tool_only(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "mysql",
                "protocol": "mysql",
                "extra_args": {"db_type": "mysql"},
            }
        )

        names = tool_names(tools)
        self.assertIn("db_execute_query", names)
        self.assertNotIn("linux_execute_command", names)
        self.assertNotIn("winrm_execute_command", names)
        self.assertNotIn("local_execute_script", names)

    def test_native_session_still_hides_local_script_when_skill_mounted(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "windows",
                "protocol": "winrm",
                "extra_args": {},
                "active_skill_paths": ["D:/AIOPS/skillops - 20260225/my_custom_skills/window"],
            }
        )

        names = tool_names(tools)
        self.assertIn("winrm_execute_command", names)
        self.assertNotIn("local_execute_script", names)

    def test_virtual_session_exposes_local_script_for_skill_work(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "virtual",
                "extra_args": {"login_protocol": "virtual"},
                "active_skill_paths": ["D:/AIOPS/skillops - 20260225/my_custom_skills/skill-creator"],
            }
        )

        names = tool_names(tools)
        self.assertIn("local_execute_script", names)

    def test_monitoring_session_exposes_http_api_tool(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "extra_args": {},
            }
        )

        self.assertIn("http_api_request", tool_names(tools))

    def test_switch_session_exposes_network_cli_not_linux_tool(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "switch",
                "protocol": "ssh",
                "extra_args": {"category": "network"},
            }
        )

        names = tool_names(tools)
        self.assertIn("network_cli_execute_command", names)
        self.assertNotIn("linux_execute_command", names)
        self.assertNotIn("local_execute_script", names)

    def test_switch_rejects_linux_command_even_if_model_calls_it(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        result = asyncio.run(
            dispatcher.route_and_execute(
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

    def test_hard_block_runs_before_tool_execution(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        result = asyncio.run(
            dispatcher.route_and_execute(
                "network_cli_execute_command",
                {"command": "reset saved-configuration"},
                {
                    "session_id": "managed-session",
                    "asset_type": "switch",
                    "protocol": "ssh",
                    "extra_args": {"category": "network"},
                    "allow_modifications": True,
                },
            )
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("硬拦截", payload["reason"])

    def test_db_query_uses_managed_session_credentials(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "asset_type": "mysql",
            "protocol": "mysql",
            "host": "db.local",
            "port": 3306,
            "username": "managed_user",
            "password": "managed_secret",
            "extra_args": {"db_name": "ops", "db_type": "mysql"},
            "allow_modifications": False,
        }

        with patch("connections.db_manager.db_executor.execute_query") as execute_query:
            execute_query.return_value = json.dumps({"success": True, "data": []})
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "db_execute_query",
                    {
                        "host": "attacker",
                        "user": "bad",
                        "password": "bad",
                        "database": "bad",
                        "sql": "SELECT 1",
                    },
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_query.assert_called_once_with(
            "mysql",
            "db.local",
            3306,
            "managed_user",
            "managed_secret",
            "ops",
            "SELECT 1",
            {"db_name": "ops", "db_type": "mysql"},
        )

    def test_winrm_command_uses_managed_session_credentials(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
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
                dispatcher.route_and_execute(
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

    def test_network_cli_uses_managed_session(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "session_id": "managed-session",
            "asset_type": "switch",
            "protocol": "ssh",
            "extra_args": {"category": "network"},
            "allow_modifications": False,
        }

        with patch("connections.ssh_manager.ssh_manager.execute_network_cli_command") as execute_command:
            execute_command.return_value = {"success": True, "output": "ok"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "network_cli_execute_command",
                    {"command": "display version"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_command.assert_called_once_with("managed-session", "display version")

    def test_snmp_v3_prefers_configured_auth_user_over_hidden_base_username(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
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
                dispatcher.route_and_execute(
                    "snmp_get",
                    {"oid": "1.3.6.1.2.1.1.1.0"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        passed_args = snmp_get.call_args.kwargs["extra_args"]
        self.assertEqual(passed_args["v3_username"], "snmp-reader")
        self.assertNotEqual(passed_args["v3_username"], "root")

    def test_execute_on_scope_uses_requested_command_for_linux_sessions(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "scope_value": "",
            "allow_modifications": False,
        }
        fake_sessions = {
            "sid-linux": {
                "info": {
                    "host": "10.0.0.10",
                    "remark": "linux-a",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "extra_args": {},
                    "tags": [],
                }
            }
        }

        with (
            patch("connections.ssh_manager.ssh_manager.active_sessions", fake_sessions),
            patch("connections.ssh_manager.ssh_manager.execute_command") as execute_command,
        ):
            execute_command.return_value = {"success": True, "output": "up 1 day"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "execute_on_scope",
                    {"scope_target": "ALL", "command": "uptime"},
                    context,
                )
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "BATCH_COMPLETE")
        execute_command.assert_called_once_with("sid-linux", "uptime")

    def test_execute_on_scope_uses_network_cli_for_switch_sessions(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "scope_value": "",
            "allow_modifications": False,
        }
        fake_sessions = {
            "sid-switch": {
                "info": {
                    "host": "192.168.46.30",
                    "remark": "switch-a",
                    "asset_type": "switch",
                    "protocol": "ssh",
                    "extra_args": {"category": "network"},
                    "tags": [],
                }
            }
        }

        with (
            patch("connections.ssh_manager.ssh_manager.active_sessions", fake_sessions),
            patch("connections.ssh_manager.ssh_manager.execute_network_cli_command") as execute_command,
        ):
            execute_command.return_value = {"success": True, "output": "Comware"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "execute_on_scope",
                    {"scope_target": "ALL", "command": "display version"},
                    context,
                )
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "BATCH_COMPLETE")
        execute_command.assert_called_once_with("sid-switch", "display version")

    def test_execute_on_scope_applies_network_hard_block_for_switch_sessions(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "scope_value": "",
            "allow_modifications": True,
        }
        fake_sessions = {
            "sid-switch": {
                "info": {
                    "host": "192.168.46.30",
                    "remark": "switch-a",
                    "asset_type": "switch",
                    "protocol": "ssh",
                    "extra_args": {"category": "network"},
                    "tags": [],
                }
            }
        }

        with (
            patch("connections.ssh_manager.ssh_manager.active_sessions", fake_sessions),
            patch("connections.ssh_manager.ssh_manager.execute_network_cli_command") as execute_command,
        ):
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "execute_on_scope",
                    {"scope_target": "ALL", "command": "reset saved-configuration"},
                    context,
                )
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "BATCH_COMPLETE")
        self.assertIn("硬拦截", json.dumps(payload, ensure_ascii=False))
        execute_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
