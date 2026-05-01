import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import approval_queue
from core.approval_request_service import (
    ApprovalRequestServiceError,
    decide_approval_request_record,
    get_approval_request_record,
    list_approval_request_records,
)


class FakeDispatcher:
    def __init__(self):
        self.pending_approvals = {}


class FakeFuture:
    def __init__(self):
        self._done = False
        self._result = None

    def done(self):
        return self._done

    def set_result(self, result):
        self._done = True
        self._result = result

    def result(self):
        return self._result


class TestApprovalRequestService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_approval_request_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_approval_request_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "approvals.json"

    def test_list_get_and_decide_approval_request_records(self):
        dispatcher = FakeDispatcher()
        future = FakeFuture()
        dispatcher.pending_approvals["call-1"] = future

        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("records")):
            approval_queue.record_approval_request(
                tool_call_id="call-1",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                context={"host": "db.local"},
                reason="高危服务重启",
            )
            listed = list_approval_request_records(status="pending")
            loaded = get_approval_request_record("call-1")
            decided = decide_approval_request_record(
                dispatcher,
                "call-1",
                approved=True,
                operator="ops",
                note="approved",
            )

        self.assertEqual(listed[0]["id"], "call-1")
        self.assertEqual(loaded["status"], "pending")
        self.assertEqual(decided["status"], "approved")
        self.assertTrue(future.done())
        self.assertTrue(future.result())

    def test_missing_approval_maps_to_404(self):
        dispatcher = FakeDispatcher()
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("missing")):
            with self.assertRaises(ApprovalRequestServiceError) as get_ctx:
                get_approval_request_record("missing")
            with self.assertRaises(ApprovalRequestServiceError) as decide_ctx:
                decide_approval_request_record(dispatcher, "missing", approved=False)

        self.assertEqual(get_ctx.exception.status_code, 404)
        self.assertEqual(decide_ctx.exception.status_code, 404)
