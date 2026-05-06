import asyncio
import unittest

from fastapi import HTTPException

from api import routes, session_runtime_routes
from api.schemas import HeartbeatUpdateRequest, PermissionUpdateRequest, SkillsUpdateRequest


class FakeMemoryDB:
    def __init__(self):
        self.messages = []

    def append_message(self, session_id, message):
        self.messages.append((session_id, message))
        return len(self.messages)


class TestSessionRuntimeRoutes(unittest.TestCase):
    def tearDown(self):
        session_runtime_routes.ssh_manager.active_sessions.clear()

    def test_session_runtime_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/session/{session_id}/stop", paths)
        self.assertIn("/session/{session_id}/permission", paths)
        self.assertIn("/session/{session_id}/heartbeat", paths)
        self.assertIn("/sessions/poll_all", paths)
        self.assertIn("/session/{session_id}/poll", paths)
        self.assertIn("/session/{session_id}/skills", paths)
        self.assertIn("/session/{session_id}/group", paths)
        self.assertIn("/session/{session_id}/metadata", paths)
        self.assertIn("/sessions/active", paths)
        self.assertIn("/tools/catalog", paths)
        self.assertIn("/session/{session_id}/tools", paths)
        self.assertIn("/session/{session_id}/commands", paths)

    def test_stop_chat_session_records_visible_audit_message(self):
        memory_db = FakeMemoryDB()
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {"pending_messages": []}
        }
        original_memory_db = session_runtime_routes.memory_db
        session_runtime_routes.memory_db = memory_db
        try:
            response = asyncio.run(session_runtime_routes.stop_chat_session("sid-1"))
        finally:
            session_runtime_routes.memory_db = original_memory_db

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "已发送中止信号。")
        pending = session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]["pending_messages"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["role"], "system")
        self.assertEqual(pending[0]["memory_type"], "manual_stop")
        self.assertTrue(pending[0]["visible_to_user"])
        self.assertEqual(memory_db.messages, [("sid-1", pending[0])])

    def test_update_session_permission_updates_existing_session(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {"allow_modifications": False}
        }

        response = asyncio.run(
            session_runtime_routes.update_session_permission(
                "sid-1",
                PermissionUpdateRequest(allow_modifications=True),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "权限已实时更新")
        self.assertTrue(
            session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]["allow_modifications"]
        )

    def test_update_session_heartbeat_updates_enabled_state_and_interval(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {"info": {}}

        response = asyncio.run(
            session_runtime_routes.update_session_heartbeat(
                "sid-1",
                HeartbeatUpdateRequest(
                    heartbeat_enabled=True,
                    master_interval=180,
                ),
            )
        )

        info = session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "心跳巡检状态已更新")
        self.assertTrue(info["heartbeat_enabled"])
        self.assertEqual(info["last_active"], 0)
        self.assertEqual(info["extra_args"]["master_interval"], 180)

    def test_update_session_heartbeat_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                session_runtime_routes.update_session_heartbeat(
                    "missing",
                    HeartbeatUpdateRequest(heartbeat_enabled=True),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_poll_all_sessions_messages_preserves_response_shape(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {"pending_messages": [{"role": "assistant", "content": "ok"}]}
        }

        response = asyncio.run(session_runtime_routes.poll_all_sessions_messages())

        self.assertEqual(response.status, "success")
        self.assertEqual(
            response.data,
            {"updates": {"sid-1": [{"role": "assistant", "content": "ok"}]}},
        )
        self.assertEqual(
            session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]["pending_messages"],
            [],
        )

    def test_update_session_skills_preserves_response_shape(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {"info": {"active_skills": []}}

        response = asyncio.run(
            session_runtime_routes.update_session_skills(
                "sid-1",
                SkillsUpdateRequest(active_skills=["oracle"]),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "挂载技能已实时更新")
        self.assertEqual(
            session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]["active_skills"],
            ["oracle"],
        )


if __name__ == "__main__":
    unittest.main()
