import asyncio
import unittest
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from api import routes


class TestGlobalSessionRoutes(unittest.TestCase):
    def tearDown(self):
        routes.ssh_manager.active_sessions.clear()

    def test_global_test_does_not_attempt_asset_connection(self):
        response = asyncio.run(
            routes.test_connection(
                routes.ConnectionRequest(
                    host="global",
                    port=0,
                    username="admin",
                    asset_type="virtual",
                    protocol="virtual",
                    target_scope="global",
                )
            )
        )

        self.assertEqual(response.status, "success")
        self.assertIn("全局", response.message)

    def test_global_connect_creates_virtual_orchestration_session(self):
        response = asyncio.run(
            routes.create_ssh_connection(
                routes.ConnectionRequest(
                    host="global",
                    port=0,
                    username="admin",
                    asset_type="virtual",
                    protocol="virtual",
                    target_scope="global",
                    allow_modifications=False,
                    active_skills=[],
                    remark="总控",
                )
            )
        )

        sid = response.data["session_id"]
        info = routes.ssh_manager.active_sessions[sid]["info"]
        self.assertEqual(info["asset_type"], "virtual")
        self.assertEqual(info["protocol"], "virtual")
        self.assertEqual(info["target_scope"], "global")
        self.assertFalse(info["allow_modifications"])
        self.assertTrue(info["is_virtual"])

    def test_active_sessions_include_target_scope_context(self):
        response = asyncio.run(
            routes.create_ssh_connection(
                routes.ConnectionRequest(
                    host="global",
                    port=0,
                    username="admin",
                    asset_type="virtual",
                    protocol="virtual",
                    target_scope="global",
                    scope_value="ops-all",
                    allow_modifications=True,
                    active_skills=["core"],
                    remark="总控",
                )
            )
        )

        sid = response.data["session_id"]
        active = asyncio.run(routes.get_active_sessions())
        session = active.data["sessions"][sid]

        self.assertEqual(session["target_scope"], "global")
        self.assertEqual(session["scope_value"], "ops-all")
        self.assertTrue(session["isReadWriteMode"])

    def test_global_inspect_returns_supported_without_physical_probe(self):
        response = asyncio.run(
            routes.inspect_connection(
                routes.ConnectionInspectionRequest(
                    host="global",
                    port=0,
                    username="admin",
                    asset_type="virtual",
                    protocol="virtual",
                    target_scope="global",
                )
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["inspection"]["profile"], "global")
        self.assertTrue(response.data["inspection"]["supported"])


if __name__ == "__main__":
    unittest.main()
