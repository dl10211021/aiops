import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.connection_test_service import run_connection_test


def request(**overrides):
    base = {
        "host": "db.local",
        "port": 3306,
        "username": "ops",
        "password": None,
        "private_key_path": None,
        "asset_type": "mysql",
        "protocol": "mysql",
        "extra_args": {"db_type": "mysql", "database": "ops"},
        "remark": "",
        "target_scope": "asset",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeSocket:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestConnectionTestService(unittest.TestCase):
    def test_global_scope_returns_success_without_probe(self):
        result = asyncio.run(
            run_connection_test(
                request(target_scope="global", asset_type="virtual", protocol="virtual"),
                restored_password=None,
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("全局", result["message"])

    def test_sql_success_uses_database_operation_profile(self):
        with (
            patch("connections.db_manager.get_database_operation_profile", return_value={"test_statement": "SELECT 42"}),
            patch(
                "connections.db_manager.db_executor.execute_query",
                return_value=json.dumps({"success": True}),
            ) as execute_query,
        ):
            result = asyncio.run(run_connection_test(request(), restored_password="secret"))

        self.assertEqual(result["status"], "success")
        self.assertIn("MYSQL", result["message"])
        args = execute_query.call_args.args
        self.assertEqual(args[:7], ("mysql", "db.local", 3306, "ops", "secret", "ops", "SELECT 42"))

    def test_sql_error_returns_normalized_error_payload(self):
        with (
            patch("connections.db_manager.get_database_operation_profile", return_value={"test_statement": "SELECT 1"}),
            patch(
                "connections.db_manager.db_executor.execute_query",
                return_value=json.dumps({"success": False, "error": "Access denied for user"}),
            ),
        ):
            result = asyncio.run(run_connection_test(request(), restored_password="bad-secret"))

        self.assertEqual(result["status"], "error")
        self.assertIn("error", result["data"])
        self.assertEqual(result["data"]["error"]["protocol"], "mysql")

    def test_http_api_success_checks_resolved_base_url_port(self):
        req = request(
            host="api.local",
            port=443,
            asset_type="prometheus",
            protocol="http_api",
            extra_args={"scheme": "https", "base_path": "/api"},
        )

        with patch("socket.create_connection", return_value=FakeSocket()) as create_connection:
            result = asyncio.run(run_connection_test(req, restored_password=None))

        self.assertEqual(result["status"], "success")
        create_connection.assert_called_once()
        self.assertEqual(create_connection.call_args.args[0][0], "api.local")
        self.assertEqual(create_connection.call_args.args[0][1], 443)

    def test_virtual_ping_failure_is_non_blocking_warning(self):
        completed = SimpleNamespace(returncode=1)
        req = request(asset_type="unknown", protocol="virtual", extra_args={}, host="198.51.100.10")

        with patch("subprocess.run", return_value=completed):
            result = asyncio.run(run_connection_test(req, restored_password=None))

        self.assertEqual(result["status"], "success")
        self.assertIn("Virtual credentials saved", result["message"])


if __name__ == "__main__":
    unittest.main()
