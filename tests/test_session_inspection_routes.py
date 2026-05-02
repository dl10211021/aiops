import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from api import routes


class TestSessionInspectionRoutes(unittest.TestCase):
    def test_inspect_active_session_returns_mapped_report_payload(self):
        report = {
            "status": "warning",
            "summary": "巡检完成，存在告警",
            "checks": [{"name": "disk", "status": "error"}],
        }
        inspect_record = AsyncMock(return_value=report)

        with patch("api.routes.inspect_active_session_record", inspect_record):
            response = asyncio.run(routes.inspect_active_session("sid-1"))

        inspect_record.assert_awaited_once_with("sid-1")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "巡检完成，存在告警")
        self.assertEqual(response.data, {"inspection": report})


if __name__ == "__main__":
    unittest.main()
