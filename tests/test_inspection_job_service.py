import asyncio
import unittest

from core.inspection_job_service import (
    InspectionJobServiceError,
    create_inspection_job_record,
    list_inspection_job_records,
    pause_inspection_job_record,
    remove_inspection_job_record,
    resume_inspection_job_record,
    run_inspection_job_record_now,
    update_inspection_job_record,
)


class FakeInspectionJobManager:
    jobs = {"job-1": {"id": "job-1", "status": "scheduled"}}
    added_kwargs = None
    removed = []

    @classmethod
    def add_inspection_job(cls, **kwargs):
        cls.added_kwargs = kwargs
        cls.jobs["job-new"] = {"id": "job-new", "status": "scheduled"}
        return "job-new"

    @classmethod
    def get_job(cls, job_id: str):
        return cls.jobs[job_id]

    @classmethod
    def get_all_jobs(cls):
        return list(cls.jobs.values())

    @classmethod
    def remove_job(cls, job_id: str):
        if job_id not in cls.jobs:
            raise KeyError(job_id)
        cls.removed.append(job_id)

    @classmethod
    def update_job(cls, job_id: str, **kwargs):
        if job_id not in cls.jobs:
            raise KeyError(job_id)
        cls.jobs[job_id] = {"id": job_id, **kwargs}
        return cls.jobs[job_id]

    @classmethod
    def pause_job(cls, job_id: str):
        if job_id not in cls.jobs:
            raise KeyError(job_id)
        cls.jobs[job_id]["status"] = "paused"
        return cls.jobs[job_id]

    @classmethod
    def resume_job(cls, job_id: str):
        if job_id not in cls.jobs:
            raise KeyError(job_id)
        cls.jobs[job_id]["status"] = "scheduled"
        return cls.jobs[job_id]

    @classmethod
    async def run_job_now(cls, job_id: str):
        if job_id not in cls.jobs:
            raise KeyError(job_id)
        return {"job_id": job_id, "status": "completed"}


class TestInspectionJobService(unittest.TestCase):
    def setUp(self):
        FakeInspectionJobManager.jobs = {"job-1": {"id": "job-1", "status": "scheduled"}}
        FakeInspectionJobManager.added_kwargs = None
        FakeInspectionJobManager.removed = []

    def _payload(self):
        return {
            "cron_expr": "0 9 * * *",
            "host": "db.local",
            "username": "ops",
            "agent_profile": "default",
            "message": "巡检",
            "password": None,
            "private_key_path": None,
            "asset_id": 1,
            "target_scope": "asset",
            "scope_value": None,
            "template_id": "linux-basic",
            "notification_channel": "auto",
            "retry_count": 1,
            "active_skills": ["linux"],
        }

    def test_create_job_returns_job_id_and_job(self):
        result = create_inspection_job_record(self._payload(), FakeInspectionJobManager)

        self.assertEqual(result["job_id"], "job-new")
        self.assertEqual(result["job"]["id"], "job-new")
        self.assertEqual(FakeInspectionJobManager.added_kwargs["asset_id"], 1)

    def test_list_update_pause_resume_and_run_job(self):
        self.assertEqual(len(list_inspection_job_records(FakeInspectionJobManager)), 1)

        updated = update_inspection_job_record("job-1", self._payload(), FakeInspectionJobManager)
        paused = pause_inspection_job_record("job-1", FakeInspectionJobManager)
        self.assertEqual(paused["status"], "paused")
        resumed = resume_inspection_job_record("job-1", FakeInspectionJobManager)
        result = asyncio.run(run_inspection_job_record_now("job-1", FakeInspectionJobManager))

        self.assertEqual(updated["host"], "db.local")
        self.assertEqual(resumed["status"], "scheduled")
        self.assertEqual(result["status"], "completed")

    def test_remove_missing_job_maps_to_404(self):
        with self.assertRaises(InspectionJobServiceError) as ctx:
            remove_inspection_job_record("missing", FakeInspectionJobManager)

        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_validation_error_maps_to_400(self):
        class InvalidManager(FakeInspectionJobManager):
            @classmethod
            def update_job(cls, job_id: str, **kwargs):
                raise ValueError("bad cron")

        with self.assertRaises(InspectionJobServiceError) as ctx:
            update_inspection_job_record("job-1", self._payload(), InvalidManager)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "bad cron")
