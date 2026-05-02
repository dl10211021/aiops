import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import approval_queue
from core.session_interaction_service import (
    SessionInteractionServiceError,
    approve_session_tool_call,
    submit_user_interaction_response,
)


class FakeDispatcher:
    def __init__(self):
        self.pending_approvals = {}
        self.pending_interactions = {}


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


class TestSessionInteractionService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_session_interaction_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_session_interaction_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "approvals.json"

    def test_approve_pending_future_sets_result_and_updates_audit(self):
        dispatcher = FakeDispatcher()
        future = FakeFuture()
        dispatcher.pending_approvals["call-1"] = future
        active_sessions = {"sid-1": {"info": {"auto_approve_all": False}}}

        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("pending")):
            approval_queue.record_approval_request(
                tool_call_id="call-1",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="高危服务重启",
                context={"host": "ops.local"},
            )
            result = approve_session_tool_call(
                active_sessions,
                "sid-1",
                "call-1",
                approved=True,
                auto_approve_all=True,
                operator="ops",
                note="approved",
                dispatcher=dispatcher,
            )
            approval = approval_queue.get_approval_request("call-1")

        self.assertEqual(result["message"], "Approval action submitted.")
        self.assertFalse(result["include_approval"])
        self.assertTrue(active_sessions["sid-1"]["info"]["auto_approve_all"])
        self.assertTrue(future.done())
        self.assertTrue(future.result())
        self.assertEqual(approval["status"], "approved")
        self.assertEqual(approval["operator"], "ops")

    def test_approve_orphaned_approval_record_returns_record_payload(self):
        dispatcher = FakeDispatcher()
        active_sessions = {}

        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("record")):
            approval_queue.record_approval_request(
                tool_call_id="call-2",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="高危服务重启",
                context={"host": "ops.local"},
            )
            result = approve_session_tool_call(
                active_sessions,
                "sid-1",
                "call-2",
                approved=False,
                operator="ops",
                dispatcher=dispatcher,
            )

        self.assertEqual(result["message"], "Approval action recorded.")
        self.assertTrue(result["include_approval"])
        self.assertEqual(result["approval"]["status"], "rejected")

    def test_missing_tool_call_maps_to_404(self):
        dispatcher = FakeDispatcher()
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("missing")):
            with self.assertRaises(SessionInteractionServiceError) as ctx:
                approve_session_tool_call(
                    {},
                    "sid-1",
                    "missing",
                    approved=True,
                    dispatcher=dispatcher,
                )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_submit_user_interaction_response_resolves_matching_future(self):
        dispatcher = FakeDispatcher()
        future = FakeFuture()
        dispatcher.pending_interactions["interaction-1"] = {
            "future": future,
            "session_id": "sid-1",
        }

        result = submit_user_interaction_response(
            "sid-1",
            "interaction-1",
            value="blue team",
            label="蓝队方案",
            dispatcher=dispatcher,
        )

        self.assertEqual(result, {"value": "blue team", "label": "蓝队方案"})
        self.assertTrue(future.done())
        self.assertEqual(future.result()["value"], "blue team")

    def test_wrong_session_interaction_maps_to_404_without_resolving(self):
        dispatcher = FakeDispatcher()
        future = FakeFuture()
        dispatcher.pending_interactions["interaction-2"] = {
            "future": future,
            "session_id": "sid-owner",
        }

        with self.assertRaises(SessionInteractionServiceError) as ctx:
            submit_user_interaction_response(
                "sid-other",
                "interaction-2",
                value="should-not-submit",
                dispatcher=dispatcher,
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertFalse(future.done())

    def test_uses_default_dispatcher_when_not_injected(self):
        dispatcher = FakeDispatcher()
        future = FakeFuture()
        dispatcher.pending_interactions["interaction-default"] = {
            "future": future,
            "session_id": "sid-1",
        }

        with patch("core.session_interaction_service.dispatcher_module.dispatcher", dispatcher):
            result = submit_user_interaction_response(
                "sid-1",
                "interaction-default",
                value="ack",
                label="确认",
            )

        self.assertEqual(result, {"value": "ack", "label": "确认"})
        self.assertTrue(future.done())
