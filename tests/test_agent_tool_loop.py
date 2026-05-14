import asyncio
import json
import unittest
from unittest.mock import patch

from core.agent_tool_events import PreparedToolCall
from core.agent_tool_loop import process_chat_tool_calls


def decode_sse(event: str) -> dict:
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    return json.loads(event[len("data: ") : -2])


class FakeMemoryStore:
    def __init__(self):
        self.appended = []

    def append_message(self, session_id, message):
        self.appended.append((session_id, message))


class FakeDispatcher:
    def __init__(self):
        self.pending_interactions = {}
        self.pending_approvals = {}
        self.executed = []

    def check_approval_needed(self, tool_name, args, context):
        return False, ""

    async def route_and_execute(self, tool_name, args, context):
        self.executed.append((tool_name, args, context))
        return {"status": "OK", "message": "done"}


async def no_sleep(_seconds):
    return None


async def collect_tool_events(**kwargs):
    events = []
    async for event in process_chat_tool_calls(**kwargs, sleep=no_sleep):
        events.append(event)
    return events


class AgentToolLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_executes_tool_and_records_safe_result(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []
        context = {"session_id": "sid-tool"}

        events = await collect_tool_events(
            tool_calls=[
                {
                    "id": "call-1",
                    "function": {
                        "name": "linux_execute_command",
                        "arguments": json.dumps({"command": "uptime"}),
                    },
                }
            ],
            session_id="sid-tool",
            messages=messages,
            memory_store=memory_store,
            dispatcher=dispatcher,
            context=context,
            iteration=0,
        )

        payloads = [decode_sse(event) for event in events]
        self.assertEqual(payloads[0]["type"], "tool_start")
        self.assertEqual(payloads[0]["cmd"], "uptime")
        self.assertEqual(payloads[0]["args"], "uptime")
        self.assertEqual(
            payloads[0]["result_meta"]["tool_policy"]["name"],
            "linux_execute_command",
        )
        self.assertEqual(
            payloads[0]["result_meta"]["tool_policy"]["evidence_family"],
            "host_cli",
        )
        self.assertEqual(payloads[1]["type"], "tool_end")
        self.assertEqual(payloads[1]["result_status"], "done")
        self.assertEqual(payloads[1]["evidence"]["session_id"], "sid-tool")
        self.assertEqual(payloads[1]["evidence"]["tool_name"], "linux_execute_command")
        self.assertEqual(payloads[1]["evidence"]["tool_family"], "os")
        self.assertEqual(payloads[1]["evidence"]["input_summary"], "uptime")
        self.assertEqual(payloads[2]["type"], "status")
        self.assertEqual(
            dispatcher.executed,
            [("linux_execute_command", {"command": "uptime"}, context)],
        )
        self.assertEqual(messages[0]["tool_call_id"], "call-1")
        self.assertEqual(memory_store.appended[0][1], messages[0])

    async def test_approval_request_includes_tool_policy(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        dispatcher.check_approval_needed = lambda tool_name, args, context: (True, "需要审批")
        messages = []

        async def never_resolve(_future, timeout):
            raise TimeoutError()

        with patch("asyncio.wait_for", side_effect=never_resolve), patch(
            "core.agent_tool_loop.record_tool_approval_request",
            return_value={"metadata": {"policy": {}}},
        ), patch("core.approval_queue.mark_approval_timeout"):
            events = await collect_tool_events(
                tool_calls=[
                    {
                        "id": "call-approval",
                        "function": {
                            "name": "db_execute_query",
                            "arguments": json.dumps({"sql": "delete from t"}),
                        },
                    }
                ],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=0,
            )

        payloads = [decode_sse(event) for event in events]
        approval = payloads[0]
        self.assertEqual(approval["type"], "tool_ask_approval")
        self.assertEqual(approval["tool_policy"]["name"], "db_execute_query")
        self.assertEqual(approval["tool_policy"]["evidence_family"], "database")

    async def test_runtime_policy_can_require_approval_even_without_safety_hit(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []

        async def never_resolve(_future, timeout):
            raise TimeoutError()

        with patch("asyncio.wait_for", side_effect=never_resolve), patch(
            "core.agent_tool_loop.record_tool_approval_request",
            return_value={"metadata": {"policy": {}}},
        ), patch("core.approval_queue.mark_approval_timeout"):
            events = await collect_tool_events(
                tool_calls=[
                    {
                        "id": "call-delete",
                        "function": {
                            "name": "memory_delete",
                            "arguments": json.dumps({"key": "old"}),
                        },
                    }
                ],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=0,
            )

        payloads = [decode_sse(event) for event in events]
        approval = payloads[0]
        self.assertEqual(approval["type"], "tool_ask_approval")
        self.assertEqual(approval["tool_policy"]["approval_policy"], "always_required")
        self.assertEqual(dispatcher.executed, [])

    async def test_runtime_policy_timeout_returns_tool_error(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []

        async def slow_execute(tool_name, args, context):
            await asyncio.sleep(0.05)
            return {"status": "OK"}

        dispatcher.route_and_execute = slow_execute

        with patch(
            "core.agent_tool_loop.tool_policy_metadata",
            return_value={
                "name": "slow_tool",
                "operation_mode": "read",
                "approval_policy": "none",
                "destructive": False,
                "timeout_policy": {"default_seconds": 0.001},
                "retry_policy": {"max_attempts": 1, "retry_on": []},
                "evidence_family": "platform",
            },
        ):
            events = await collect_tool_events(
                tool_calls=[
                    {
                        "id": "call-timeout",
                        "function": {
                            "name": "slow_tool",
                            "arguments": json.dumps({}),
                        },
                    }
                ],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=0,
            )

        payloads = [decode_sse(event) for event in events]
        self.assertEqual(payloads[1]["type"], "tool_end")
        self.assertEqual(payloads[1]["result_status"], "error")
        self.assertEqual(payloads[1]["result_meta"]["error_type"], "tool_timeout")
        self.assertIn("tool_timeout", messages[0]["content"])

    async def test_runtime_policy_success_retry_is_attached_to_tool_trace(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []
        attempts = 0

        async def flaky_execute(tool_name, args, context):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError("temporary connection issue")
            return {"status": "OK", "attempts": attempts}

        dispatcher.route_and_execute = flaky_execute

        with patch(
            "core.agent_tool_loop.tool_policy_metadata",
            return_value={
                "name": "flaky_tool",
                "operation_mode": "read",
                "approval_policy": "none",
                "destructive": False,
                "timeout_policy": {"default_seconds": 1},
                "retry_policy": {
                    "max_attempts": 2,
                    "retry_on": ["connection_error"],
                    "delay_seconds": 0,
                },
                "evidence_family": "platform",
            },
        ):
            events = await collect_tool_events(
                tool_calls=[
                    {
                        "id": "call-flaky",
                        "function": {
                            "name": "flaky_tool",
                            "arguments": json.dumps({}),
                        },
                    }
                ],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=0,
            )

        payloads = [decode_sse(event) for event in events]
        runtime_execution = payloads[1]["result_meta"]["runtime_execution"]
        self.assertEqual(payloads[1]["result_status"], "done")
        self.assertEqual(runtime_execution["attempts"], 2)
        self.assertEqual(runtime_execution["max_attempts"], 2)
        self.assertTrue(runtime_execution["retried"])
        self.assertEqual(runtime_execution["final_status"], "success")
        self.assertEqual(attempts, 2)

    async def test_concurrency_safe_tools_run_in_parallel_batch(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []
        active = 0
        max_active = 0

        async def parallel_execute(tool_name, args, context):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1
            return {"status": "OK", "tool": tool_name}

        dispatcher.route_and_execute = parallel_execute

        def read_policy(name):
            return {
                "name": name,
                "operation_mode": "read",
                "approval_policy": "none",
                "destructive": False,
                "concurrency_safe": True,
                "timeout_policy": {"default_seconds": 1},
                "retry_policy": {"max_attempts": 1, "retry_on": []},
                "evidence_family": "platform",
            }

        with patch("core.agent_tool_loop.tool_policy_metadata", side_effect=read_policy):
            events = await collect_tool_events(
                tool_calls=[
                    {
                        "id": "call-read-1",
                        "function": {"name": "read_one", "arguments": json.dumps({})},
                    },
                    {
                        "id": "call-read-2",
                        "function": {"name": "read_two", "arguments": json.dumps({})},
                    },
                ],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=0,
            )

        payloads = [decode_sse(event) for event in events]
        self.assertEqual([payload["type"] for payload in payloads], ["tool_start", "tool_start", "tool_end", "tool_end", "status"])
        self.assertTrue(payloads[0]["result_meta"]["concurrent"])
        self.assertGreaterEqual(max_active, 2)
        self.assertEqual([message["name"] for message in messages], ["read_one", "read_two"])

    async def test_mixed_batch_parallelizes_safe_prefix_then_guards_unsafe_tool(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []
        active = 0
        max_active = 0

        async def parallel_execute(tool_name, args, context):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1
            dispatcher.executed.append((tool_name, args, context))
            return {"status": "OK", "tool": tool_name}

        dispatcher.route_and_execute = parallel_execute

        def policy_for(name):
            if name.startswith("read_"):
                return {
                    "name": name,
                    "operation_mode": "read",
                    "approval_policy": "none",
                    "destructive": False,
                    "concurrency_safe": True,
                    "timeout_policy": {"default_seconds": 0},
                    "retry_policy": {"max_attempts": 1, "retry_on": []},
                    "evidence_family": "platform",
                }
            return {
                "name": name,
                "operation_mode": "destructive",
                "approval_policy": "always_required",
                "destructive": True,
                "concurrency_safe": False,
                "timeout_policy": {"default_seconds": 1},
                "retry_policy": {"max_attempts": 1, "retry_on": []},
                "evidence_family": "memory",
            }

        async def never_resolve(_future, timeout):
            raise TimeoutError()

        with patch(
            "core.agent_tool_loop.tool_policy_metadata",
            side_effect=policy_for,
        ), patch(
            "asyncio.wait_for",
            side_effect=never_resolve,
        ), patch(
            "core.agent_tool_loop.record_tool_approval_request",
            return_value={"metadata": {"policy": {}}},
        ), patch("core.approval_queue.mark_approval_timeout"):
            events = await collect_tool_events(
                tool_calls=[
                    {
                        "id": "call-read-1",
                        "function": {
                            "name": "read_one",
                            "arguments": json.dumps({}),
                        },
                    },
                    {
                        "id": "call-read-2",
                        "function": {
                            "name": "read_two",
                            "arguments": json.dumps({}),
                        },
                    },
                    {
                        "id": "call-delete",
                        "function": {
                            "name": "memory_delete",
                            "arguments": json.dumps({"key": "old"}),
                        },
                    },
                ],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=0,
            )

        payloads = [decode_sse(event) for event in events]
        self.assertEqual(
            [payload["type"] for payload in payloads],
            [
                "tool_start",
                "tool_start",
                "tool_end",
                "tool_end",
                "tool_ask_approval",
                "tool_end",
                "status",
            ],
        )
        self.assertTrue(payloads[0]["result_meta"]["concurrent"])
        self.assertGreaterEqual(max_active, 2)
        self.assertEqual(
            [call[0] for call in dispatcher.executed],
            ["read_one", "read_two"],
        )
        self.assertEqual(
            [message["name"] for message in messages],
            ["read_one", "read_two", "memory_delete"],
        )

    async def test_parse_error_appends_tool_error_without_executing(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        messages = []

        with patch(
            "core.agent_tool_loop.prepare_tool_call",
            return_value=PreparedToolCall(
                id="call-bad",
                name="linux_execute_command",
                args={},
                parse_error="bad json",
                display_cmd="JSON解析失败: bad json",
            ),
        ):
            events = await collect_tool_events(
                tool_calls=[{"id": "call-bad"}],
                session_id="sid-tool",
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context={"session_id": "sid-tool"},
                iteration=1,
            )

        payloads = [decode_sse(event) for event in events]
        self.assertEqual(payloads[0]["type"], "tool_end")
        self.assertEqual(payloads[0]["result_status"], "error")
        self.assertEqual(payloads[0]["result_meta"]["error_type"], "tool_arguments_invalid")
        self.assertEqual(payloads[0]["evidence"]["result_status"], "error")
        self.assertEqual(payloads[0]["evidence"]["input_summary"], "JSON解析失败: bad json")
        self.assertEqual(dispatcher.executed, [])
        self.assertEqual(messages[0]["tool_call_id"], "call-bad")
        self.assertIn("bad json", messages[0]["content"])
        self.assertEqual(memory_store.appended[0][1], messages[0])


if __name__ == "__main__":
    unittest.main()
