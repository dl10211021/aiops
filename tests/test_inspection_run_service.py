import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import inspection_results
from core.inspection_run_service import (
    InspectionRunServiceError,
    export_inspection_run_report_content,
    get_inspection_run_record,
    get_inspection_run_report_record,
    inspection_run_summary,
    list_inspection_run_records,
)


class TestInspectionRunService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_inspection_run_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_inspection_run_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "runs.json"

    def _record_run(self):
        return inspection_results.record_run(
            job_id="job-1",
            status="completed",
            target_scope="asset",
            scope_value=None,
            message="done",
            targets=[
                {
                    "asset_id": 101,
                    "host": "db.local",
                    "asset_type": "mysql",
                    "protocol": "mysql",
                    "status": "success",
                    "result": "ok",
                }
            ],
        )

    def test_list_get_summary_and_report_records(self):
        store_path = self._store_path("records")
        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", store_path):
            run = self._record_run()
            runs = list_inspection_run_records(job_id="job-1")
            loaded = get_inspection_run_record(run["id"])
            report = get_inspection_run_report_record(run["id"])
            summary = inspection_run_summary()

        self.assertEqual(runs[0]["id"], run["id"])
        self.assertEqual(loaded["id"], run["id"])
        self.assertEqual(report["run_id"], run["id"])
        self.assertEqual(summary["total_runs"], 1)

    def test_run_transcript_records_create_update_report_and_delete(self):
        store_path = self._store_path("transcript")
        started_event = {
            "time": "2026-05-13T00:00:00+00:00",
            "type": "run_started",
            "message": "开始巡检。",
            "status": "running",
        }
        target_event = {
            "time": "2026-05-13T00:00:10+00:00",
            "type": "target_completed",
            "message": "目标完成。",
            "status": "success",
        }
        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", store_path):
            run = inspection_results.record_run(
                job_id="job-transcript",
                status="running",
                target_scope="asset",
                scope_value="101",
                message="transcript run",
                targets=[{"asset_id": 101, "host": "db.local", "status": "running"}],
                events=[started_event],
                completed_at=None,
            )
            inspection_results.update_run(
                run["id"],
                status="completed",
                targets=[{"asset_id": 101, "host": "db.local", "status": "success"}],
                events=[started_event, target_event],
                notification={"status": "SUCCESS", "message": "sent"},
                completed_at="2026-05-13T00:01:00+00:00",
            )
            transcript_events = inspection_results.get_run_transcript_events(run["id"])
            report = get_inspection_run_report_record(run["id"])
            deleted = inspection_results.delete_run(run["id"])
            after_delete = inspection_results.get_run_transcript_events(run["id"])

        event_types = [event["type"] for event in transcript_events]
        self.assertIn("run_recorded", event_types)
        self.assertIn("run_started", event_types)
        self.assertIn("run_updated", event_types)
        self.assertIn("target_completed", event_types)
        self.assertEqual(report["transcript"]["event_count"], len(transcript_events))
        self.assertTrue(deleted)
        self.assertEqual(after_delete, [])

    def test_export_report_supports_markdown_and_json(self):
        store_path = self._store_path("export")
        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", store_path):
            run = self._record_run()
            markdown = export_inspection_run_report_content(run["id"], "markdown")
            json_payload = export_inspection_run_report_content(run["id"], "json")

        self.assertEqual(markdown["content_type"], "text/markdown")
        self.assertIn("# 巡检报告", markdown["content"])
        self.assertEqual(json_payload["content_type"], "application/json")
        self.assertIn('"run_id"', json_payload["content"])

    def test_export_report_rejects_unknown_format(self):
        with self.assertRaises(InspectionRunServiceError) as ctx:
            export_inspection_run_report_content("run-missing", "pdf")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "format 仅支持 markdown、html 或 json")

    def test_missing_run_and_report_raise_404(self):
        store_path = self._store_path("missing")
        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", store_path):
            with self.assertRaises(InspectionRunServiceError) as run_ctx:
                get_inspection_run_record("missing")
            with self.assertRaises(InspectionRunServiceError) as report_ctx:
                get_inspection_run_report_record("missing")

        self.assertEqual(run_ctx.exception.status_code, 404)
        self.assertEqual(report_ctx.exception.status_code, 404)
