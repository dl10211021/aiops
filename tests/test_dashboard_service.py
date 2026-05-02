import unittest
from unittest.mock import patch

from core import dashboard_service


class FakeDashboardMemory:
    def get_all_assets(self):
        return [
            {
                "id": 1,
                "host": "10.0.0.10",
                "port": 22,
                "remark": "linux",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {"category": "os"},
            }
        ]


class TestDashboardService(unittest.TestCase):
    def test_overview_payload_combines_assets_sessions_jobs_alerts_and_runs(self):
        with (
            patch.object(dashboard_service.CronManager, "get_all_jobs", return_value=[{"status": "scheduled"}]),
            patch.object(dashboard_service, "alert_summary", return_value={"open": 2}),
            patch.object(dashboard_service, "run_summary", return_value={"success_rate": 100.0}),
        ):
            payload = dashboard_service.build_dashboard_overview_payload(
                {
                    "sid-1": {
                        "info": {
                            "asset_type": "linux",
                            "protocol": "ssh",
                            "host": "10.0.0.10",
                            "port": 22,
                        }
                    }
                },
                memory_db=FakeDashboardMemory(),
            )

        self.assertEqual(payload["summary"]["asset_total"], 1)
        self.assertEqual(payload["summary"]["active_sessions"], 1)
        self.assertEqual(payload["alerts"]["open"], 2)
        self.assertEqual(payload["jobs"]["scheduled"], 1)
        self.assertEqual(payload["inspection_runs"]["success_rate"], 100.0)

    def test_alert_trend_and_risk_ranking_payloads_use_alert_store(self):
        alerts = [
            {"created_at": "2026-05-01 10:00:00", "severity": "critical", "host": "db-1"},
            {"created_at": "2026-05-01 11:00:00", "severity": "warning", "host": "db-1"},
            {"created_at": "2026-05-01 12:00:00", "severity": "info", "host": "web-1"},
        ]
        with patch.object(dashboard_service, "list_alert_events", return_value=alerts):
            trend = dashboard_service.build_dashboard_alert_trend_payload()
            ranking = dashboard_service.build_dashboard_risk_ranking_payload()

        self.assertEqual(trend["points"][0]["total"], 3)
        self.assertEqual(ranking["ranking"][0]["host"], "db-1")

    def test_inspection_run_trend_payload_wraps_points(self):
        with patch.object(dashboard_service, "run_trend", return_value=[{"date": "2026-05-01", "total": 1}]):
            payload = dashboard_service.build_dashboard_inspection_run_trend_payload()

        self.assertEqual(payload["points"][0]["total"], 1)
