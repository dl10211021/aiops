import asyncio
import json
import shutil
import unittest
import warnings
from pathlib import Path
from unittest.mock import AsyncMock, patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from api import routes


class TestInspectionJobs(unittest.TestCase):
    def tearDown(self):
        from core.cron_manager import CronManager

        for job in CronManager.get_all_jobs():
            if str(job["id"]).startswith("test_job_") or job.get("host") in {"10.0.0.10", ""}:
                try:
                    CronManager.remove_job(job["id"])
                except Exception:
                    pass
        for path in (Path.cwd() / "tests").glob("tmp_inspection_runs_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _run_store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_inspection_runs_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "runs.json"

    def test_cron_manager_supports_crud_pause_resume_and_run_metadata(self):
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="daily inspection",
            password="secret",
            job_id="test_job_crud",
            asset_id=7,
            target_scope="asset",
            template_id="linux-basic",
            notification_channel="wechat",
            active_skills=["linux-basic", "disk-check"],
        )
        self.assertEqual(job_id, "test_job_crud")

        job = CronManager.get_job(job_id)
        self.assertEqual(job["cron_expr"], "0 9 * * *")
        self.assertEqual(job["host"], "10.0.0.10")
        self.assertEqual(job["username"], "root")
        self.assertEqual(job["asset_id"], 7)
        self.assertEqual(job["template_id"], "linux-basic")
        self.assertEqual(job["active_skills"], ["linux-basic", "disk-check"])
        self.assertEqual(job["status"], "scheduled")

        paused = CronManager.pause_job(job_id)
        self.assertEqual(paused["status"], "paused")
        resumed = CronManager.resume_job(job_id)
        self.assertEqual(resumed["status"], "scheduled")

        updated = CronManager.update_job(
            job_id,
            cron_expr="*/30 * * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="half-hour inspection",
            password="secret",
            asset_id=7,
            target_scope="asset",
            template_id="linux-basic",
            notification_channel="wechat",
            active_skills=["linux-basic"],
        )
        self.assertEqual(updated["cron_expr"], "*/30 * * * *")
        self.assertEqual(updated["message"], "half-hour inspection")
        self.assertEqual(updated["active_skills"], ["linux-basic"])

        with patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock) as trigger:
            result = asyncio.run(CronManager.run_job_now(job_id))
        self.assertEqual(result["status"], "completed")
        trigger.assert_awaited_once()

    def test_cron_routes_expose_update_pause_resume_and_run(self):
        payload = routes.CronAddRequest(
            cron_expr="0 9 * * *",
            message="daily inspection",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            password="secret",
            asset_id=7,
            target_scope="asset",
            template_id="linux-basic",
            notification_channel="wechat",
            active_skills=["linux-basic"],
        )

        response = asyncio.run(routes.add_cron_job(payload))
        self.assertEqual(response.status, "success")
        job_id = response.data["job_id"]

        update_payload = routes.CronAddRequest(
            cron_expr="*/30 * * * *",
            message="half-hour inspection",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            password="secret",
            asset_id=7,
            target_scope="asset",
            template_id="linux-basic",
            notification_channel="wechat",
            active_skills=["db-check"],
        )
        updated = asyncio.run(routes.update_cron_job(job_id, update_payload))
        self.assertEqual(updated.data["job"]["cron_expr"], "*/30 * * * *")
        self.assertEqual(updated.data["job"]["active_skills"], ["db-check"])

        paused = asyncio.run(routes.pause_cron_job(job_id))
        self.assertEqual(paused.data["job"]["status"], "paused")
        resumed = asyncio.run(routes.resume_cron_job(job_id))
        self.assertEqual(resumed.data["job"]["status"], "scheduled")

        with patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock):
            run = asyncio.run(routes.run_cron_job_now(job_id))
        self.assertEqual(run.data["result"]["status"], "completed")

        deleted = asyncio.run(routes.delete_cron_job(job_id))
        self.assertEqual(deleted.status, "success")

    def test_scope_cron_route_does_not_require_single_host_or_username(self):
        payload = routes.CronAddRequest(
            cron_expr="0 2 * * *",
            message="inspect prod linux assets",
            target_scope="tag",
            scope_value="prod",
            template_id="linux-basic",
            notification_channel="auto",
        )

        response = asyncio.run(routes.add_cron_job(payload))
        job_id = response.data["job_id"]

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["job"]["host"], "")
        self.assertEqual(response.data["job"]["username"], "")
        self.assertEqual(response.data["job"]["target_scope"], "tag")
        asyncio.run(routes.delete_cron_job(job_id))

    def test_trigger_uses_selected_skills_instead_of_entire_registry(self):
        from connections.ssh_manager import ssh_manager
        from core import cron_manager
        from core.dispatcher import dispatcher

        with (
            patch.object(dispatcher, "skills_registry", {"selected-skill": {}, "other-skill": {}}),
            patch.object(ssh_manager, "connect", return_value={"success": True, "session_id": "sid-cron-skill"}) as connect,
            patch.object(ssh_manager, "disconnect") as disconnect,
            patch("core.agent.headless_agent_chat", new_callable=AsyncMock, return_value="ok") as headless,
        ):
            result = asyncio.run(
                cron_manager._trigger_proactive_inspection(
                    job_id="test_job_skills",
                    host="10.0.0.10",
                    agent_profile="default",
                    message="inspect",
                    username="root",
                    password="secret",
                    active_skills=["selected-skill", "missing-skill"],
                )
            )

        self.assertEqual(result, "ok")
        self.assertEqual(connect.call_args.kwargs["active_skills"], ["selected-skill"])
        self.assertNotIn("other-skill", connect.call_args.kwargs["active_skills"])
        headless.assert_awaited_once()
        disconnect.assert_called_once_with("sid-cron-skill")

    def test_job_skills_override_asset_default_skills_for_scope_runs(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        class FakeMemoryDB:
            def get_all_assets(self):
                return [
                    {
                        "id": 201,
                        "host": "10.0.0.201",
                        "port": 22,
                        "username": "root",
                        "password": "p1",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "agent_profile": "linux_ops",
                        "extra_args": {"category": "os"},
                        "skills": ["asset-default-skill"],
                        "tags": ["prod"],
                    }
                ]

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="",
            username="",
            agent_profile="default",
            message="prod inspection",
            job_id="test_job_skill_override",
            target_scope="tag",
            scope_value="prod",
            active_skills=["job-selected-skill"],
        )

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("skill_override")),
            patch("core.memory.memory_db", FakeMemoryDB()),
            patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock, return_value="ok") as trigger,
        ):
            asyncio.run(CronManager.run_job_now(job_id))

        self.assertEqual(trigger.await_args.kwargs["active_skills"], ["job-selected-skill"])

    def test_run_now_expands_asset_scope_and_persists_target_results(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        class FakeMemoryDB:
            def get_all_assets(self):
                return [
                    {
                        "id": 101,
                        "host": "10.0.0.101",
                        "port": 22,
                        "username": "root",
                        "password": "p1",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "agent_profile": "linux_ops",
                        "extra_args": {"category": "os"},
                        "skills": ["linux-skill"],
                        "tags": ["prod", "linux"],
                    },
                    {
                        "id": 102,
                        "host": "10.0.0.102",
                        "port": 3306,
                        "username": "mysql",
                        "password": "p2",
                        "asset_type": "mysql",
                        "protocol": "mysql",
                        "agent_profile": "db_ops",
                        "extra_args": {"category": "database"},
                        "skills": ["mysql-skill"],
                        "tags": ["prod", "db"],
                    },
                    {
                        "id": 103,
                        "host": "10.0.0.103",
                        "port": 22,
                        "username": "root",
                        "password": "p3",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "agent_profile": "linux_ops",
                        "extra_args": {"category": "os"},
                        "skills": [],
                        "tags": ["dev"],
                    },
                ]

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="",
            username="",
            agent_profile="default",
            message="prod inspection",
            job_id="test_job_scope",
            target_scope="tag",
            scope_value="prod",
            notification_channel="auto",
        )

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("scope")),
            patch("core.memory.memory_db", FakeMemoryDB()),
            patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock, return_value="ok") as trigger,
        ):
            result = asyncio.run(CronManager.run_job_now(job_id))
            runs = inspection_results.list_runs(job_id=job_id)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["target_count"], 2)
        self.assertEqual(trigger.await_count, 2)
        first_call = trigger.await_args_list[0].kwargs
        second_call = trigger.await_args_list[1].kwargs
        self.assertEqual(first_call["asset_type"], "linux")
        self.assertEqual(first_call["protocol"], "ssh")
        self.assertEqual(first_call["port"], 22)
        self.assertEqual(first_call["active_skills"], ["linux-skill"])
        self.assertEqual(second_call["asset_type"], "mysql")
        self.assertEqual(second_call["protocol"], "mysql")
        self.assertEqual(second_call["port"], 3306)
        self.assertEqual(second_call["active_skills"], ["mysql-skill"])
        self.assertEqual(runs[0]["id"], result["run_id"])
        self.assertEqual(runs[0]["status"], "completed")
        self.assertEqual([target["host"] for target in runs[0]["targets"]], ["10.0.0.101", "10.0.0.102"])
        self.assertTrue(all(target["status"] == "success" for target in runs[0]["targets"]))

    def test_cron_run_routes_return_persisted_history(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="single inspection",
            password="secret",
            job_id="test_job_runs_route",
        )

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("route")),
            patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock, return_value="ok"),
        ):
            run_response = asyncio.run(routes.run_cron_job_now(job_id))
            list_response = asyncio.run(routes.list_cron_job_runs(job_id))
            detail_response = asyncio.run(routes.get_cron_job_run(run_response.data["result"]["run_id"]))

        self.assertEqual(run_response.data["result"]["status"], "completed")
        self.assertEqual(len(list_response.data["runs"]), 1)
        self.assertEqual(detail_response.data["run"]["job_id"], job_id)
        self.assertEqual(detail_response.data["run"]["targets"][0]["host"], "10.0.0.10")

    def test_cron_run_summary_reports_success_rate_and_recent_failures(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("summary")):
            inspection_results.record_run(
                job_id="job-ok",
                status="completed",
                target_scope="asset",
                scope_value=None,
                message="ok",
                targets=[{"host": "10.0.0.10", "status": "success"}],
            )
            inspection_results.record_run(
                job_id="job-fail",
                status="failed",
                target_scope="tag",
                scope_value="prod",
                message="fail",
                targets=[{"host": "10.0.0.11", "status": "error", "error": "timeout"}],
            )
            summary_response = asyncio.run(routes.get_cron_run_summary())

        summary = summary_response.data["summary"]
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["success_rate"], 50.0)
        self.assertEqual(summary["recent_failures"][0]["job_id"], "job-fail")

    def test_inspection_report_detail_export_and_asset_filter_are_secret_free(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("report")):
            run = inspection_results.record_run(
                job_id="job-report",
                status="partial",
                target_scope="tag",
                scope_value="prod",
                message="daily report",
                targets=[
                    {
                        "asset_id": 101,
                        "host": "10.0.0.101",
                        "port": 22,
                        "username": "root",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "status": "success",
                        "result": "ok managed-secret",
                    },
                    {
                        "asset_id": 102,
                        "host": "10.0.0.102",
                        "port": 3306,
                        "username": "mysql",
                        "asset_type": "mysql",
                        "protocol": "mysql",
                        "status": "error",
                        "error": "timeout secret-key",
                    },
                ],
            )
            report_response = asyncio.run(routes.get_inspection_run_report(run["id"]))
            export_response = asyncio.run(routes.export_inspection_run_report(run["id"], format="markdown"))
            filtered_response = asyncio.run(routes.list_inspection_runs(asset_id=102))

        report = report_response.data["report"]
        self.assertEqual(report["run_id"], run["id"])
        self.assertEqual(report["summary"]["target_count"], 2)
        self.assertEqual(report["summary"]["success_count"], 1)
        self.assertEqual(report["summary"]["error_count"], 1)
        self.assertEqual(filtered_response.data["runs"][0]["id"], run["id"])
        self.assertEqual(len(filtered_response.data["runs"][0]["targets"]), 1)
        self.assertEqual(filtered_response.data["runs"][0]["targets"][0]["asset_id"], 102)
        markdown = export_response.data["content"]
        self.assertIn("# 巡检报告", markdown)
        self.assertIn("10.0.0.102", markdown)
        dumped = json.dumps({"report": report, "markdown": markdown}, ensure_ascii=False)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_run_now_retries_failed_target_and_records_duration(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="retry inspection",
            password="secret",
            job_id="test_job_retry",
            retry_count=1,
        )

        attempts = [
            {"status": "timeout", "error": "timeout"},
            "ok",
        ]

        async def flaky_trigger(**_kwargs):
            return attempts.pop(0)

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("retry")),
            patch("core.cron_manager._trigger_proactive_inspection", side_effect=flaky_trigger) as trigger,
        ):
            result = asyncio.run(CronManager.run_job_now(job_id))
            run = inspection_results.get_run(result["run_id"])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(trigger.await_count, 2)
        self.assertGreaterEqual(run["duration_ms"], 0)
        self.assertEqual(run["targets"][0]["attempts"], 2)
        self.assertEqual(run["targets"][0]["status"], "success")
        self.assertGreaterEqual(run["targets"][0]["duration_ms"], 0)

    def test_dashboard_inspection_trend_reports_success_rate_and_duration(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("trend")):
            inspection_results.record_run(
                job_id="job-ok",
                status="completed",
                target_scope="asset",
                scope_value=None,
                message="ok",
                targets=[{"asset_id": 1, "host": "10.0.0.10", "status": "success", "duration_ms": 100}],
                started_at="2026-04-27T00:00:00+00:00",
                completed_at="2026-04-27T00:00:01+00:00",
            )
            inspection_results.record_run(
                job_id="job-fail",
                status="failed",
                target_scope="asset",
                scope_value=None,
                message="fail",
                targets=[{"asset_id": 2, "host": "10.0.0.11", "status": "error", "duration_ms": 300}],
                started_at="2026-04-27T01:00:00+00:00",
                completed_at="2026-04-27T01:00:03+00:00",
            )
            response = asyncio.run(routes.get_dashboard_inspection_run_trend())

        point = response.data["points"][0]
        self.assertEqual(point["date"], "2026-04-27")
        self.assertEqual(point["total_runs"], 2)
        self.assertEqual(point["success_rate"], 50.0)
        self.assertEqual(point["avg_duration_ms"], 2000.0)
        self.assertEqual(point["target_error"], 1)


if __name__ == "__main__":
    unittest.main()
