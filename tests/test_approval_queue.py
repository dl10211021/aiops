import asyncio
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from api import routes


class TestApprovalQueue(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_approval_queue_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_approval_queue_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "approvals.json"

    def test_record_approval_request_redacts_args_and_lists_pending(self):
        from core import approval_queue

        store_path = self._store_path("record")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            request = approval_queue.record_approval_request(
                tool_call_id="call-1",
                session_id="sid-1",
                tool_name="db_execute_query",
                args={"sql": "UPDATE users SET password='secret' WHERE id=1", "password": "plain-secret"},
                reason="检测到数据库数据修改或结构变更操作。",
                context={"host": "10.0.0.1", "asset_type": "mysql", "protocol": "mysql", "password": "asset-secret"},
                timeout_seconds=300,
            )
            pending = approval_queue.list_approval_requests(status="pending")

        self.assertEqual(request["status"], "pending")
        self.assertEqual(pending[0]["id"], "call-1")
        self.assertEqual(pending[0]["args"]["password"], "***")
        self.assertNotIn("asset-secret", str(pending[0]))

    def test_evolve_skill_approval_records_summary_instead_of_full_content(self):
        from core import approval_queue

        content = "---\nname: safe-skill\ndescription: demo\n---\n\n" + ("line\n" * 120)
        store_path = self._store_path("skill_change")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            request = approval_queue.record_approval_request(
                tool_call_id="call-skill",
                session_id="sid-skill",
                tool_name="evolve_skill",
                args={"skill_id": "safe-skill", "file_name": "SKILL.md", "content": content},
                reason="AI 试图创建或修改平台技能，必须人工审批并审计。",
                context={"session_id": "sid-skill", "asset_type": "virtual", "protocol": "virtual"},
            )

        skill_change = request["metadata"]["skill_change"]
        self.assertEqual(skill_change["skill_id"], "safe-skill")
        self.assertEqual(skill_change["file_name"], "SKILL.md")
        self.assertTrue(skill_change["validation"]["valid"])
        self.assertEqual(request["args"]["content"]["chars"], len(content))
        self.assertNotEqual(request["args"]["content"], content)
        self.assertNotIn("line\n" * 80, str(request))

    def test_rollback_skill_approval_records_target_metadata(self):
        from core import approval_queue

        store_path = self._store_path("rollback")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            request = approval_queue.record_approval_request(
                tool_call_id="call-rollback",
                session_id="api",
                tool_name="rollback_skill",
                args={
                    "skill_id": "safe-skill",
                    "file_name": "SKILL.md",
                    "version_id": "SKILL.md.1.bak",
                    "target_file": "D:/tmp/safe-skill/SKILL.md",
                    "version_file": "D:/tmp/safe-skill/.versions/SKILL.md.1.bak",
                },
                reason="用户请求回滚平台技能文件，必须人工审批并审计。",
                context={"asset_type": "platform", "protocol": "api"},
            )

        rollback = request["metadata"]["skill_rollback"]
        self.assertEqual(rollback["skill_id"], "safe-skill")
        self.assertEqual(rollback["file_name"], "SKILL.md")
        self.assertEqual(rollback["version_id"], "SKILL.md.1.bak")

    def test_resolve_approval_request_records_decision(self):
        from core import approval_queue

        store_path = self._store_path("resolve")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            approval_queue.record_approval_request(
                tool_call_id="call-2",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="检测到可能改变 Linux/KVM 系统状态的命令。",
                context={"host": "10.0.0.2", "asset_type": "linux", "protocol": "ssh"},
            )
            resolved = approval_queue.resolve_approval_request(
                "call-2",
                approved=False,
                operator="ops-admin",
                note="变更窗口外拒绝",
            )

        self.assertEqual(resolved["status"], "rejected")
        self.assertEqual(resolved["decision"], "rejected")
        self.assertEqual(resolved["operator"], "ops-admin")
        self.assertEqual(resolved["note"], "变更窗口外拒绝")

    def test_record_approval_execution_attaches_redacted_result_summary(self):
        from core import approval_queue

        store_path = self._store_path("execution")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            approval_queue.record_approval_request(
                tool_call_id="call-exec",
                session_id="sid-1",
                tool_name="evolve_skill",
                args={
                    "skill_id": "safe-skill",
                    "file_name": "SKILL.md",
                    "content": "---\nname: safe-skill\ndescription: demo\n---\n\nbody\n",
                },
                reason="AI 试图创建或修改平台技能，必须人工审批并审计。",
                context={"host": "virtual.local", "asset_type": "virtual", "protocol": "virtual"},
            )
            approval_queue.resolve_approval_request("call-exec", approved=True, operator="ops-admin")
            executed = approval_queue.record_approval_execution(
                "call-exec",
                (
                    '{"status":"SUCCESS","message":"updated",'
                    '"skill_id":"safe-skill","file_name":"SKILL.md",'
                    '"file_path":"D:/tmp/safe-skill/SKILL.md",'
                    '"backup_path":"D:/tmp/safe-skill/.versions/SKILL.md.1.bak",'
                    '"api_key":"sk-testsecret1234567890"}'
                ),
            )

        self.assertEqual(executed["execution"]["status"], "success")
        self.assertIn("updated", executed["execution"]["result_preview"])
        self.assertEqual(executed["execution"]["artifacts"]["skill_id"], "safe-skill")
        self.assertEqual(executed["execution"]["artifacts"]["backup_path"], "D:/tmp/safe-skill/.versions/SKILL.md.1.bak")
        self.assertNotIn("sk-testsecret1234567890", str(executed["execution"]))

    def test_record_approval_execution_rejects_duplicate_result_without_overwriting(self):
        from core import approval_queue

        store_path = self._store_path("duplicate_execution")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            approval_queue.record_approval_request(
                tool_call_id="call-exec-dup",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="检测到可能改变 Linux/KVM 系统状态的命令。",
                context={"host": "10.0.0.2", "asset_type": "linux", "protocol": "ssh"},
            )
            approval_queue.resolve_approval_request("call-exec-dup", approved=True, operator="ops-admin")
            approval_queue.record_approval_execution(
                "call-exec-dup",
                '{"status":"SUCCESS","message":"first execution"}',
            )

            with self.assertRaises(ValueError):
                approval_queue.record_approval_execution(
                    "call-exec-dup",
                    '{"status":"SUCCESS","message":"second execution"}',
                )
            existing = approval_queue.get_approval_request("call-exec-dup")

        self.assertIn("first execution", existing["execution"]["result_preview"])
        self.assertNotIn("second execution", existing["execution"]["result_preview"])

    def test_record_approval_request_rejects_duplicate_id_without_overwriting_audit(self):
        from core import approval_queue

        store_path = self._store_path("duplicate")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            approval_queue.record_approval_request(
                tool_call_id="call-dup",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="检测到可能改变 Linux/KVM 系统状态的命令。",
                context={"host": "10.0.0.2", "asset_type": "linux", "protocol": "ssh"},
            )
            approval_queue.resolve_approval_request("call-dup", approved=True, operator="ops-admin")
            approval_queue.record_approval_execution(
                "call-dup",
                '{"status":"SUCCESS","message":"service restarted"}',
            )

            with self.assertRaises(ValueError):
                approval_queue.record_approval_request(
                    tool_call_id="call-dup",
                    session_id="sid-2",
                    tool_name="linux_execute_command",
                    args={"command": "rm -rf /tmp/demo"},
                    reason="检测到可能改变 Linux/KVM 系统状态的命令。",
                    context={"host": "10.0.0.3", "asset_type": "linux", "protocol": "ssh"},
                )

            existing = approval_queue.get_approval_request("call-dup")

        self.assertEqual(existing["status"], "approved")
        self.assertEqual(existing["operator"], "ops-admin")
        self.assertIn("service restarted", existing["execution"]["result_preview"])
        self.assertNotIn("rm -rf", str(existing))

    def test_pending_approval_expires_to_timeout(self):
        from core import approval_queue

        store_path = self._store_path("timeout")
        with (
            patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path),
            patch.object(approval_queue, "_now", return_value=1_000.0),
        ):
            approval_queue.record_approval_request(
                tool_call_id="call-3",
                session_id="sid-1",
                tool_name="http_api_request",
                args={"method": "POST", "path": "/api/change"},
                reason="HTTP POST 可能改变目标系统状态，需要确认。",
                context={"host": "api.local", "asset_type": "api", "protocol": "http_api"},
                timeout_seconds=30,
            )

        with (
            patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path),
            patch.object(approval_queue, "_now", return_value=1_031.0),
        ):
            timed_out = approval_queue.list_approval_requests(status="timeout")

        self.assertEqual(len(timed_out), 1)
        self.assertEqual(timed_out[0]["status"], "timeout")

    def test_mark_approval_timeout_records_timeout_decision(self):
        from core import approval_queue

        store_path = self._store_path("mark_timeout")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            approval_queue.record_approval_request(
                tool_call_id="call-timeout",
                session_id="sid-1",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="检测到可能改变 Linux/KVM 系统状态的命令。",
                context={"host": "10.0.0.9", "asset_type": "linux", "protocol": "ssh"},
            )
            timed_out = approval_queue.mark_approval_timeout("call-timeout")

        self.assertEqual(timed_out["status"], "timeout")
        self.assertEqual(timed_out["decision"], "timeout")
        self.assertEqual(timed_out["operator"], "system")

    def test_approval_routes_list_and_decide_without_live_future(self):
        from core import approval_queue

        store_path = self._store_path("routes")
        with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
            approval_queue.record_approval_request(
                tool_call_id="call-4",
                session_id="sid-1",
                tool_name="redis_execute_command",
                args={"command": "SET a b"},
                reason="检测到 Redis 写操作或高危命令。",
                context={"host": "redis.local", "asset_type": "redis", "protocol": "redis"},
            )

            listed = asyncio.run(routes.list_approval_requests(status="pending"))
            decision = asyncio.run(
                routes.decide_approval_request(
                    "call-4",
                    routes.ApprovalDecisionRequest(approved=True, operator="ops-admin"),
                )
            )

        self.assertEqual(listed.data["approvals"][0]["id"], "call-4")
        self.assertEqual(decision.data["approval"]["status"], "approved")

    def test_agent_records_approval_request_with_policy_timeout(self):
        from core import agent, approval_queue

        store_path = self._store_path("agent")
        with (
            patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path),
            patch.object(agent, "approval_timeout_seconds", return_value=45),
        ):
            recorded = agent.record_tool_approval_request(
                tool_call_id="call-5",
                session_id="sid-2",
                tool_name="linux_execute_command",
                args={"command": "systemctl restart nginx"},
                reason="检测到可能改变 Linux/KVM 系统状态的命令。",
                context={"session_id": "sid-2", "host": "10.0.0.5", "asset_type": "linux", "protocol": "ssh"},
            )

        self.assertEqual(recorded["id"], "call-5")
        self.assertEqual(recorded["status"], "pending")
        self.assertEqual(recorded["expires_at_ts"] - recorded["requested_at_ts"], 45)


if __name__ == "__main__":
    unittest.main()
