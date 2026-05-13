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

from api import dashboard_routes, inspection_job_routes, inspection_run_routes, routes
from api.schemas import CronAddRequest


class TestInspectionJobs(unittest.TestCase):
    def tearDown(self):
        from core import cron_manager, inspection_results
        from core.cron_manager import CronManager

        for job in CronManager.get_all_jobs():
            if str(job["id"]).startswith("test_job_") or job.get("host") in {"10.0.0.10", ""}:
                try:
                    CronManager.remove_job(job["id"])
                except Exception:
                    pass
        cron_manager._RUNNING_INSPECTIONS.clear()
        for path in (Path.cwd() / "tests").glob("tmp_inspection_runs_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _run_store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_inspection_runs_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "runs.json"

    def test_inspection_job_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/cron/add", paths)
        self.assertIn("/cron/list", paths)
        self.assertIn("/cron/{job_id}", paths)
        self.assertIn("/cron/{job_id}/pause", paths)
        self.assertIn("/cron/{job_id}/resume", paths)
        self.assertIn("/cron/{job_id}/run", paths)
        self.assertIn("/cron/{job_id}/run/async", paths)
        self.assertIn("/cron/{job_id}/run/cancel", paths)

    def test_inspection_run_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/cron/{job_id}/runs", paths)
        self.assertIn("/inspection-runs", paths)
        self.assertIn("/cron/runs/summary", paths)
        self.assertIn("/cron/runs/{run_id}", paths)
        self.assertIn("/inspection-runs/{run_id}", paths)
        self.assertIn("/inspection-runs/{run_id}/report", paths)
        self.assertIn("/inspection-runs/{run_id}/export", paths)

    def test_cron_manager_supports_crud_pause_resume_and_run_metadata(self):
        from core import cron_manager, inspection_results
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="daily inspection",
            inspection_cycle="weekly",
            inspection_depth="deep",
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
        self.assertEqual(job["inspection_cycle"], "weekly")
        self.assertEqual(job["inspection_depth"], "deep")
        self.assertEqual(job["host"], "10.0.0.10")
        self.assertEqual(job["username"], "root")
        self.assertEqual(job["asset_id"], 7)
        self.assertEqual(job["template_id"], "linux-basic")
        self.assertEqual(job["active_skills"], ["linux-basic", "disk-check"])
        self.assertEqual(job["status"], "scheduled")

        paused = CronManager.pause_job(job_id)
        self.assertEqual(paused["status"], "paused")
        stored_job = cron_manager.scheduler.get_job(job_id)
        self.assertTrue(stored_job.kwargs["_opscore_paused"])
        resumed = CronManager.resume_job(job_id)
        self.assertEqual(resumed["status"], "scheduled")
        stored_job = cron_manager.scheduler.get_job(job_id)
        self.assertFalse(stored_job.kwargs["_opscore_paused"])

        updated = CronManager.update_job(
            job_id,
            cron_expr="*/30 * * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="half-hour inspection",
            inspection_cycle="monthly",
            inspection_depth="standard",
            password="secret",
            asset_id=7,
            target_scope="asset",
            template_id="linux-basic",
            notification_channel="wechat",
            active_skills=["linux-basic"],
        )
        self.assertEqual(updated["cron_expr"], "*/30 * * * *")
        self.assertEqual(updated["message"], "half-hour inspection")
        self.assertEqual(updated["inspection_cycle"], "monthly")
        self.assertEqual(updated["inspection_depth"], "standard")
        self.assertEqual(updated["active_skills"], ["linux-basic"])

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("crud_metadata")),
            patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock) as trigger,
        ):
            result = asyncio.run(CronManager.run_job_now(job_id))
        self.assertEqual(result["status"], "completed")
        trigger.assert_awaited_once()

    def test_job_to_dict_treats_missing_next_run_as_paused_when_scheduler_runs(self):
        from core import cron_manager
        from core.cron_manager import CronManager

        class FakeJob:
            id = "test_job_paused_after_restart"
            args = []
            kwargs = {
                "job_id": id,
                "cron_expr": "0 9 * * *",
                "host": "10.0.0.10",
                "username": "root",
                "agent_profile": "default",
                "message": "inspection",
            }
            next_run_time = None

        class FakeScheduler:
            running = True

        with patch.object(cron_manager, "scheduler", FakeScheduler()):
            job = CronManager._job_to_dict(FakeJob())

        self.assertEqual(job["status"], "paused")
        self.assertEqual(job["next_run_time"], "Paused")

    def test_job_to_dict_uses_persisted_paused_flag(self):
        from core import cron_manager
        from core.cron_manager import CronManager

        class FakeJob:
            id = "test_job_persisted_paused"
            args = []
            kwargs = {
                "job_id": id,
                "cron_expr": "0 9 * * *",
                "host": "10.0.0.10",
                "username": "root",
                "agent_profile": "default",
                "message": "inspection",
                "_opscore_paused": True,
            }
            next_run_time = "2026-05-12 13:00:00+08:00"

        class FakeScheduler:
            running = True

        with patch.object(cron_manager, "scheduler", FakeScheduler()):
            job = CronManager._job_to_dict(FakeJob())

        self.assertEqual(job["status"], "paused")

    def test_job_to_dict_includes_openocta_style_run_state(self):
        from core import cron_manager, inspection_results
        from core.cron_manager import CronManager

        class FakeJob:
            id = "test_job_run_state"
            args = []
            kwargs = {
                "job_id": id,
                "cron_expr": "0 9 * * *",
                "host": "10.0.0.10",
                "username": "root",
                "agent_profile": "default",
                "message": "inspection",
            }
            next_run_time = "2026-05-12 13:00:00+08:00"

        class FakeScheduler:
            running = True

        class FakeTask:
            def done(self):
                return False

        with (
            patch.object(cron_manager, "scheduler", FakeScheduler()),
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("job_run_state")),
        ):
            run = inspection_results.record_run(
                job_id="test_job_run_state",
                status="partial",
                target_scope="asset",
                scope_value="37",
                message="inspection",
                targets=[
                    {"asset_id": 37, "host": "10.0.0.10", "status": "success"},
                    {"asset_id": 38, "host": "10.0.0.11", "status": "error"},
                ],
            )
            inspection_results.update_run(
                run["id"],
                notification={"status": "SUCCESS", "message": "企业微信通知已发送成功！"},
            )
            cron_manager._RUNNING_INSPECTIONS["test_job_run_state"] = {
                "task": FakeTask(),
                "run_id": "run-active",
                "started_at": "2026-05-12T00:00:00+00:00",
            }
            job = CronManager._job_to_dict(FakeJob())

        self.assertEqual(job["run_state"]["schedule_status"], "scheduled")
        self.assertTrue(job["run_state"]["running"])
        self.assertEqual(job["run_state"]["running_run_id"], "run-active")
        self.assertEqual(job["run_state"]["latest_run_id"], run["id"])
        self.assertEqual(job["run_state"]["latest_status"], "partial")
        self.assertEqual(job["run_state"]["target_count"], 2)
        self.assertEqual(job["run_state"]["success_count"], 1)
        self.assertEqual(job["run_state"]["error_count"], 1)
        self.assertEqual(job["run_state"]["notification_status"], "SUCCESS")

    def test_job_to_dict_marks_stale_running_run_as_orphaned(self):
        from core import cron_manager, inspection_results
        from core.cron_manager import CronManager

        class FakeJob:
            id = "test_job_stale_running"
            args = []
            kwargs = {
                "job_id": id,
                "cron_expr": "0 9 * * *",
                "host": "10.0.0.10",
                "username": "root",
                "agent_profile": "default",
                "message": "inspection",
            }
            next_run_time = "2026-05-12 13:00:00+08:00"

        class FakeScheduler:
            running = True

        with (
            patch.object(cron_manager, "scheduler", FakeScheduler()),
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("stale_running")),
        ):
            inspection_results.record_run(
                job_id="test_job_stale_running",
                status="running",
                target_scope="asset",
                scope_value="37",
                message="inspection",
                targets=[{"asset_id": 37, "host": "10.0.0.10", "status": "running"}],
                completed_at=None,
            )
            job = CronManager._job_to_dict(FakeJob())

        self.assertFalse(job["run_state"]["running"])
        self.assertEqual(job["run_state"]["latest_status"], "running")
        self.assertEqual(job["run_state"]["effective_status"], "orphaned")

    def test_update_preserves_paused_status(self):
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="inspection",
            password="secret",
            job_id="test_job_update_paused",
        )
        CronManager.pause_job(job_id)

        updated = CronManager.update_job(
            job_id,
            cron_expr="*/30 * * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="updated inspection",
            password="secret",
        )

        self.assertEqual(updated["status"], "paused")
        self.assertEqual(updated["cron_expr"], "*/30 * * * *")

    def test_cron_routes_expose_update_pause_resume_and_run(self):
        from core import inspection_results

        payload = CronAddRequest(
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

        response = asyncio.run(inspection_job_routes.add_cron_job(payload))
        self.assertEqual(response.status, "success")
        job_id = response.data["job_id"]

        update_payload = CronAddRequest(
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
        updated = asyncio.run(
            inspection_job_routes.update_cron_job(job_id, update_payload)
        )
        self.assertEqual(updated.data["job"]["cron_expr"], "*/30 * * * *")
        self.assertEqual(updated.data["job"]["active_skills"], ["db-check"])

        paused = asyncio.run(inspection_job_routes.pause_cron_job(job_id))
        self.assertEqual(paused.data["job"]["status"], "paused")
        resumed = asyncio.run(inspection_job_routes.resume_cron_job(job_id))
        self.assertEqual(resumed.data["job"]["status"], "scheduled")

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("route_crud")),
            patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock),
        ):
            run = asyncio.run(inspection_job_routes.run_cron_job_now(job_id))
        self.assertEqual(run.data["result"]["status"], "completed")

        deleted = asyncio.run(inspection_job_routes.delete_cron_job(job_id))
        self.assertEqual(deleted.status, "success")

    def test_cron_list_route_supports_pagination_and_status_metrics(self):
        from core.cron_manager import CronManager

        first_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="linux daily inspection",
            password="secret",
            job_id="test_job_page_one",
        )
        second_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * 1",
            host="10.0.0.20",
            username="root",
            agent_profile="default",
            message="oracle weekly inspection",
            password="secret",
            job_id="test_job_page_two",
        )
        CronManager.pause_job(second_id)

        response = asyncio.run(
            inspection_job_routes.list_cron_jobs(
                page=1,
                page_size=1,
                query="inspection",
                status="all",
            )
        )
        paused = asyncio.run(
            inspection_job_routes.list_cron_jobs(
                page=1,
                page_size=10,
                query="oracle",
                status="paused",
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["pagination"]["page_size"], 1)
        self.assertGreaterEqual(response.data["pagination"]["filtered_total"], 2)
        self.assertGreaterEqual(response.data["metrics"]["total"], 2)
        self.assertEqual(paused.data["jobs"][0]["id"], second_id)
        self.assertEqual(paused.data["pagination"]["filtered_total"], 1)
        asyncio.run(inspection_job_routes.delete_cron_job(first_id))
        asyncio.run(inspection_job_routes.delete_cron_job(second_id))

    def test_scope_cron_route_does_not_require_single_host_or_username(self):
        payload = CronAddRequest(
            cron_expr="0 2 * * *",
            message="inspect prod linux assets",
            target_scope="tag",
            scope_value="prod",
            template_id="linux-basic",
            notification_channel="auto",
        )

        response = asyncio.run(inspection_job_routes.add_cron_job(payload))
        job_id = response.data["job_id"]

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["job"]["host"], "")
        self.assertEqual(response.data["job"]["username"], "")
        self.assertEqual(response.data["job"]["target_scope"], "tag")
        asyncio.run(inspection_job_routes.delete_cron_job(job_id))

    def test_run_now_can_be_cancelled_and_records_cancelled_status(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        async def run_case():
            job_id = CronManager.add_inspection_job(
                cron_expr="0 9 * * *",
                host="10.0.0.10",
                username="root",
                agent_profile="default",
                message="cancel inspection",
                password="secret",
                job_id="test_job_cancel_run",
                notification_channel="none",
            )

            never_finishes = asyncio.Event()

            async def slow_trigger(**_kwargs):
                await never_finishes.wait()
                return "ok"

            with (
                patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("cancel_run")),
                patch("core.cron_manager._trigger_proactive_inspection", side_effect=slow_trigger) as trigger,
            ):
                task = asyncio.create_task(CronManager.run_job_now(job_id))
                for _ in range(100):
                    runs = inspection_results.list_runs(job_id=job_id)
                    if runs and runs[0]["status"] == "running" and trigger.await_count:
                        break
                    await asyncio.sleep(0.01)

                cancel_response = await inspection_job_routes.cancel_cron_job_run(job_id)
                result = await asyncio.wait_for(task, timeout=2)
                run = inspection_results.get_run(result["run_id"])

            return cancel_response, result, run

        cancel_response, result, run = asyncio.run(run_case())

        self.assertEqual(cancel_response.data["result"]["status"], "cancelling")
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(run["status"], "cancelled")
        self.assertEqual(run["targets"][0]["status"], "cancelled")

    def test_start_job_now_returns_after_recording_running_progress(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        async def run_case():
            job_id = CronManager.add_inspection_job(
                cron_expr="0 9 * * *",
                host="10.0.0.10",
                username="root",
                agent_profile="default",
                message="background inspection",
                password="secret",
                job_id="test_job_async_run",
                notification_channel="none",
            )

            release = asyncio.Event()

            async def slow_trigger(**_kwargs):
                await release.wait()
                return "ok"

            with (
                patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("async_run")),
                patch("core.cron_manager._trigger_proactive_inspection", side_effect=slow_trigger),
            ):
                started = await CronManager.start_job_now(job_id)
                run = inspection_results.get_run(started["run_id"])
                release.set()
                for _ in range(100):
                    completed = inspection_results.get_run(started["run_id"])
                    if completed and completed["status"] == "completed":
                        return started, run, completed
                    await asyncio.sleep(0.01)
                raise AssertionError("background run did not finish")

        started, running, completed = asyncio.run(run_case())

        self.assertEqual(started["status"], "accepted")
        self.assertIsNotNone(started["run_id"])
        self.assertEqual(running["status"], "running")
        self.assertIn(running["targets"][0]["status"], {"pending", "running"})
        self.assertTrue(running["events"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["notification"]["status"], "SKIPPED")

    def test_run_now_reuses_existing_running_job(self):
        from core import cron_manager
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="duplicate inspection",
            password="secret",
            job_id="test_job_duplicate_run",
        )

        class FakeTask:
            def done(self):
                return False

        cron_manager._RUNNING_INSPECTIONS[job_id] = {
            "task": FakeTask(),
            "run_id": "run-existing",
            "started_at": "2026-05-12T00:00:00+00:00",
        }

        result = asyncio.run(CronManager.run_job_now(job_id))

        self.assertEqual(result["status"], "running")
        self.assertEqual(result["run_id"], "run-existing")
        self.assertEqual(result["message"], "该计划已有巡检正在执行。")

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
        self.assertIn("请不要自行调用 `send_notification`", headless.await_args.args[1])
        disconnect.assert_called_once_with("sid-cron-skill")

    def test_trigger_prompt_uses_inspection_cycle_and_depth(self):
        from connections.ssh_manager import ssh_manager
        from core import cron_manager
        from core.dispatcher import dispatcher

        with (
            patch.object(dispatcher, "skills_registry", {}),
            patch.object(ssh_manager, "connect", return_value={"success": True, "session_id": "sid-cron-cycle"}),
            patch.object(ssh_manager, "disconnect"),
            patch("core.agent.headless_agent_chat", new_callable=AsyncMock, return_value="ok") as headless,
        ):
            asyncio.run(
                cron_manager._trigger_proactive_inspection(
                    job_id="test_job_cycle_prompt",
                    host="10.0.0.10",
                    agent_profile="default",
                    message="inspect",
                    username="root",
                    password="secret",
                    inspection_cycle="monthly",
                    inspection_depth="deep",
                )
            )

        prompt = headless.await_args.args[1]
        self.assertIn("巡检周期：月巡检", prompt)
        self.assertIn("巡检深度：深度巡检", prompt)
        self.assertIn("容量预测", prompt)
        self.assertIn("最近 30 天", prompt)

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
            run_response = asyncio.run(inspection_job_routes.run_cron_job_now(job_id))
            list_response = asyncio.run(inspection_run_routes.list_cron_job_runs(job_id))
            detail_response = asyncio.run(
                inspection_run_routes.get_cron_job_run(
                    run_response.data["result"]["run_id"]
                )
            )

        self.assertEqual(run_response.data["result"]["status"], "completed")
        self.assertEqual(len(list_response.data["runs"]), 1)
        self.assertEqual(detail_response.data["run"]["job_id"], job_id)
        self.assertEqual(detail_response.data["run"]["targets"][0]["host"], "10.0.0.10")

    def test_inspection_run_report_can_be_deleted(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("delete_run")):
            run = inspection_results.record_run(
                job_id="job-delete-report",
                status="completed",
                target_scope="asset",
                scope_value="7",
                message="delete report",
                targets=[{"host": "10.0.0.10", "status": "success"}],
            )
            deleted = asyncio.run(inspection_run_routes.delete_inspection_run(run["id"]))
            remaining = inspection_results.list_runs(job_id="job-delete-report")

        self.assertEqual(deleted.status, "success")
        self.assertEqual(deleted.data["run_id"], run["id"])
        self.assertEqual(remaining, [])

    def test_delete_missing_inspection_run_report_maps_to_404(self):
        from fastapi import HTTPException
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("delete_missing")):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(inspection_run_routes.delete_inspection_run("run_missing"))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "巡检报告不存在")

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
            summary_response = asyncio.run(inspection_run_routes.get_cron_run_summary())

        summary = summary_response.data["summary"]
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["success_rate"], 50.0)
        self.assertEqual(summary["recent_failures"][0]["job_id"], "job-fail")

    def test_inspection_run_store_retries_windows_replace_permission_error(self):
        from core import inspection_results

        store_path = self._run_store_path("replace_retry")
        original_replace = Path.replace
        replace_failures = []

        def flaky_replace(path: Path, target: Path):
            if target == store_path and not replace_failures:
                replace_failures.append(str(path))
                raise PermissionError("locked")
            return original_replace(path, target)

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", store_path),
            patch.object(inspection_results, "_SAVE_REPLACE_RETRY_DELAY_SECONDS", 0),
            patch.object(Path, "replace", flaky_replace),
        ):
            run = inspection_results.record_run(
                job_id="job-retry",
                status="completed",
                target_scope="asset",
                scope_value=None,
                message="ok",
                targets=[{"host": "10.0.0.10", "status": "success"}],
            )

        self.assertEqual(run["job_id"], "job-retry")
        self.assertEqual(len(replace_failures), 1)
        self.assertTrue(store_path.exists())

    def test_running_inspection_run_is_recorded_then_updated(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("running_update")):
            run = inspection_results.record_run(
                job_id="job-running",
                status="running",
                target_scope="asset",
                scope_value="20",
                message="oracle inspection",
                targets=[{"asset_id": 20, "host": "10.0.0.20", "status": "pending"}],
                started_at="2026-05-12T00:00:00+00:00",
                completed_at=None,
            )
            running = inspection_results.get_run(run["id"])
            updated = inspection_results.update_run(
                run["id"],
                status="failed",
                targets=[{"asset_id": 20, "host": "10.0.0.20", "status": "error", "error": "timeout"}],
                completed_at="2026-05-12T00:01:00+00:00",
            )
            stored = inspection_results.get_run(run["id"])

        self.assertEqual(running["status"], "running")
        self.assertIsNone(running["completed_at"])
        self.assertEqual(updated["status"], "failed")
        self.assertEqual(stored["target_count"], 1)
        self.assertEqual(stored["duration_ms"], 60000)

    def test_oracle_inspection_timeout_defaults_to_thirty_minutes(self):
        from core.cron_manager import _inspection_timeout_seconds

        self.assertEqual(_inspection_timeout_seconds("oracle", "oracle"), 1800.0)
        self.assertEqual(_inspection_timeout_seconds("mysql", "mysql"), 1200.0)
        self.assertEqual(_inspection_timeout_seconds("ssh", "linux"), 600.0)
        self.assertEqual(_inspection_timeout_seconds("oracle", "oracle", {"inspection_timeout_seconds": 90}), 90.0)

    def test_inspection_report_detail_export_and_asset_filter_are_secret_free(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("report")):
            related_run = inspection_results.record_run(
                job_id="job-report",
                status="completed",
                target_scope="tag",
                scope_value="prod",
                message="previous report",
                targets=[
                    {
                        "asset_id": 101,
                        "host": "10.0.0.101",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "status": "success",
                        "result": "ok",
                    },
                ],
                started_at="2026-05-11T00:00:00+00:00",
                completed_at="2026-05-11T00:01:00+00:00",
            )
            run = inspection_results.record_run(
                job_id="job-report",
                status="partial",
                target_scope="tag",
                scope_value="prod",
                message="daily report",
                events=[
                    {
                        "time": "2026-05-12T00:00:00+00:00",
                        "type": "run_started",
                        "message": "巡检运行已启动，等待处理 2 个目标。",
                        "status": "running",
                    },
                    {
                        "time": "2026-05-12T00:01:00+00:00",
                        "type": "target_completed",
                        "message": "目标 10.0.0.101 巡检完成。",
                        "status": "success",
                    },
                    {
                        "time": "2026-05-12T00:02:00+00:00",
                        "type": "target_failed",
                        "message": "目标 10.0.0.102 巡检失败。",
                        "status": "error",
                    },
                ],
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
            inspection_results.update_run(
                run["id"],
                notification={"status": "ERROR", "message": "企业微信发送失败"},
            )
            report_response = asyncio.run(
                inspection_run_routes.get_inspection_run_report(run["id"])
            )
            export_response = asyncio.run(
                inspection_run_routes.export_inspection_run_report(
                    run["id"],
                    format="markdown",
                )
            )
            html_export_response = asyncio.run(
                inspection_run_routes.export_inspection_run_report(
                    run["id"],
                    format="html",
                )
            )
            filtered_response = asyncio.run(
                inspection_run_routes.list_inspection_runs(asset_id=102)
            )

        report = report_response.data["report"]
        self.assertEqual(report["run_id"], run["id"])
        self.assertEqual(report["summary"]["target_count"], 2)
        self.assertEqual(report["summary"]["success_count"], 1)
        self.assertEqual(report["summary"]["error_count"], 1)
        self.assertEqual(report["trace"]["kind"], "inspection_run")
        self.assertEqual(report["trace"]["counters"]["targets"], 2)
        self.assertEqual(report["trace"]["counters"]["success"], 1)
        self.assertEqual(report["trace"]["counters"]["error"], 1)
        self.assertEqual(report["trace"]["phases"][1]["id"], "targets")
        self.assertEqual(report["trace"]["phases"][1]["status"], "partial")
        self.assertEqual(report["trace"]["phases"][2]["id"], "notification")
        self.assertEqual(report["trace"]["phases"][2]["status"], "failed")
        self.assertEqual(report["score"]["profile"], "mixed")
        self.assertLess(report["score"]["score"], 100)
        self.assertEqual(len(report["score"]["target_scores"]), 2)
        self.assertTrue(report["score"]["deductions"])
        self.assertEqual(filtered_response.data["runs"][0]["id"], run["id"])
        self.assertEqual(len(filtered_response.data["runs"][0]["targets"]), 1)
        self.assertEqual(filtered_response.data["runs"][0]["targets"][0]["asset_id"], 102)
        markdown = export_response.data["content"]
        self.assertIn("# 巡检报告", markdown)
        self.assertIn("## 健康评分", markdown)
        self.assertIn("## AIOps Run Trace", markdown)
        self.assertIn("通知发送", markdown)
        self.assertIn("10.0.0.102", markdown)
        html = html_export_response.data["content"]
        self.assertEqual(html_export_response.data["content_type"], "text/html")
        self.assertIn("<!doctype html>", html)
        self.assertIn('href="#score"', html)
        self.assertIn('id="targets"', html)
        self.assertIn('id="report-index"', html)
        self.assertIn(f'href="#report-{related_run["id"]}"', html)
        self.assertIn(f'id="report-{related_run["id"]}"', html)
        self.assertIn(related_run["id"], html)
        self.assertNotIn("/api/v1/inspection-runs/", html)
        self.assertIn("保存到本地后不依赖 OpsCore 服务", html)
        self.assertIn("当前", html)
        self.assertIn("健康评分", html)
        self.assertIn("AIOps Run Trace", html)
        dumped = json.dumps({"report": report, "markdown": markdown, "html": html}, ensure_ascii=False)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_inspection_report_scores_oracle_risk_by_profile(self):
        from core import inspection_results

        with patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("oracle-score")):
            run = inspection_results.record_run(
                job_id="job-oracle-score",
                status="completed",
                target_scope="asset",
                scope_value="201",
                message="oracle report",
                targets=[
                    {
                        "asset_id": 201,
                        "host": "10.0.0.201",
                        "asset_type": "oracle",
                        "protocol": "oracle",
                        "status": "success",
                        "result": "总体健康评分：70/100。ORA-00257 archiver stuck, tablespace usage 96%, no backup, 需立即扩容",
                    },
                    {
                        "asset_id": 202,
                        "host": "10.0.0.202",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "status": "success",
                        "result": "ok",
                    },
                ],
            )
            report = inspection_results.build_report(run["id"])

        self.assertIsNotNone(report)
        score = report["score"]
        oracle_score = score["target_scores"][0]
        linux_score = score["target_scores"][1]
        self.assertEqual(oracle_score["profile"], "oracle")
        self.assertLess(oracle_score["score"], linux_score["score"])
        self.assertLessEqual(oracle_score["score"], 70)
        self.assertIn("Oracle 归档或表空间高风险", json.dumps(oracle_score, ensure_ascii=False))

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
        self.assertNotIn("retry_count", trigger.await_args_list[0].kwargs)
        self.assertNotIn("_opscore_paused", trigger.await_args_list[0].kwargs)
        self.assertGreaterEqual(run["duration_ms"], 0)
        self.assertEqual(run["targets"][0]["attempts"], 2)
        self.assertEqual(run["targets"][0]["status"], "success")
        self.assertGreaterEqual(run["targets"][0]["duration_ms"], 0)

    def test_run_now_sends_backend_completion_notification(self):
        from core import inspection_results
        from core.cron_manager import CronManager

        job_id = CronManager.add_inspection_job(
            cron_expr="0 9 * * *",
            host="10.0.0.10",
            username="root",
            agent_profile="default",
            message="notify inspection",
            password="secret",
            job_id="test_job_notify",
            notification_channel="wechat",
        )

        with (
            patch.object(inspection_results, "INSPECTION_RUN_STORE_PATH", self._run_store_path("notify")),
            patch("core.cron_manager._trigger_proactive_inspection", new_callable=AsyncMock, return_value="inspection ok"),
            patch("core.notifier.send_notification", return_value={"status": "SUCCESS", "message": "sent"}) as send_notification,
        ):
            result = asyncio.run(CronManager.run_job_now(job_id))
            run = inspection_results.get_run(result["run_id"])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["notification"]["status"], "SUCCESS")
        self.assertEqual(run["notification"]["status"], "SUCCESS")
        self.assertEqual(run["events"][-1]["type"], "notification_completed")
        send_notification.assert_called_once()
        channel, title, content = send_notification.call_args.args
        self.assertEqual(channel, "wechat")
        self.assertIn("10.0.0.10", title)
        self.assertIn("inspection ok", content)

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
            response = asyncio.run(dashboard_routes.get_dashboard_inspection_run_trend())

        point = response.data["points"][0]
        self.assertEqual(point["date"], "2026-04-27")
        self.assertEqual(point["total_runs"], 2)
        self.assertEqual(point["success_rate"], 50.0)
        self.assertEqual(point["avg_duration_ms"], 2000.0)
        self.assertEqual(point["target_error"], 1)


if __name__ == "__main__":
    unittest.main()
