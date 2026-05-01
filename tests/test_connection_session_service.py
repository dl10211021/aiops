import asyncio
import unittest
from types import SimpleNamespace

from core.connection_session_service import (
    ConnectionSessionServiceError,
    create_connection_session,
)


class FakeSSHManager:
    def __init__(self, connect_result=None, local_result=None):
        self.connect_result = connect_result or {"success": True, "session_id": "sid-asset"}
        self.local_result = local_result or {"success": True, "session_id": "sid-global"}
        self.connect_calls = []
        self.local_calls = []

    def connect_local(self, **kwargs):
        self.local_calls.append(kwargs)
        return self.local_result

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)
        return self.connect_result


class FakeMemoryDB:
    def __init__(self):
        self.saved_assets = []

    def save_asset(self, **kwargs):
        self.saved_assets.append(kwargs)


def request(**overrides):
    base = {
        "host": "db.local",
        "port": 3306,
        "username": "ops",
        "private_key_path": "string",
        "allow_modifications": False,
        "active_skills": ["mysql-skill"],
        "agent_profile": "default",
        "remark": "核心库",
        "asset_type": "mysql",
        "protocol": "mysql",
        "extra_args": {"db_type": "mysql", "database": "ops"},
        "tags": ["数据库"],
        "target_scope": "asset",
        "scope_value": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestConnectionSessionService(unittest.TestCase):
    def test_global_scope_creates_local_orchestration_session(self):
        ssh_manager = FakeSSHManager()
        memory_db = FakeMemoryDB()

        result = asyncio.run(
            create_connection_session(
                request(
                    target_scope="global",
                    asset_type="virtual",
                    protocol="virtual",
                    remark="总控",
                    tags=[],
                    scope_value="ops-all",
                ),
                ssh_manager,
                memory_db,
                restored_password=None,
            )
        )

        self.assertEqual(result["message"], "Global Session Established")
        self.assertEqual(result["data"]["session_id"], "sid-global")
        self.assertEqual(ssh_manager.local_calls[0]["tags"], ["全局会话"])
        self.assertEqual(memory_db.saved_assets, [])

    def test_asset_success_connects_and_persists_normalized_asset(self):
        ssh_manager = FakeSSHManager()
        memory_db = FakeMemoryDB()

        result = asyncio.run(
            create_connection_session(
                request(),
                ssh_manager,
                memory_db,
                restored_password="secret",
            )
        )

        self.assertEqual(result["message"], "Session Established")
        self.assertEqual(ssh_manager.connect_calls[0]["key_filename"], None)
        self.assertEqual(ssh_manager.connect_calls[0]["protocol"], "mysql")
        self.assertEqual(memory_db.saved_assets[0]["password"], "secret")
        self.assertEqual(memory_db.saved_assets[0]["extra_args"]["database"], "ops")

    def test_asset_failure_raises_structured_connection_error(self):
        ssh_manager = FakeSSHManager(
            connect_result={
                "success": False,
                "message": "Access denied for user",
            }
        )

        with self.assertRaises(ConnectionSessionServiceError) as ctx:
            asyncio.run(
                create_connection_session(
                    request(),
                    ssh_manager,
                    FakeMemoryDB(),
                    restored_password="bad-secret",
                )
            )

        self.assertGreaterEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail["protocol"], "mysql")


if __name__ == "__main__":
    unittest.main()
