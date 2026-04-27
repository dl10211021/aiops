import asyncio
import json
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

from api import routes


class FakeMemoryDB:
    def get_all_assets(self):
        return [
            {
                "id": 1,
                "remark": "linux-prod",
                "host": "10.0.0.10",
                "port": 22,
                "username": "root",
                "password": "managed-secret",
                "asset_type": "linux",
                "protocol": "ssh",
                "agent_profile": "default",
                "extra_args": {"category": "os", "api_key": "secret-key"},
                "skills": [],
                "tags": ["prod"],
            },
            {
                "id": 2,
                "remark": "mysql-prod",
                "host": "10.0.0.20",
                "port": 3306,
                "username": "mysql",
                "password": "db-secret",
                "asset_type": "mysql",
                "protocol": "mysql",
                "agent_profile": "default",
                "extra_args": {"category": "db", "database": "ops"},
                "skills": [],
                "tags": ["prod", "db"],
            },
        ]

    def get_asset(self, asset_id: int):
        for asset in self.get_all_assets():
            if asset["id"] == asset_id:
                return asset
        return None


class TestProtocolVerificationMatrix(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_protocol_verification_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _run_store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_protocol_verification_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "runs.json"

    def test_asset_verification_matrix_is_protocol_aware_and_secret_free(self):
        from core import memory

        with patch.object(memory, "memory_db", FakeMemoryDB()):
            response = asyncio.run(routes.get_asset_verification_matrix(2))

        self.assertEqual(response.status, "success")
        matrix = response.data["matrix"]
        self.assertEqual(matrix["asset"]["id"], 2)
        self.assertEqual(matrix["asset"]["asset_type"], "mysql")
        self.assertEqual(matrix["asset"]["protocol"], "mysql")
        step_ids = [step["id"] for step in matrix["steps"]]
        self.assertIn("connection_test", step_ids)
        self.assertIn("protocol_probe", step_ids)
        self.assertIn("tool_catalog", step_ids)
        self.assertIn("readonly_inspection", step_ids)
        self.assertIn("scheduled_inspection", step_ids)
        self.assertIn("db_execute_query", matrix["active_tools"])
        dumped = json.dumps(response.data, ensure_ascii=False)
        self.assertNotIn("db-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_protocol_verification_overview_groups_assets_and_gaps(self):
        from core import memory

        with patch.object(memory, "memory_db", FakeMemoryDB()):
            response = asyncio.run(routes.get_protocol_verification_overview())

        self.assertEqual(response.status, "success")
        summary = response.data["summary"]
        self.assertEqual(summary["asset_total"], 2)
        self.assertEqual(summary["protocols"]["ssh"], 1)
        self.assertEqual(summary["protocols"]["mysql"], 1)
        self.assertGreaterEqual(summary["steps_total"], 8)
        self.assertIn("matrix", response.data)
        dumped = json.dumps(response.data, ensure_ascii=False)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_asset_verify_executes_readonly_steps_and_persists_history(self):
        from core import memory
        from core import protocol_verification

        with (
            patch.object(memory, "memory_db", FakeMemoryDB()),
            patch.object(protocol_verification, "VERIFICATION_RUN_STORE_PATH", self._run_store_path("runner")),
            patch("connections.ssh_manager.ssh_manager.connect") as connect,
            patch("connections.ssh_manager.ssh_manager.disconnect") as disconnect,
            patch.object(protocol_verification, "run_protocol_probe") as protocol_probe,
            patch("core.session_inspector.inspect_session") as inspect_session,
        ):
            connect.return_value = {"success": True, "session_id": "verify-session", "message": "ok"}
            protocol_probe.return_value = {
                "status": "success",
                "message": "native ok",
                "details": {"tool": "db_execute_query"},
            }
            inspect_session.return_value = {
                "status": "success",
                "supported": True,
                "summary": "ok",
                "checks": [{"name": "sql_ping", "status": "success"}],
            }
            response = asyncio.run(routes.verify_asset(2))
            history = asyncio.run(routes.list_asset_verification_runs(2))

        self.assertEqual(response.status, "success")
        run = response.data["run"]
        self.assertEqual(run["asset"]["id"], 2)
        self.assertEqual(run["status"], "success")
        self.assertEqual([step["id"] for step in run["steps"]], [
            "connection_test",
            "protocol_probe",
            "tool_catalog",
            "readonly_inspection",
            "scheduled_inspection",
        ])
        self.assertTrue(all(step["status"] == "success" for step in run["steps"]))
        self.assertEqual(history.data["runs"][0]["id"], run["id"])
        connect.assert_called_once()
        disconnect.assert_called_once_with("verify-session")
        dumped = json.dumps(response.data, ensure_ascii=False)
        self.assertNotIn("db-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_asset_verify_records_connection_failure_without_inspection(self):
        from core import memory
        from core import protocol_verification

        with (
            patch.object(memory, "memory_db", FakeMemoryDB()),
            patch.object(protocol_verification, "VERIFICATION_RUN_STORE_PATH", self._run_store_path("failed")),
            patch("connections.ssh_manager.ssh_manager.connect") as connect,
            patch("core.session_inspector.inspect_session") as inspect_session,
        ):
            connect.return_value = {"success": False, "message": "auth failed"}
            response = asyncio.run(routes.verify_asset(1))

        run = response.data["run"]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["steps"][0]["status"], "error")
        self.assertEqual(run["steps"][1]["id"], "protocol_probe")
        self.assertEqual(run["steps"][1]["status"], "skipped")
        self.assertEqual(run["steps"][3]["id"], "readonly_inspection")
        self.assertEqual(run["steps"][3]["status"], "skipped")
        inspect_session.assert_not_called()

    def test_asset_verify_skips_inspection_when_protocol_probe_fails(self):
        from core import memory
        from core import protocol_verification

        with (
            patch.object(memory, "memory_db", FakeMemoryDB()),
            patch.object(protocol_verification, "VERIFICATION_RUN_STORE_PATH", self._run_store_path("probe_failed")),
            patch("connections.ssh_manager.ssh_manager.connect") as connect,
            patch("connections.ssh_manager.ssh_manager.disconnect") as disconnect,
            patch.object(protocol_verification, "run_protocol_probe") as protocol_probe,
            patch("core.session_inspector.inspect_session") as inspect_session,
        ):
            connect.return_value = {"success": True, "session_id": "verify-session", "message": "registered"}
            protocol_probe.return_value = {
                "status": "error",
                "message": "native probe failed",
                "details": {"tool": "db_execute_query"},
            }
            response = asyncio.run(routes.verify_asset(2))

        run = response.data["run"]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["steps"][1]["id"], "protocol_probe")
        self.assertEqual(run["steps"][1]["status"], "error")
        self.assertEqual(run["steps"][3]["id"], "readonly_inspection")
        self.assertEqual(run["steps"][3]["status"], "skipped")
        inspect_session.assert_not_called()
        disconnect.assert_called_once_with("verify-session")

    def test_mysql_verify_uses_native_database_probe(self):
        from core import protocol_verification

        asset = FakeMemoryDB().get_asset(2)
        with patch("connections.db_manager.db_executor.execute_query") as execute_query:
            execute_query.return_value = '{"success": true, "data": [{"ok": 1}]}'
            result = asyncio.run(protocol_verification.run_protocol_probe(asset))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["tool"], "db_execute_query")
        execute_query.assert_called_once()

    def test_ssh_probe_is_covered_by_physical_connection(self):
        from core import protocol_verification

        asset = FakeMemoryDB().get_asset(1)
        result = asyncio.run(protocol_verification.run_protocol_probe(asset))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["tool"], "ssh_connect")

    def test_windows_verify_uses_native_winrm_probe(self):
        from core import protocol_verification

        asset = {
            "id": 3,
            "remark": "win-prod",
            "host": "10.0.0.30",
            "port": 5985,
            "username": "Administrator",
            "password": "win-secret",
            "asset_type": "windows",
            "protocol": "winrm",
            "extra_args": {},
        }
        with patch("connections.winrm_manager.winrm_executor.execute_command") as execute_command:
            execute_command.return_value = {"success": True, "output": "ok", "exit_status": 0}
            result = asyncio.run(protocol_verification.run_protocol_probe(asset))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["tool"], "winrm_execute_command")
        execute_command.assert_called_once()

    def test_snmp_verify_uses_native_snmp_probe(self):
        from core import protocol_verification

        asset = {
            "id": 4,
            "remark": "switch-snmp",
            "host": "10.0.0.40",
            "port": 161,
            "username": "",
            "password": "",
            "asset_type": "snmp",
            "protocol": "snmp",
            "extra_args": {"community_string": "public"},
        }
        with patch("connections.snmp_manager.snmp_executor.get") as snmp_get:
            snmp_get.return_value = {"success": True, "data": [{"oid": "1.3", "value": "ok"}]}
            result = asyncio.run(protocol_verification.run_protocol_probe(asset))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["tool"], "snmp_get")
        snmp_get.assert_called_once()

    def test_http_verify_uses_native_http_probe(self):
        from core import protocol_verification

        asset = {
            "id": 5,
            "remark": "prometheus",
            "host": "10.0.0.50",
            "port": 9090,
            "username": "",
            "password": "",
            "asset_type": "prometheus",
            "protocol": "http_api",
            "extra_args": {},
        }
        with patch("connections.http_api_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "status_code": 200, "output": "ok"}
            result = asyncio.run(protocol_verification.run_protocol_probe(asset))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["tool"], "monitoring_api_query")
        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
