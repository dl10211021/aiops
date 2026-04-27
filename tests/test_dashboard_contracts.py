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

from api import routes


class FakeMemoryDB:
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
            },
            {
                "id": 2,
                "host": "prom.local",
                "port": 9090,
                "remark": "prometheus",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "extra_args": {"category": "monitor"},
            },
        ]


class TestDashboardContracts(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_dashboard_contracts_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_dashboard_contracts_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "alerts.json"

    def _run_store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_dashboard_contracts_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "runs.json"

    def test_dashboard_overview_includes_assets_alerts_and_jobs(self):
        from core import alert_events
        from core import inspection_results

        store_path = self._store_path("overview")
        run_store_path = self._run_store_path("overview_runs")
        with (
            patch.object(alert_events, "ALERT_STORE_PATH", store_path),
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", run_store_path),
            patch("core.memory.memory_db", FakeMemoryDB()),
        ):
            alert_events.create_alert_event({"host": "10.0.0.10", "alert_name": "DiskFull", "severity": "critical"})
            inspection_results.record_run(
                job_id="job-ok",
                status="completed",
                target_scope="asset",
                scope_value=None,
                message="ok",
                targets=[{"host": "10.0.0.10", "status": "success"}],
            )
            response = asyncio.run(routes.get_dashboard_overview())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["summary"]["asset_total"], 2)
        self.assertEqual(response.data["alerts"]["open"], 1)
        self.assertEqual(response.data["inspection_runs"]["success_rate"], 100.0)
        self.assertIn("by_category", response.data)
        self.assertIn("jobs", response.data)

    def test_dashboard_alert_trend_and_risk_ranking_contracts(self):
        from core import alert_events

        store_path = self._store_path("trend")
        with patch.object(alert_events, "ALERT_STORE_PATH", store_path):
            alert_events.create_alert_event({"host": "10.0.0.10", "alert_name": "DiskFull", "severity": "critical"})
            alert_events.create_alert_event({"host": "10.0.0.10", "alert_name": "CPUHigh", "severity": "warning"})
            alert_events.create_alert_event({"host": "10.0.0.11", "alert_name": "MemoryHigh", "severity": "warning"})

            trend = asyncio.run(routes.get_dashboard_alert_trend())
            risk = asyncio.run(routes.get_dashboard_risk_ranking())

        self.assertGreaterEqual(len(trend.data["points"]), 1)
        self.assertEqual(trend.data["points"][0]["total"], 3)
        self.assertEqual(risk.data["ranking"][0]["host"], "10.0.0.10")
        self.assertEqual(risk.data["ranking"][0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
