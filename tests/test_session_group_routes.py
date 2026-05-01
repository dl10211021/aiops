import asyncio
import unittest

from fastapi import HTTPException

from api import routes


class TestSessionGroupRoutes(unittest.TestCase):
    def tearDown(self):
        routes.ssh_manager.active_sessions.clear()

    def test_update_session_group_updates_primary_tag_and_keeps_secondary_tags(self):
        routes.ssh_manager.active_sessions["sid-1"] = {
            "info": {
                "tags": ["旧组", "P0", "数据库"],
            }
        }

        response = asyncio.run(
            routes.update_session_group(
                "sid-1",
                routes.SessionGroupUpdateRequest(group_name="数据库核心组"),
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["group_name"], "数据库核心组")
        self.assertEqual(
            routes.ssh_manager.active_sessions["sid-1"]["info"]["tags"],
            ["数据库核心组", "P0", "数据库"],
        )

    def test_update_session_group_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                routes.update_session_group(
                    "missing",
                    routes.SessionGroupUpdateRequest(group_name="数据库核心组"),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_session_group_rejects_blank_group(self):
        routes.ssh_manager.active_sessions["sid-1"] = {"info": {"tags": ["旧组"]}}

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                routes.update_session_group(
                    "sid-1",
                    routes.SessionGroupUpdateRequest(group_name="   "),
                )
            )

        self.assertEqual(ctx.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
