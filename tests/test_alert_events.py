import asyncio
import shutil
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from fastapi import HTTPException

from api import routes


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class TestAlertEvents(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_alert_events_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_alert_events_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "alerts.json"

    def test_webhook_alert_is_persisted_and_queryable(self):
        from core import alert_events

        store_path = self._store_path("webhook")
        payload = {
            "host": "10.0.0.10",
            "alert_name": "DiskFull",
            "severity": "critical",
            "description": "disk usage above 95%",
        }
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.dict(routes.ssh_manager.active_sessions, {}, clear=True),
        ):
            response = asyncio.run(routes.receive_webhook_alert(FakeRequest(payload)))
            self.assertEqual(response.status, "success")
            alert_id = response.data["alert"]["id"]

            listed = asyncio.run(routes.list_alert_events(status="open", severity="critical", host=None))
            self.assertEqual(len(listed.data["alerts"]), 1)
            self.assertEqual(listed.data["alerts"][0]["id"], alert_id)
            self.assertEqual(listed.data["alerts"][0]["host"], "10.0.0.10")

            detail = asyncio.run(routes.get_alert_event(alert_id))
            self.assertEqual(detail.data["alert"]["payload"]["alert_name"], "DiskFull")

    def test_alert_status_update_and_close_contract(self):
        from core import alert_events

        store_path = self._store_path("status")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            created = alert_events.create_alert_event(
                {
                    "host": "10.0.0.11",
                    "alert_name": "CPUHigh",
                    "severity": "warning",
                    "description": "cpu high",
                }
            )
            update = routes.AlertEventUpdateRequest(
                status="acknowledged",
                assignee="ops",
                note="checking",
            )
            response = asyncio.run(routes.update_alert_event(created["id"], update))
            self.assertEqual(response.data["alert"]["status"], "acknowledged")
            self.assertEqual(response.data["alert"]["assignee"], "ops")

            close = routes.AlertEventUpdateRequest(status="closed", note="resolved")
            response = asyncio.run(routes.update_alert_event(created["id"], close))
            self.assertEqual(response.data["alert"]["status"], "closed")
            self.assertTrue(response.data["alert"]["closed_at"])

    def test_missing_alert_raises_404(self):
        from core import alert_events

        store_path = self._store_path("missing")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.get_alert_event("missing"))

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
