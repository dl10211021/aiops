import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from api import routes


class TestConnectionInspectionRoutes(unittest.TestCase):
    def test_inspect_connection_restores_secret_and_delegates_to_service(self):
        req = routes.ConnectionInspectionRequest(
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
            patch("api.routes.get_restored_connection_request", return_value=(req, "secret")),
            patch("api.routes.inspect_connection_request", inspect_request),
        ):
            response = asyncio.run(routes.inspect_connection(req))

        inspect_request.assert_awaited_once_with(req, restored_password="secret")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "巡检完成")
        self.assertEqual(response.data["kept_session"], False)


if __name__ == "__main__":
    unittest.main()
