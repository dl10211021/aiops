import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from api import connection_routes, routes
from api.schemas import ConnectionInspectionRequest


class TestConnectionInspectionRoutes(unittest.TestCase):
    def test_connection_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/connect/test", paths)
        self.assertIn("/connect/inspect", paths)
        self.assertIn("/connect", paths)
        self.assertIn("/execute", paths)
        self.assertIn("/disconnect/{session_id}", paths)

    def test_inspect_connection_restores_secret_and_delegates_to_service(self):
        req = ConnectionInspectionRequest(
            host="db.local",
            port=3306,
            username="ops",
            asset_type="mysql",
            protocol="mysql",
            extra_args={"database": "ops"},
        )
        payload = {
            "status": "success",
            "message": "巡检完成",
            "data": {"session_id": None, "kept_session": False, "inspection": {}},
        }
        inspect_request = AsyncMock(return_value=payload)

        with (
            patch(
                "api.connection_routes.get_restored_connection_request",
                return_value=(req, "secret"),
            ),
            patch("api.connection_routes.inspect_connection_request", inspect_request),
        ):
            response = asyncio.run(connection_routes.inspect_connection(req))

        inspect_request.assert_awaited_once_with(req, restored_password="secret")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "巡检完成")
        self.assertEqual(response.data["kept_session"], False)


if __name__ == "__main__":
    unittest.main()
