import asyncio
import unittest

from fastapi import HTTPException

from api import session_runtime_routes
from api.schemas import SessionGroupUpdateRequest, SessionMetadataUpdateRequest


class TestSessionGroupRoutes(unittest.TestCase):
    def tearDown(self):
        session_runtime_routes.ssh_manager.active_sessions.clear()

    def test_update_session_group_updates_primary_tag_and_keeps_secondary_tags(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {
                "tags": ["旧组", "P0", "数据库"],
            }
        }

        response = asyncio.run(
            session_runtime_routes.update_session_group(
                "sid-1",
                SessionGroupUpdateRequest(group_name="数据库核心组"),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["group_name"], "数据库核心组")
        self.assertEqual(
            session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]["tags"],
            ["数据库核心组", "P0", "数据库"],
        )

    def test_update_session_group_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                session_runtime_routes.update_session_group(
                    "missing",
                    SessionGroupUpdateRequest(group_name="数据库核心组"),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_session_group_rejects_blank_group(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {"info": {"tags": ["旧组"]}}

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                session_runtime_routes.update_session_group(
                    "sid-1",
                    SessionGroupUpdateRequest(group_name="   "),
                )
            )

        self.assertEqual(ctx.exception.status_code, 422)

    def test_update_session_metadata_updates_remark_group_and_tags(self):
        session_runtime_routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {
                "remark": "旧名称",
                "tags": ["旧组", "P0"],
            }
        }

        response = asyncio.run(
            session_runtime_routes.update_session_metadata(
                "sid-1",
                SessionMetadataUpdateRequest(
                    remark="核心 Redis",
                    group_name="缓存组",
                    tags=["旧组", "P0", "缓存组", "P0"],
                ),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["remark"], "核心 Redis")
        self.assertEqual(response.data["group_name"], "缓存组")
        self.assertEqual(response.data["tags"], ["缓存组", "P0"])
        self.assertEqual(
            session_runtime_routes.ssh_manager.active_sessions["sid-1"]["info"]["tags"],
            ["缓存组", "P0"],
        )

    def test_update_session_metadata_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                session_runtime_routes.update_session_metadata(
                    "missing",
                    SessionMetadataUpdateRequest(remark="生产数据库"),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
