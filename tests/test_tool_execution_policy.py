import asyncio
import json
import unittest
from unittest.mock import patch

from core.tool_execution_policy import (
    evaluate_tool_execution_gate,
    execute_with_runtime_policy,
)


class ToolExecutionPolicyTests(unittest.IsolatedAsyncioTestCase):
    def test_destructive_policy_requires_approval_without_safety_hit(self):
        gate = evaluate_tool_execution_gate(
            "memory_delete",
            policy={
                "name": "memory_delete",
                "label": "删除记忆",
                "operation_mode": "destructive",
                "approval_policy": "always_required",
                "destructive": True,
            },
        )

        self.assertTrue(gate.approval_required)
        self.assertIn("工具执行策略要求审批", gate.reason)

    def test_guarded_write_uses_existing_safety_policy_reason(self):
        gate = evaluate_tool_execution_gate(
            "linux_execute_command",
            safety_needs_approval=True,
            safety_reason="命中 sudo 变更策略",
            policy={
                "name": "linux_execute_command",
                "operation_mode": "read_write",
                "approval_policy": "guarded_write",
                "destructive": False,
            },
        )

        self.assertTrue(gate.approval_required)
        self.assertEqual(gate.reason, "命中 sudo 变更策略")

    async def test_runtime_policy_times_out_and_returns_structured_error(self):
        async def slow_tool():
            await asyncio.sleep(0.05)
            return {"status": "OK"}

        result = await execute_with_runtime_policy(
            "slow_tool",
            slow_tool,
            policy={
                "name": "slow_tool",
                "timeout_policy": {"default_seconds": 0.001},
                "retry_policy": {"max_attempts": 1, "retry_on": []},
            },
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error_type"], "tool_timeout")
        self.assertEqual(payload["retry_attempts"], 1)
        self.assertEqual(
            payload["runtime_policy"],
            {
                "attempts": 1,
                "max_attempts": 1,
                "retry_delay_seconds": 0.0,
                "retry_on": [],
                "timeout_seconds": 0.001,
                "final_status": "error",
                "error_type": "tool_timeout",
                "retried": False,
            },
        )

    async def test_runtime_policy_retries_allowed_timeout_once(self):
        attempts = 0
        runtime_stats = {}

        async def flaky_tool():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                await asyncio.sleep(0.02)
            return {"status": "OK", "attempts": attempts}

        result = await execute_with_runtime_policy(
            "flaky_tool",
            flaky_tool,
            policy={
                "name": "flaky_tool",
                "timeout_policy": {"default_seconds": 0.001},
                "retry_policy": {"max_attempts": 2, "retry_on": ["timeout"]},
            },
            runtime_stats=runtime_stats,
        )

        self.assertEqual(result, {"status": "OK", "attempts": 2})
        self.assertEqual(attempts, 2)
        self.assertEqual(runtime_stats["attempts"], 2)
        self.assertEqual(runtime_stats["max_attempts"], 2)
        self.assertTrue(runtime_stats["retried"])
        self.assertEqual(runtime_stats["final_status"], "success")

    async def test_runtime_policy_clamps_default_timeout_to_max_seconds(self):
        async def slow_tool():
            await asyncio.sleep(0.02)
            return {"status": "OK"}

        runtime_stats = {}
        result = await execute_with_runtime_policy(
            "slow_tool",
            slow_tool,
            policy={
                "name": "slow_tool",
                "timeout_policy": {"default_seconds": 10, "max_seconds": 0.001},
                "retry_policy": {"max_attempts": 1, "retry_on": []},
            },
            runtime_stats=runtime_stats,
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error_type"], "tool_timeout")
        self.assertIn("0.001 秒", payload["error"])
        self.assertEqual(payload["retry_attempts"], 1)
        self.assertEqual(runtime_stats["attempts"], 1)
        self.assertEqual(runtime_stats["final_status"], "error")
        self.assertEqual(runtime_stats["error_type"], "tool_timeout")

    async def test_runtime_policy_invalid_retry_attempts_falls_back_to_one(self):
        attempts = 0

        async def failing_tool():
            nonlocal attempts
            attempts += 1
            raise ConnectionError("temporary network failure")

        result = await execute_with_runtime_policy(
            "flaky_tool",
            failing_tool,
            policy={
                "name": "flaky_tool",
                "timeout_policy": {"default_seconds": 1},
                "retry_policy": {
                    "max_attempts": "not-a-number",
                    "retry_on": ["connection_error"],
                },
            },
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error_type"], "tool_connection_error")
        self.assertEqual(payload["retry_attempts"], 1)
        self.assertEqual(attempts, 1)

    async def test_runtime_policy_caps_retry_attempts_and_applies_delay(self):
        attempts = 0
        delays = []

        async def failing_tool():
            nonlocal attempts
            attempts += 1
            raise ConnectionError("temporary network failure")

        async def fake_sleep(seconds):
            delays.append(seconds)

        with patch("core.tool_execution_policy.asyncio.sleep", side_effect=fake_sleep):
            result = await execute_with_runtime_policy(
                "flaky_tool",
                failing_tool,
                policy={
                    "name": "flaky_tool",
                    "timeout_policy": {"default_seconds": 1},
                    "retry_policy": {
                        "max_attempts": 99,
                        "retry_on": ["connection_error"],
                        "delay_seconds": 99,
                    },
                },
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error_type"], "tool_connection_error")
        self.assertEqual(payload["retry_attempts"], 3)
        self.assertEqual(payload["runtime_policy"]["max_attempts"], 3)
        self.assertTrue(payload["runtime_policy"]["retried"])
        self.assertEqual(payload["runtime_policy"]["retry_delay_seconds"], 5.0)
        self.assertEqual(payload["runtime_policy"]["retry_on"], ["connection_error"])
        self.assertEqual(attempts, 3)
        self.assertEqual(delays, [5.0, 5.0])

    async def test_runtime_policy_ignores_invalid_retry_on_metadata(self):
        attempts = 0
        runtime_stats = {}

        async def failing_tool():
            nonlocal attempts
            attempts += 1
            raise ConnectionError("temporary network failure")

        result = await execute_with_runtime_policy(
            "flaky_tool",
            failing_tool,
            policy={
                "name": "flaky_tool",
                "timeout_policy": {"default_seconds": 1},
                "retry_policy": {
                    "max_attempts": 2,
                    "retry_on": "connection_error",
                },
            },
            runtime_stats=runtime_stats,
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error_type"], "tool_connection_error")
        self.assertEqual(payload["retry_attempts"], 1)
        self.assertEqual(attempts, 1)
        self.assertEqual(runtime_stats["retry_on"], [])

    async def test_runtime_policy_filters_unknown_retry_reasons(self):
        attempts = 0
        runtime_stats = {}

        async def failing_tool():
            nonlocal attempts
            attempts += 1
            raise ConnectionError("temporary network failure")

        result = await execute_with_runtime_policy(
            "flaky_tool",
            failing_tool,
            policy={
                "name": "flaky_tool",
                "timeout_policy": {"default_seconds": 1},
                "retry_policy": {
                    "max_attempts": 2,
                    "retry_on": ["connection_error", "network_glitch"],
                },
            },
            runtime_stats=runtime_stats,
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["error_type"], "tool_connection_error")
        self.assertEqual(payload["retry_attempts"], 2)
        self.assertEqual(attempts, 2)
        self.assertEqual(runtime_stats["retry_on"], ["connection_error"])


if __name__ == "__main__":
    unittest.main()
