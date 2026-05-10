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

    def test_hyperv_session_exposes_winrm_not_virtualization_api(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "hyperv",
                "protocol": "winrm",
                "extra_args": {"category": "virtualization"},
            }
        )

        names = tool_names(tools)
        self.assertIn("winrm_execute_command", names)
        self.assertNotIn("virtualization_api_request", names)
        self.assertNotIn("linux_execute_command", names)

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

    def test_monitoring_session_exposes_monitoring_tool_not_generic_http(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "extra_args": {},
            }
        )

        names = tool_names(tools)
        self.assertIn("monitoring_api_query", names)
        self.assertNotIn("http_api_request", names)

    def test_firewall_http_api_session_exposes_network_api_not_cli(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "firewall",
                "protocol": "http_api",
                "extra_args": {"category": "network", "sub_type": "firewall"},
            }
        )

        names = tool_names(tools)
        self.assertIn("network_api_request", names)
        self.assertNotIn("http_api_request", names)
        self.assertNotIn("network_cli_execute_command", names)

    def test_bigdata_api_request_routes_through_managed_http_executor(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "asset_type": "airflow",
            "protocol": "http_api",
            "host": "airflow.local",
            "port": 8080,
            "username": "managed-user",
            "password": "managed-secret",
            "extra_args": {"category": "bigdata", "sub_type": "airflow"},
            "allow_modifications": False,
        }

        with patch("connections.http_api_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "data": {"health": "ok"}}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "bigdata_api_request",
                    {"path": "/health", "method": "GET"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        request.assert_called_once_with(
            asset_type="airflow",
            host="airflow.local",
            port=8080,
            username="managed-user",
            password="managed-secret",
            extra_args={"category": "bigdata", "sub_type": "airflow"},
            method="GET",
            path="/health",
            headers={},
            body=None,
        )

    def test_switch_session_exposes_network_cli_not_linux_tool(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)

        for asset_type in ("switch", "h3c_switch", "huawei_switch"):
            with self.subTest(asset_type=asset_type):
                tools = dispatcher.get_available_tools(
                    {
                        "target_scope": "asset",
                        "asset_type": asset_type,
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

        for asset_type in ("switch", "h3c_switch"):
            with self.subTest(asset_type=asset_type):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "linux_execute_command",
                        {"command": "uname -a"},
                        {
                            "session_id": "sid",
                            "asset_type": asset_type,
                            "protocol": "ssh",
                            "extra_args": {"category": "network"},
                            "allow_modifications": False,
                        },
                    )
                )

                payload = json.loads(result)
                self.assertEqual(payload["status"], "ERROR")
                self.assertIn("network_cli_execute_command", payload["error"])

    def test_storage_session_exposes_storage_command_not_linux_tool(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)

        for asset_type in ("ceph", "nas", "synology_nas"):
            with self.subTest(asset_type=asset_type):
                tools = dispatcher.get_available_tools(
                    {
                        "target_scope": "asset",
                        "asset_type": asset_type,
                        "protocol": "ssh",
                        "extra_args": {"category": "storage"},
                    }
                )

                names = tool_names(tools)
                self.assertIn("storage_execute_command", names)
                self.assertNotIn("linux_execute_command", names)
                self.assertNotIn("local_execute_script", names)

    def test_storage_session_rejects_linux_command_even_if_model_calls_it(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)

        for asset_type in ("ceph", "nas", "synology_nas"):
            with self.subTest(asset_type=asset_type):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "linux_execute_command",
                        {"command": "df -h"},
                        {
                            "session_id": "sid",
                            "asset_type": asset_type,
                            "protocol": "ssh",
                            "extra_args": {"category": "storage"},
                            "allow_modifications": False,
                        },
                    )
                )

                payload = json.loads(result)
                self.assertEqual(payload["status"], "ERROR")
                self.assertIn("storage_execute_command", payload["error"])

    def test_middleware_session_exposes_middleware_command_not_linux_tool(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)

        for asset_type in ("nginx", "kafka", "process"):
            with self.subTest(asset_type=asset_type):
                tools = dispatcher.get_available_tools(
                    {
                        "target_scope": "asset",
                        "asset_type": asset_type,
                        "protocol": "ssh",
                        "extra_args": {"category": "middleware"},
                    }
                )

                names = tool_names(tools)
                self.assertIn("middleware_execute_command", names)
                self.assertNotIn("linux_execute_command", names)
                self.assertNotIn("local_execute_script", names)

    def test_middleware_session_rejects_linux_command_even_if_model_calls_it(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)

        for asset_type in ("kafka", "process"):
            with self.subTest(asset_type=asset_type):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "linux_execute_command",
                        {"command": "ps -ef | head"},
                        {
                            "session_id": "sid",
                            "asset_type": asset_type,
                            "protocol": "ssh",
                            "extra_args": {"category": "middleware"},
                            "allow_modifications": False,
                        },
                    )
                )

                payload = json.loads(result)
                self.assertEqual(payload["status"], "ERROR")
                self.assertIn("middleware_execute_command", payload["error"])

    def test_legacy_storage_asset_without_catalog_definition_stays_protected(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        tools = dispatcher.get_available_tools(
            {
                "target_scope": "asset",
                "asset_type": "glusterfs",
                "protocol": "ssh",
                "extra_args": {"category": "storage"},
            }
        )

        names = tool_names(tools)
        self.assertIn("storage_execute_command", names)
        self.assertNotIn("linux_execute_command", names)

    def test_legacy_storage_rejects_linux_command_even_if_model_calls_it(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        result = asyncio.run(
            dispatcher.route_and_execute(
                "linux_execute_command",
                {"command": "gluster volume status"},
                {
                    "session_id": "sid",
                    "asset_type": "glusterfs",
                    "protocol": "ssh",
                    "extra_args": {"category": "storage"},
                    "allow_modifications": False,
                },
            )
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("storage_execute_command", payload["error"])

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

    def test_jdbc_database_query_uses_managed_session_credentials(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "asset_type": "dameng",
            "protocol": "dameng",
            "host": "dm.local",
            "port": 5236,
            "username": "SYSDBA",
            "password": "managed_secret",
            "extra_args": {"db_name": "TEST", "db_type": "dameng", "jdbc_jar": "D:/AIOPS/jdbc_drivers/dameng/DmJdbcDriver18.jar"},
            "allow_modifications": False,
        }

        with patch("connections.db_manager.db_executor.execute_query") as execute_query:
            execute_query.return_value = json.dumps({"success": True, "data": []})
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "db_execute_query",
                    {"sql": "SELECT 1", "user": "bad", "password": "bad"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_query.assert_called_once_with(
            "dameng",
            "dm.local",
            5236,
            "SYSDBA",
            "managed_secret",
            "TEST",
            "SELECT 1",
            {"db_name": "TEST", "db_type": "dameng", "jdbc_jar": "D:/AIOPS/jdbc_drivers/dameng/DmJdbcDriver18.jar"},
        )

    def test_memcached_command_uses_managed_session_target(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "asset_type": "memcached",
            "protocol": "memcached",
            "host": "cache.local",
            "port": 11211,
            "username": "ignored",
            "password": "ignored",
            "extra_args": {"category": "db"},
            "allow_modifications": False,
        }

        with patch("connections.datastore_manager.memcached_executor.execute_command") as execute_command:
            execute_command.return_value = {"success": True, "output": "VERSION 1.6.22"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "memcached_execute_command",
                    {"command": "version", "host": "attacker"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_command.assert_called_once_with(
            host="cache.local",
            port=11211,
            command="version",
            extra_args={"category": "db"},
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

    def test_winrm_dispatch_preserves_powershell_script_syntax(self):
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
        command = (
            "Get-Service | Where-Object {$_.Status -ne 'Running'} | "
            "Select-Object Name,Status,@{Name='Display';Expression={$_.DisplayName}}"
        )

        with patch("connections.winrm_manager.winrm_executor.execute_command") as execute_command:
            execute_command.return_value = {"success": True, "output": "ok"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "winrm_execute_command",
                    {"command": command},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_command.assert_called_once_with(
            host="win.local",
            port=5985,
            username="managed_user",
            password="managed_secret",
            command=command,
            extra_args={},
        )

    def test_hyperv_rejects_virtualization_api_tool_name(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        result = asyncio.run(
            dispatcher.route_and_execute(
                "virtualization_api_request",
                {"operation": "vms"},
                {
                    "asset_type": "hyperv",
                    "protocol": "winrm",
                    "host": "hyperv.local",
                    "port": 5985,
                    "username": "managed_user",
                    "password": "managed_secret",
                    "extra_args": {"category": "virtualization"},
                    "allow_modifications": False,
                },
            )
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("winrm_execute_command", payload["error"])

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

    def test_storage_command_uses_managed_session(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "session_id": "managed-storage-session",
            "asset_type": "ceph",
            "protocol": "ssh",
            "extra_args": {"category": "storage"},
            "allow_modifications": False,
        }

        with patch("connections.ssh_manager.ssh_manager.execute_command") as execute_command:
            execute_command.return_value = {"success": True, "output": "HEALTH_OK"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "storage_execute_command",
                    {"command": "ceph status"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute_command.assert_called_once_with("managed-storage-session", "ceph status")

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

    def test_s3_storage_request_uses_object_storage_adapter(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "asset_type": "s3",
            "protocol": "http_api",
            "host": "s3.local",
            "port": 443,
            "username": "managed-ak",
            "password": "managed-sk",
            "extra_args": {"bucket": "ops-logs", "category": "storage", "sub_type": "s3"},
            "allow_modifications": False,
        }

        with patch("connections.object_storage_manager.object_storage_executor.execute") as execute:
            execute.return_value = {"success": True, "objects": []}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "storage_api_request",
                    {"operation": "list_objects", "bucket": "bad-bucket"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute.assert_called_once_with(
            asset_type="s3",
            host="s3.local",
            port=443,
            username="managed-ak",
            password="managed-sk",
            extra_args={"bucket": "ops-logs", "category": "storage", "sub_type": "s3"},
            operation="list_objects",
            bucket="bad-bucket",
            prefix=None,
            key=None,
            max_keys=None,
        )

    def test_backup_storage_request_uses_storage_platform_adapter(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        context = {
            "asset_type": "backup",
            "protocol": "backup",
            "host": "backup.local",
            "port": 443,
            "username": "managed-user",
            "password": "managed-secret",
            "extra_args": {"category": "storage", "jobs_path": "/api/jobs"},
            "allow_modifications": False,
        }

        with patch("connections.storage_platform_manager.storage_platform_executor.execute") as execute:
            execute.return_value = {"success": True, "output": "jobs"}
            result = asyncio.run(
                dispatcher.route_and_execute(
                    "storage_api_request",
                    {"operation": "jobs", "path": "/ignored"},
                    context,
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        execute.assert_called_once_with(
            asset_type="backup",
            host="backup.local",
            port=443,
            username="managed-user",
            password="managed-secret",
            extra_args={"category": "storage", "jobs_path": "/api/jobs"},
            operation="jobs",
            method="GET",
            path="/ignored",
            headers={},
            body=None,
            timeout=None,
        )

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
