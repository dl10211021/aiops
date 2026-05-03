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
                active_sessions={"sid-1": {"info": {"remark": "数据库"}}},
            )
        )

        self.assertEqual(calls, [("sid-1", "检查磁盘", True)])
        self.assertEqual(
            results,
            [
                {
                    "session_id": "sid-1",
                    "status": "SUCCESS",
                    "report": "done:sid-1:检查磁盘:True",
                }
            ],
        )

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
