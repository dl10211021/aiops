import asyncio
import shutil
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from fastapi import HTTPException

from api import routes


class TestInspectionTemplates(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_inspection_templates_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_inspection_templates_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "templates.json"

    def test_template_crud_masks_disabled_and_persists_updates(self):
        from core import inspection_templates

        store_path = self._store_path("crud")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            created = routes.InspectionTemplatePayload(
                id="linux-basic-custom",
                name="Linux Basic Custom",
                asset_type="linux",
                protocol="ssh",
                enabled=True,
                steps=[
                    {
                        "name": "uptime",
                        "title": "Uptime",
                        "tool": "linux_execute_command",
                        "command": "uptime",
                    }
                ],
            )
            response = asyncio.run(routes.create_inspection_template(created))
            self.assertEqual(response.status, "success")

            listed = asyncio.run(routes.list_inspection_templates())
            custom_templates = [
                template
                for template in listed.data["templates"]
                if template["id"] == "linux-basic-custom"
            ]
            self.assertEqual(len(custom_templates), 1)
            self.assertFalse(custom_templates[0].get("builtin", False))

            updated = routes.InspectionTemplatePayload(
                id="linux-basic-custom",
                name="Linux Basic Custom",
                asset_type="linux",
                protocol="ssh",
                enabled=False,
                steps=[
                    {
                        "name": "identity",
                        "title": "Identity",
                        "tool": "linux_execute_command",
                        "command": "hostname",
                    }
                ],
            )
            response = asyncio.run(routes.update_inspection_template("linux-basic-custom", updated))
            self.assertEqual(response.data["template"]["enabled"], False)

            response = asyncio.run(routes.delete_inspection_template("linux-basic-custom"))
            self.assertEqual(response.status, "success")
            listed = asyncio.run(routes.list_inspection_templates())
            self.assertNotIn(
                "linux-basic-custom",
                {template["id"] for template in listed.data["templates"]},
            )

    def test_builtin_k8s_and_prometheus_templates_are_listed_without_store(self):
        from core import inspection_templates

        store_path = self._store_path("builtins")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            templates = inspection_templates.list_templates()

        by_id = {template["id"]: template for template in templates}
        self.assertIn("builtin-k8s-core-readonly", by_id)
        self.assertIn("builtin-prometheus-core-readonly", by_id)
        self.assertEqual(by_id["builtin-k8s-core-readonly"]["source"], "builtin")
        self.assertTrue(by_id["builtin-k8s-core-readonly"]["builtin"])
        self.assertTrue(by_id["builtin-prometheus-core-readonly"]["readonly"])

    def test_builtin_k8s_and_prometheus_templates_match_read_only_tools(self):
        from core import inspection_templates

        store_path = self._store_path("builtin_match")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            k8s = inspection_templates.find_matching_template("k8s", "k8s")
            prometheus = inspection_templates.find_matching_template("prometheus", "http_api")

        self.assertIsNotNone(k8s)
        self.assertEqual(k8s["id"], "builtin-k8s-core-readonly")
        self.assertEqual({step["tool"] for step in k8s["steps"]}, {"k8s_api_request"})
        self.assertTrue(all(step["method"] == "GET" for step in k8s["steps"]))
        self.assertIn("/api/v1/nodes", {step["path"] for step in k8s["steps"]})

        self.assertIsNotNone(prometheus)
        self.assertEqual(prometheus["id"], "builtin-prometheus-core-readonly")
        self.assertEqual(
            {step["tool"] for step in prometheus["steps"]},
            {"monitoring_api_query"},
        )
        self.assertTrue(all(step["method"] == "GET" for step in prometheus["steps"]))
        self.assertTrue(
            {"cpu_usage", "memory_usage", "disk_usage"}.issubset(
                {step["name"] for step in prometheus["steps"]}
            )
        )
        self.assertIn(
            "/api/v1/query?query=up",
            {step["path"] for step in prometheus["steps"]},
        )

    def test_builtin_windows_and_database_templates_match_deep_readonly_steps(self):
        from core import inspection_templates

        store_path = self._store_path("builtin_windows_db")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            windows = inspection_templates.find_matching_template("windows", "winrm")
            mysql = inspection_templates.find_matching_template("tidb", "mysql")
            postgresql = inspection_templates.find_matching_template("kingbase", "postgresql")
            oracle = inspection_templates.find_matching_template("oracle", "oracle")
            mssql = inspection_templates.find_matching_template("mssql", "mssql")

        self.assertEqual(windows["id"], "builtin-windows-core-readonly")
        self.assertEqual({step["tool"] for step in windows["steps"]}, {"winrm_execute_command"})
        self.assertTrue(
            {"os", "disk", "services", "events", "hotfixes"}.issubset(
                {step["name"] for step in windows["steps"]}
            )
        )

        self.assertEqual(mysql["id"], "builtin-mysql-core-readonly")
        self.assertEqual(postgresql["id"], "builtin-postgresql-core-readonly")
        self.assertEqual(oracle["id"], "builtin-oracle-core-readonly")
        self.assertEqual(mssql["id"], "builtin-mssql-core-readonly")
        for template in (mysql, postgresql, oracle, mssql):
            self.assertEqual({step["tool"] for step in template["steps"]}, {"db_execute_query"})
            self.assertTrue({"version", "connections"}.issubset({step["name"] for step in template["steps"]}))

    def test_builtin_network_snmp_virtualization_and_redfish_templates_match(self):
        from core import inspection_templates

        store_path = self._store_path("builtin_network_virtualization")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            network = inspection_templates.find_matching_template("firewall", "ssh")
            snmp = inspection_templates.find_matching_template("nas", "snmp")
            vmware = inspection_templates.find_matching_template("vmware", "http_api")
            proxmox = inspection_templates.find_matching_template("proxmox", "http_api")
            kvm = inspection_templates.find_matching_template("kvm", "ssh")
            redfish = inspection_templates.find_matching_template("redfish", "redfish")

        self.assertEqual(network["id"], "builtin-network-cli-core-readonly")
        self.assertEqual({step["tool"] for step in network["steps"]}, {"network_cli_execute_command"})
        self.assertTrue(
            {"version", "interfaces", "interface_errors", "neighbors"}.issubset(
                {step["name"] for step in network["steps"]}
            )
        )

        self.assertEqual(snmp["id"], "builtin-snmp-core-readonly")
        self.assertEqual({step["tool"] for step in snmp["steps"]}, {"snmp_get"})
        self.assertIn("1.3.6.1.2.1.1.1.0", {step["oid"] for step in snmp["steps"]})

        self.assertEqual(vmware["id"], "builtin-vmware-core-readonly")
        self.assertEqual(proxmox["id"], "builtin-proxmox-core-readonly")
        self.assertEqual(kvm["id"], "builtin-kvm-core-readonly")
        self.assertEqual(redfish["id"], "builtin-redfish-core-readonly")
        self.assertEqual({step["tool"] for step in vmware["steps"]}, {"virtualization_api_request"})
        self.assertEqual({step["tool"] for step in proxmox["steps"]}, {"virtualization_api_request"})
        self.assertEqual({step["tool"] for step in kvm["steps"]}, {"linux_execute_command"})
        self.assertEqual({step["tool"] for step in redfish["steps"]}, {"http_api_request"})

    def test_template_validation_rejects_unsafe_step(self):
        from core import inspection_templates

        store_path = self._store_path("unsafe")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            payload = routes.InspectionTemplatePayload(
                id="unsafe",
                name="Unsafe",
                asset_type="linux",
                protocol="ssh",
                enabled=True,
                steps=[
                    {
                        "name": "restart",
                        "title": "Restart",
                        "tool": "linux_execute_command",
                        "command": "systemctl restart nginx",
                    }
                ],
            )
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.create_inspection_template(payload))

        self.assertEqual(ctx.exception.status_code, 422)

    def test_inspector_uses_enabled_custom_template_for_linux(self):
        from core import inspection_templates, session_inspector

        fake_sessions = {
            "sid-linux": {
                "info": {
                    "host": "10.0.0.10",
                    "port": 22,
                    "username": "root",
                    "password": "secret",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "extra_args": {"sub_type": "linux"},
                }
            }
        }

        class FakeSSH:
            active_sessions = fake_sessions

            def execute_command(self, session_id, command, timeout=None):
                return {
                    "success": True,
                    "has_error": False,
                    "output": f"ran:{command}",
                    "exit_status": 0,
                }

        store_path = self._store_path("inspector")
        with (
            patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path),
            patch.object(session_inspector, "ssh_manager", FakeSSH()),
        ):
            inspection_templates.save_template(
                {
                    "id": "linux-custom",
                    "name": "Linux Custom",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "enabled": True,
                    "steps": [
                        {
                            "name": "custom_hostname",
                            "title": "Custom Hostname",
                            "tool": "linux_execute_command",
                            "command": "hostname",
                            "timeout": 5,
                        }
                    ],
                }
            )

            report = asyncio.run(session_inspector.inspect_session("sid-linux"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["checks"][0]["command"], "hostname")
        self.assertEqual(report["checks"][0]["output"], "ran:hostname")

    def test_inspector_uses_builtin_k8s_template_for_k8s_session(self):
        from core import inspection_templates, session_inspector
        from connections import http_api_manager

        fake_sessions = {
            "sid-k8s": {
                "info": {
                    "host": "k8s.local",
                    "port": 6443,
                    "username": "admin",
                    "password": "secret",
                    "asset_type": "k8s",
                    "protocol": "k8s",
                    "extra_args": {"bearer_token": "secret"},
                }
            }
        }

        class FakeSSH:
            active_sessions = fake_sessions

        class FakeHttpApiExecutor:
            def __init__(self):
                self.calls = []

            def request(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "output": kwargs["path"], "exit_status": 200}

        fake_http = FakeHttpApiExecutor()
        store_path = self._store_path("builtin_k8s_inspector")
        with (
            patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path),
            patch.object(session_inspector, "ssh_manager", FakeSSH()),
            patch.object(http_api_manager, "http_api_executor", fake_http),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid-k8s"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-k8s-core-readonly")
        self.assertIn("/api/v1/nodes", {call["path"] for call in fake_http.calls})
        self.assertEqual({call["asset_type"] for call in fake_http.calls}, {"k8s"})
        self.assertEqual({call["method"] for call in fake_http.calls}, {"GET"})

    def test_inspector_uses_builtin_prometheus_template_for_monitoring_session(self):
        from core import inspection_templates, session_inspector
        from connections import http_api_manager

        fake_sessions = {
            "sid-prometheus": {
                "info": {
                    "host": "prometheus.local",
                    "port": 9090,
                    "username": "",
                    "password": "",
                    "asset_type": "prometheus",
                    "protocol": "http_api",
                    "extra_args": {},
                }
            }
        }

        class FakeSSH:
            active_sessions = fake_sessions

        class FakeHttpApiExecutor:
            def __init__(self):
                self.calls = []

            def request(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "output": kwargs["path"], "exit_status": 200}

        fake_http = FakeHttpApiExecutor()
        store_path = self._store_path("builtin_prometheus_inspector")
        with (
            patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path),
            patch.object(session_inspector, "ssh_manager", FakeSSH()),
            patch.object(http_api_manager, "http_api_executor", fake_http),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid-prometheus"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-prometheus-core-readonly")
        self.assertIn(
            "/api/v1/query?query=up",
            {call["path"] for call in fake_http.calls},
        )
        self.assertEqual({call["asset_type"] for call in fake_http.calls}, {"prometheus"})
        self.assertEqual({call["method"] for call in fake_http.calls}, {"GET"})

    def test_inspector_uses_builtin_windows_template_for_winrm_session(self):
        from core import inspection_templates, session_inspector
        from connections import winrm_manager

        fake_sessions = {
            "sid-windows": {
                "info": {
                    "host": "windows.local",
                    "port": 5985,
                    "username": "administrator",
                    "password": "secret",
                    "asset_type": "windows",
                    "protocol": "winrm",
                    "extra_args": {},
                }
            }
        }

        class FakeSSH:
            active_sessions = fake_sessions

        class FakeWinrmExecutor:
            def __init__(self):
                self.calls = []

            def execute_command(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "output": kwargs["command"], "exit_status": 0}

        fake_winrm = FakeWinrmExecutor()
        store_path = self._store_path("builtin_windows_inspector")
        with (
            patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path),
            patch.object(session_inspector, "ssh_manager", FakeSSH()),
            patch.object(winrm_manager, "winrm_executor", fake_winrm),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid-windows"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-windows-core-readonly")
        self.assertTrue(any("Get-HotFix" in call["command"] for call in fake_winrm.calls))

    def test_inspector_uses_builtin_mysql_template_for_mysql_protocol_subtypes(self):
        from core import inspection_templates, session_inspector
        from connections import db_manager

        fake_sessions = {
            "sid-tidb": {
                "info": {
                    "host": "tidb.local",
                    "port": 4000,
                    "username": "ops",
                    "password": "secret",
                    "asset_type": "tidb",
                    "protocol": "mysql",
                    "extra_args": {"database": "test"},
                }
            }
        }

        class FakeSSH:
            active_sessions = fake_sessions

        class FakeDbExecutor:
            def __init__(self):
                self.calls = []

            def execute_query(self, db_type, host, port, user, password, database, sql, extra_args=None):
                self.calls.append(
                    {
                        "db_type": db_type,
                        "host": host,
                        "port": port,
                        "user": user,
                        "password": password,
                        "database": database,
                        "sql": sql,
                        "extra_args": extra_args,
                    }
                )
                return '{"success": true, "data": []}'

        fake_db = FakeDbExecutor()
        store_path = self._store_path("builtin_mysql_inspector")
        with (
            patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path),
            patch.object(session_inspector, "ssh_manager", FakeSSH()),
            patch.object(db_manager, "db_executor", fake_db),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid-tidb"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-mysql-core-readonly")
        self.assertEqual({call["db_type"] for call in fake_db.calls}, {"mysql"})
        self.assertTrue(any("Threads_connected" in call["sql"] for call in fake_db.calls))

    def test_inspector_uses_builtin_network_template_for_network_cli_subtypes(self):
        from core import inspection_templates, session_inspector

        fake_sessions = {
            "sid-firewall": {
                "info": {
                    "host": "firewall.local",
                    "port": 22,
                    "username": "admin",
                    "password": "secret",
                    "asset_type": "firewall",
                    "protocol": "ssh",
                    "extra_args": {},
                }
            }
        }

        class FakeSSH:
            active_sessions = fake_sessions

            def __init__(self):
                self.commands = []

            def execute_network_cli_command(self, session_id, command, timeout=None):
                self.commands.append(command)
                return {"success": True, "output": command, "exit_status": 0}

        fake_ssh = FakeSSH()
        store_path = self._store_path("builtin_network_inspector")
        with (
            patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path),
            patch.object(session_inspector, "ssh_manager", fake_ssh),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid-firewall"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-network-cli-core-readonly")
        self.assertTrue(any("lldp" in command.lower() for command in fake_ssh.commands))


if __name__ == "__main__":
    unittest.main()
