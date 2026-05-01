import shutil
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import approval_queue
from core.approval_execution_service import (
    ApprovalExecutionServiceError,
    execute_approval_request_action,
)


class TestApprovalExecutionService(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_approval_execution_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_approval_execution_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "approvals.json"

    def _record_rollback_approval(self, approval_id: str = "call-rollback") -> dict:
        return approval_queue.record_approval_request(
            tool_call_id=approval_id,
            session_id="api",
            tool_name="rollback_skill",
            args={
                "skill_id": "safe-skill",
                "file_name": "SKILL.md",
                "version_id": "SKILL.md.20260428010101.1.bak",
            },
            reason="用户请求回滚平台技能文件，必须人工审批并审计。",
            context={"asset_type": "platform", "protocol": "api"},
        )

    async def test_execute_approved_rollback_approval_injects_executor_and_reloads_record(self):
        calls = []

        async def fake_executor(skill_id: str, file_name: str, version_id: str, approval_id: str):
            calls.append((skill_id, file_name, version_id, approval_id))
            approval_queue.record_approval_execution(
                approval_id,
                (
                    '{"status":"SUCCESS","skill_id":"safe-skill",'
                    '"file_name":"SKILL.md","version_id":"SKILL.md.20260428010101.1.bak"}'
                ),
            )
            return SimpleNamespace(
                status="success",
                message="rollback complete",
                data={"version_id": version_id},
            )

        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("execute")):
            self._record_rollback_approval("call-1")
            approval_queue.resolve_approval_request("call-1", approved=True, operator="ops")
            result = await execute_approval_request_action("call-1", fake_executor)

        self.assertEqual(
            calls,
            [("safe-skill", "SKILL.md", "SKILL.md.20260428010101.1.bak", "call-1")],
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.message, "rollback complete")
        self.assertEqual(result.result["version_id"], "SKILL.md.20260428010101.1.bak")
        self.assertEqual(result.approval["execution"]["artifacts"]["version_id"], "SKILL.md.20260428010101.1.bak")

    async def test_rejects_missing_pending_executed_wrong_tool_and_incomplete_args(self):
        async def should_not_run(*_args):
            raise AssertionError("executor should not run")

        with patch.object(approval_queue, "APPROVAL_STORE_PATH", self._store_path("invalid")):
            with self.assertRaises(ApprovalExecutionServiceError) as missing_ctx:
                await execute_approval_request_action("missing", should_not_run)

            self._record_rollback_approval("pending")
            with self.assertRaises(ApprovalExecutionServiceError) as pending_ctx:
                await execute_approval_request_action("pending", should_not_run)

            self._record_rollback_approval("executed")
            approval_queue.resolve_approval_request("executed", approved=True, operator="ops")
            approval_queue.record_approval_execution("executed", '{"status":"SUCCESS"}')
            with self.assertRaises(ApprovalExecutionServiceError) as executed_ctx:
                await execute_approval_request_action("executed", should_not_run)

            approval_queue.record_approval_request(
                tool_call_id="wrong-tool",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="高危服务重启",
                context={"host": "ops.local"},
            )
            approval_queue.resolve_approval_request("wrong-tool", approved=True, operator="ops")
            with self.assertRaises(ApprovalExecutionServiceError) as wrong_tool_ctx:
                await execute_approval_request_action("wrong-tool", should_not_run)

            approval_queue.record_approval_request(
                tool_call_id="incomplete",
                session_id="api",
                tool_name="rollback_skill",
                args={"skill_id": "safe-skill", "file_name": "SKILL.md"},
                reason="用户请求回滚平台技能文件，必须人工审批并审计。",
                context={"asset_type": "platform", "protocol": "api"},
            )
            approval_queue.resolve_approval_request("incomplete", approved=True, operator="ops")
            with self.assertRaises(ApprovalExecutionServiceError) as incomplete_ctx:
                await execute_approval_request_action("incomplete", should_not_run)

        self.assertEqual(missing_ctx.exception.status_code, 404)
        self.assertEqual(pending_ctx.exception.status_code, 409)
        self.assertEqual(executed_ctx.exception.status_code, 409)
        self.assertEqual(wrong_tool_ctx.exception.status_code, 422)
        self.assertEqual(incomplete_ctx.exception.status_code, 422)
