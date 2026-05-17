import asyncio
import unittest

from core.agent_task_dispatch import dispatch_group_tasks


class AgentTaskDispatchTests(unittest.TestCase):
    def test_dispatches_valid_tasks_to_injected_runner(self):
        calls = []

        async def runner(session_id, task_description, allow_mod):
            calls.append((session_id, task_description, allow_mod))
            return f"done:{session_id}:{task_description}:{allow_mod}"

        results = asyncio.run(
            dispatch_group_tasks(
                [{"target_session_id": "sid-1", "task_description": "检查磁盘"}],
                True,
                task_runner=runner,
                active_sessions={"sid-1": {"info": {"remark": "数据库", "allow_modifications": True}}},
            )
        )

        self.assertEqual(calls, [("sid-1", "检查磁盘", True)])
        self.assertEqual(
            results,
            [
                {
                    "session_id": "sid-1",
                    "status": "SUCCESS",
                    "allow_modifications": True,
                    "session_mode": "readwrite",
                    "permission_boundary": {
                        "scope": "group",
                        "parent_mode": "readwrite",
                        "target_mode": "readwrite",
                        "effective_mode": "readwrite",
                        "downgraded": False,
                        "reason": "allowed",
                    },
                    "report": "done:sid-1:检查磁盘:True",
                }
            ],
        )

    def test_child_task_cannot_exceed_parent_or_target_permissions(self):
        calls = []

        async def runner(session_id, task_description, allow_mod):
            calls.append((session_id, allow_mod))
            return f"mode:{allow_mod}"

        parent_readwrite_results = asyncio.run(
            dispatch_group_tasks(
                [{"target_session_id": "sid-readonly", "task_description": "检查"}],
                True,
                task_runner=runner,
                active_sessions={"sid-readonly": {"info": {"allow_modifications": False}}},
            )
        )
        parent_readonly_results = asyncio.run(
            dispatch_group_tasks(
                [{"target_session_id": "sid-readwrite", "task_description": "检查"}],
                False,
                task_runner=runner,
                active_sessions={"sid-readwrite": {"info": {"allow_modifications": True}}},
            )
        )

        self.assertEqual(calls, [("sid-readonly", False), ("sid-readwrite", False)])
        self.assertFalse(parent_readwrite_results[0]["allow_modifications"])
        self.assertEqual(parent_readwrite_results[0]["session_mode"], "readonly")
        self.assertEqual(
            parent_readwrite_results[0]["permission_boundary"],
            {
                "scope": "group",
                "parent_mode": "readwrite",
                "target_mode": "readonly",
                "effective_mode": "readonly",
                "downgraded": True,
                "reason": "target_readonly",
            },
        )
        self.assertFalse(parent_readonly_results[0]["allow_modifications"])
        self.assertEqual(parent_readonly_results[0]["session_mode"], "readonly")
        self.assertEqual(
            parent_readonly_results[0]["permission_boundary"],
            {
                "scope": "group",
                "parent_mode": "readonly",
                "target_mode": "readwrite",
                "effective_mode": "readonly",
                "downgraded": False,
                "reason": "parent_readonly",
            },
        )

    def test_dispatch_result_preserves_explicit_global_scope_boundary(self):
        async def runner(session_id, task_description, allow_mod):
            return f"mode:{allow_mod}"

        results = asyncio.run(
            dispatch_group_tasks(
                [
                    {
                        "target_session_id": "sid-1",
                        "task_description": "全局检查",
                        "dispatch_scope": "global",
                    }
                ],
                True,
                task_runner=runner,
                active_sessions={"sid-1": {"info": {"allow_modifications": True}}},
            )
        )

        self.assertEqual(results[0]["permission_boundary"]["scope"], "global")
        self.assertEqual(results[0]["permission_boundary"]["effective_mode"], "readwrite")
        self.assertFalse(results[0]["permission_boundary"]["downgraded"])

    def test_dispatch_result_preserves_observability_metadata(self):
        async def runner(session_id, task_description, allow_mod):
            return f"done:{session_id}"

        results = asyncio.run(
            dispatch_group_tasks(
                [
                    {
                        "target_session_id": "sid-1",
                        "task_description": "检查订单库",
                        "dispatch_scope": "global",
                        "observability_task_id": "inv-1-summary",
                        "investigation_id": "inv-1",
                    }
                ],
                False,
                task_runner=runner,
                active_sessions={"sid-1": {"info": {"allow_modifications": False}}},
            )
        )

        self.assertEqual(results[0]["observability_task_id"], "inv-1-summary")
        self.assertEqual(results[0]["investigation_id"], "inv-1")

    def test_rejects_invalid_task_definition_before_running(self):
        async def runner(session_id, task_description, allow_mod):
            raise AssertionError("runner should not be called")

        results = asyncio.run(
            dispatch_group_tasks(
                [{"target_session_id": "sid-1"}],
                False,
                task_runner=runner,
                active_sessions={},
            )
        )

        self.assertEqual(
            results,
            [
                {
                    "session_id": "sid-1",
                    "status": "ERROR",
                    "error": "Invalid task definition",
                }
            ],
        )

    def test_returns_error_for_runner_exception(self):
        async def runner(session_id, task_description, allow_mod):
            raise RuntimeError("boom")

        results = asyncio.run(
            dispatch_group_tasks(
                [{"target_session_id": "sid-1", "task_description": "检查"}],
                False,
                task_runner=runner,
                active_sessions={},
            )
        )

        self.assertEqual(results[0]["session_id"], "sid-1")
        self.assertEqual(results[0]["status"], "ERROR")
        self.assertEqual(results[0]["error"], "跨域协同异常: boom")

    def test_returns_error_for_runner_timeout(self):
        async def runner(session_id, task_description, allow_mod):
            await asyncio.sleep(0.05)
            return "late"

        results = asyncio.run(
            dispatch_group_tasks(
                [{"target_session_id": "sid-1", "task_description": "检查"}],
                False,
                task_runner=runner,
                active_sessions={},
                timeout_seconds=0.001,
            )
        )

        self.assertEqual(results[0]["session_id"], "sid-1")
        self.assertEqual(results[0]["status"], "ERROR")
        self.assertEqual(results[0]["error"], "跨域协同超时 (0.001秒) 被强行中断。")


if __name__ == "__main__":
    unittest.main()
