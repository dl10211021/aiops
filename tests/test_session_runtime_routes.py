import asyncio
import unittest

from fastapi import HTTPException

from api import routes


class TestSessionRuntimeRoutes(unittest.TestCase):
    def tearDown(self):
        routes.ssh_manager.active_sessions.clear()

    def test_update_session_permission_updates_existing_session(self):
        routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {"allow_modifications": False}
        }

        response = asyncio.run(
            routes.update_session_permission(
                "sid-1",
                routes.PermissionUpdateRequest(allow_modifications=True),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "权限已实时更新")
        self.assertTrue(
            routes.ssh_manager.active_sessions["sid-1"]["info"]["allow_modifications"]
        )

    def test_update_session_heartbeat_updates_enabled_state_and_interval(self):
        routes.ssh_manager.active_sessions["sid-1"] = {"info": {}}

        response = asyncio.run(
            routes.update_session_heartbeat(
                "sid-1",
                routes.HeartbeatUpdateRequest(
                    heartbeat_enabled=True,
                    master_interval=180,
                ),
            )
        )

        info = routes.ssh_manager.active_sessions["sid-1"]["info"]
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "心跳巡检状态已更新")
        self.assertTrue(info["heartbeat_enabled"])
        self.assertEqual(info["last_active"], 0)
        self.assertEqual(info["extra_args"]["master_interval"], 180)

    def test_update_session_heartbeat_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                routes.update_session_heartbeat(
                    "missing",
                    routes.HeartbeatUpdateRequest(heartbeat_enabled=True),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
