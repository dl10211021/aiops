import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import alert_events, alert_policy
from core.alert_event_service import (
    AlertEventServiceError,
    get_alert_event_record,
    list_alert_event_records,
    update_alert_event_record,
)


class TestAlertEventService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_alert_event_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_alert_event_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "alerts.json"

    def test_list_get_and_update_alert_event_records(self):
        store_path = self._store_path("records")
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(alert_policy, "ALERT_POLICY_CONFIG_PATH", store_path.parent / "policy.json"),
        ):
            created = alert_events.create_alert_event(
                {
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "critical",
                    "description": "disk high",
                }
            )

            listed = list_alert_event_records(status="open", severity="critical")
            listed_by_policy = list_alert_event_records(source_family="generic", automation_mode="record_only")
            loaded = get_alert_event_record(created["id"])
            updated = update_alert_event_record(created["id"], status="acknowledged", assignee="ops", note="checking")

        self.assertEqual(listed[0]["id"], created["id"])
        self.assertEqual(listed_by_policy[0]["id"], created["id"])
        self.assertEqual(loaded["host"], "db.local")
        self.assertEqual(updated["status"], "acknowledged")
        self.assertEqual(updated["assignee"], "ops")
        self.assertEqual(updated["notes"][0]["content"], "checking")

    def test_missing_alert_maps_to_404(self):
        with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("missing")):
            with self.assertRaises(AlertEventServiceError) as get_ctx:
                get_alert_event_record("missing")
            with self.assertRaises(AlertEventServiceError) as update_ctx:
                update_alert_event_record("missing", status="closed")

        self.assertEqual(get_ctx.exception.status_code, 404)
        self.assertEqual(update_ctx.exception.status_code, 404)

    def test_invalid_status_maps_to_422(self):
        with patch.object(alert_events, "ALERT_STORE_PATH", self._store_path("invalid")):
            created = alert_events.create_alert_event({"host": "db.local", "alert_name": "DiskFull"})
            with self.assertRaises(AlertEventServiceError) as ctx:
                update_alert_event_record(created["id"], status="invalid")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("不支持的告警状态", ctx.exception.detail)
