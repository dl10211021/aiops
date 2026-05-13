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

from api import alert_routes, routes
from api.schemas import AlertEventUpdateRequest


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

    def test_alert_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/alerts", paths)
        self.assertIn("/alerts/{alert_id}", paths)
        self.assertIn("/webhook/alert", paths)

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
            patch.dict(alert_routes.ssh_manager.active_sessions, {}, clear=True),
        ):
            response = asyncio.run(alert_routes.receive_webhook_alert(FakeRequest(payload)))
            self.assertEqual(response.status, "success")
            alert_id = response.data["alert"]["id"]

            listed = asyncio.run(alert_routes.list_alert_events(status="open", severity="critical", host=None))
            self.assertEqual(len(listed.data["alerts"]), 1)
            self.assertEqual(listed.data["alerts"][0]["id"], alert_id)
            self.assertEqual(listed.data["alerts"][0]["host"], "10.0.0.10")

            detail = asyncio.run(alert_routes.get_alert_event(alert_id))
            self.assertEqual(detail.data["alert"]["payload"]["alert_name"], "DiskFull")

    def test_alertmanager_payload_expands_and_preserves_labels(self):
        from core import alert_events

        store_path = self._store_path("alertmanager")
        payload = {
            "receiver": "grafana",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "NodeDown",
                        "instance": "10.0.0.12:9100",
                        "severity": "critical",
                    },
                    "annotations": {
                        "summary": "node exporter target down",
                    },
                    "startsAt": "2026-05-13T08:00:00Z",
                    "fingerprint": "fp-node-down",
                }
            ],
        }

        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            created = alert_events.create_alert_events(payload)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["source_type"], "alertmanager")
        self.assertEqual(created[0]["source"], "grafana")
        self.assertEqual(created[0]["host"], "10.0.0.12:9100")
        self.assertEqual(created[0]["alert_name"], "NodeDown")
        self.assertEqual(created[0]["fingerprint"], "fp-node-down")
        self.assertEqual(created[0]["labels"]["severity"], "critical")

    def test_duplicate_fingerprint_merges_and_recovery_closes_event(self):
        from core import alert_events

        store_path = self._store_path("dedupe")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            first = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "warning",
                    "description": "disk 90%",
                    "fingerprint": "zbx-disk",
                }
            )
            second = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "critical",
                    "description": "disk 98%",
                    "fingerprint": "zbx-disk",
                }
            )
            recovered = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "ok",
                    "description": "disk recovered",
                    "status": "resolved",
                    "fingerprint": "zbx-disk",
                }
            )
            listed = alert_events.list_alert_events(limit=10)

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["id"], recovered["id"])
        self.assertEqual(recovered["repeat_count"], 3)
        self.assertEqual(recovered["status"], "closed")
        self.assertEqual(len(listed), 1)

    def test_list_alert_events_filters_source_family_and_automation(self):
        from core import alert_events

        store_path = self._store_path("policy_filters")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            zabbix = alert_events.create_alert_event(
                {
                    "source": "zabbix",
                    "host": "db.local",
                    "alert_name": "DiskFull",
                    "severity": "critical",
                    "description": "disk above 95%",
                    "fingerprint": "zbx-critical",
                }
            )
            info = alert_events.create_alert_event(
                {
                    "source": "prometheus",
                    "host": "web.local",
                    "alert_name": "FYI",
                    "severity": "info",
                    "description": "informational alert",
                    "fingerprint": "prom-info",
                }
            )
            zabbix_items = alert_events.list_alert_events(source_family="zabbix", limit=10)
            ai_items = alert_events.list_alert_events(automation_mode="ai", limit=10)
            record_items = alert_events.list_alert_events(automation_mode="record_only", limit=10)

        self.assertEqual([item["id"] for item in zabbix_items], [zabbix["id"]])
        self.assertEqual([item["id"] for item in ai_items], [zabbix["id"]])
        self.assertEqual([item["id"] for item in record_items], [info["id"]])

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
            update = AlertEventUpdateRequest(
                status="acknowledged",
                assignee="ops",
                note="checking",
            )
            response = asyncio.run(alert_routes.update_alert_event(created["id"], update))
            self.assertEqual(response.data["alert"]["status"], "acknowledged")
            self.assertEqual(response.data["alert"]["assignee"], "ops")

            close = AlertEventUpdateRequest(status="closed", note="resolved")
            response = asyncio.run(alert_routes.update_alert_event(created["id"], close))
            self.assertEqual(response.data["alert"]["status"], "closed")
            self.assertTrue(response.data["alert"]["closed_at"])

    def test_missing_alert_raises_404(self):
        from core import alert_events

        store_path = self._store_path("missing")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(alert_routes.get_alert_event("missing"))

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
