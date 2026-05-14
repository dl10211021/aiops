from core.aiops_task_runtime import AIOpsTaskRuntime, task_runtime_snapshot


class FakeTask:
    def __init__(self, done: bool = False):
        self._done = done

    def done(self):
        return self._done


def test_task_runtime_tracks_progress_and_cancel_state():
    runtime = AIOpsTaskRuntime(
        task_id="task-1",
        owner_id="job-1",
        run_id="run-1",
        task=FakeTask(False),
        started_at="2026-05-13T00:00:00+00:00",
        progress_total=4,
    )

    runtime.mark_progress(
        stage="target_running",
        message="正在巡检目标 db.local。",
        current=2,
        total=4,
        target={"asset_id": 7, "host": "db.local", "password": "secret"},
    )
    snapshot = runtime.snapshot()

    assert snapshot["running"] is True
    assert snapshot["current_stage"] == "target_running"
    assert snapshot["progress_current"] == 2
    assert snapshot["progress_total"] == 4
    assert snapshot["progress_percent"] == 50
    assert snapshot["current_target"]["asset_id"] == 7
    assert "password" not in snapshot["current_target"]

    runtime.request_cancel("用户请求取消。")
    cancelling = task_runtime_snapshot(runtime)

    assert cancelling["status"] == "cancelling"
    assert cancelling["current_stage"] == "cancelling"
    assert cancelling["cancel_requested_at"]


def test_task_runtime_snapshot_keeps_legacy_dict_compatibility():
    legacy = {
        "task": FakeTask(False),
        "run_id": "run-legacy",
        "started_at": "2026-05-13T00:00:00+00:00",
    }

    assert task_runtime_snapshot(legacy)["run_id"] == "run-legacy"
