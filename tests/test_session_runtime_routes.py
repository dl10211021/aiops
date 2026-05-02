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

    def test_poll_all_sessions_messages_preserves_response_shape(self):
        routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {"pending_messages": [{"role": "assistant", "content": "ok"}]}
        }

        response = asyncio.run(routes.poll_all_sessions_messages())

        self.assertEqual(response.status, "success")
        self.assertEqual(
            response.data,
            {"updates": {"sid-1": [{"role": "assistant", "content": "ok"}]}},
        )
        self.assertEqual(
            routes.ssh_manager.active_sessions["sid-1"]["info"]["pending_messages"],
            [],
        )

    def test_update_session_skills_preserves_response_shape(self):
        routes.ssh_manager.active_sessions["sid-1"] = {"info": {"active_skills": []}}

        response = asyncio.run(
            routes.update_session_skills(
                "sid-1",
                routes.SkillsUpdateRequest(active_skills=["oracle"]),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "挂载技能已实时更新")
        self.assertEqual(
            routes.ssh_manager.active_sessions["sid-1"]["info"]["active_skills"],
            ["oracle"],
        )


if __name__ == "__main__":
    unittest.main()
