import asyncio
import unittest
from types import SimpleNamespace

from core.connection_inspection_service import (
    inspect_connection_request,
    inspect_connection_session,
)


class FakeSSHManager:
    def __init__(self, connect_result=None):
        self.connect_result = connect_result or {"success": True, "session_id": "sid-inspect"}
        self.connect_calls = []
        self.disconnect_calls = []

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)
        return self.connect_result

    def disconnect(self, session_id):
        self.disconnect_calls.append(session_id)


def request(**overrides):
    base = {
        "host": "db.local",
        "port": 3306,
        "username": "ops",
        "private_key_path": "string",
        "active_skills": [],
        "agent_profile": "default",
        "remark": "",
        "asset_type": "mysql",
        "protocol": "mysql",
        "extra_args": {"db_type": "mysql", "database": "ops"},
        "tags": ["数据库"],
        "target_scope": "asset",
        "scope_value": None,
        "keep_session": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


async def successful_inspector(session_id):
    return {
        "status": "warning",
        "summary": f"inspected {session_id}",
        "checks": [],
    }


class TestConnectionInspectionService(unittest.TestCase):
    def test_global_scope_returns_supported_virtual_report(self):
        result = asyncio.run(
            inspect_connection_session(
                request(target_scope="global", asset_type="virtual", protocol="virtual"),
                FakeSSHManager(),
                successful_inspector,
                restored_password=None,
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["inspection"]["profile"], "global")

    def test_inspects_temporary_session_and_disconnects_by_default(self):
        ssh_manager = FakeSSHManager()

        result = asyncio.run(
            inspect_connection_session(
                request(),
                ssh_manager,
                successful_inspector,
                restored_password="secret",
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "inspected sid-inspect")
        self.assertIsNone(result["data"]["session_id"])
        self.assertEqual(ssh_manager.connect_calls[0]["password"], "secret")
        self.assertEqual(ssh_manager.connect_calls[0]["key_filename"], None)
        self.assertEqual(ssh_manager.disconnect_calls, ["sid-inspect"])

    def test_keep_session_returns_session_id_without_disconnect(self):
        ssh_manager = FakeSSHManager()

        result = asyncio.run(
            inspect_connection_session(
                request(keep_session=True),
                ssh_manager,
                successful_inspector,
                restored_password="secret",
            )
        )

        self.assertEqual(result["data"]["session_id"], "sid-inspect")
        self.assertTrue(result["data"]["kept_session"])
        self.assertEqual(ssh_manager.disconnect_calls, [])

    def test_connection_failure_returns_error_payload(self):
        ssh_manager = FakeSSHManager(
            {
                "success": False,
                "error_code": "AUTH_FAILED",
                "error_category": "auth",
                "message": "认证失败",
                "raw_error": "denied",
            }
        )

        result = asyncio.run(
            inspect_connection_session(
                request(),
                ssh_manager,
                successful_inspector,
                restored_password="bad-secret",
            )
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["error"]["code"], "AUTH_FAILED")
        self.assertEqual(result["data"]["error"]["protocol"], "mysql")

    def test_inspect_connection_request_uses_injected_manager_and_inspector(self):
        ssh_manager = FakeSSHManager()

        result = asyncio.run(
            inspect_connection_request(
                request(),
                restored_password="secret",
                ssh_manager=ssh_manager,
                inspector=successful_inspector,
            )
        )

        self.assertEqual(result["message"], "inspected sid-inspect")
        self.assertEqual(ssh_manager.connect_calls[0]["password"], "secret")
        self.assertEqual(ssh_manager.disconnect_calls, ["sid-inspect"])


if __name__ == "__main__":
    unittest.main()
