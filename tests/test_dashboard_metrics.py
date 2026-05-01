import unittest

from core.dashboard_metrics import (
    build_alert_trend,
    build_dashboard_overview,
    build_risk_ranking,
)


class TestDashboardMetrics(unittest.TestCase):
    def test_build_dashboard_overview_groups_assets_sessions_and_jobs(self):
        overview = build_dashboard_overview(
            assets=[
                {
                    "host": "10.0.0.10",
                    "port": 22,
                    "remark": "linux",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "extra_args": {"category": "os"},
                },
                {
                    "host": "prom.local",
                    "port": 9090,
                    "remark": "prometheus",
                    "asset_type": "prometheus",
                    "protocol": "http_api",
                    "extra_args": {"category": "monitor"},
                },
            ],
            active_sessions=[
                {
                    "info": {
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "host": "10.0.0.10",
                        "port": 22,
                        "extra_args": {},
                    }
                }
            ],
            jobs=[{"status": "scheduled"}, {"status": "paused"}, {"status": "disabled"}],
            alerts={"open": 1},
            inspection_runs={"success_rate": 100.0},
        )

        self.assertEqual(overview["summary"]["asset_total"], 2)
        self.assertEqual(overview["summary"]["active_sessions"], 1)
        self.assertEqual(overview["by_protocol"]["ssh"], 1)
        self.assertEqual(overview["active_by_protocol"]["ssh"], 1)
        self.assertEqual(overview["jobs"]["scheduled"], 1)
        self.assertEqual(overview["jobs"]["paused"], 1)

    def test_alert_trend_and_risk_ranking_are_deterministic(self):
        alerts = [
            {"host": "10.0.0.10", "severity": "critical", "created_at": "2026-05-01 10:00:00"},
            {"host": "10.0.0.10", "severity": "warning", "created_at": "2026-05-01 11:00:00"},
            {"host": "10.0.0.11", "severity": "warning", "created_at": "2026-05-01 12:00:00"},
        ]

        trend = build_alert_trend(alerts)
        ranking = build_risk_ranking(alerts)

        self.assertEqual(trend, [{"date": "2026-05-01", "total": 3, "critical": 1, "warning": 2}])
        self.assertEqual(ranking[0]["host"], "10.0.0.10")
        self.assertEqual(ranking[0]["count"], 2)
