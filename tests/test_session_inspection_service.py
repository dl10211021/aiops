import asyncio
import unittest

from core.session_inspection_service import inspect_active_session_record


class TestSessionInspectionService(unittest.TestCase):
    def test_inspect_active_session_record_delegates_to_inspector(self):
        calls = []

        async def inspector(session_id):
            calls.append(session_id)
            return {
                "status": "warning",
                "summary": "发现巡检告警",
                "checks": [{"name": "disk", "status": "error"}],
            }

        report = asyncio.run(inspect_active_session_record("sid-1", inspector=inspector))

        self.assertEqual(calls, ["sid-1"])
        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["checks"][0]["name"], "disk")


if __name__ == "__main__":
    unittest.main()
