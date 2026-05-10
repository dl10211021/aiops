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
        self.assertEqual(payloads[1]["type"], "tool_end")
        self.assertEqual(payloads[1]["result_status"], "done")
        self.assertEqual(payloads[2]["type"], "status")
        self.assertEqual(
            dispatcher.executed,
            [("linux_execute_command", {"command": "uptime"}, context)],
        )
        self.assertEqual(messages[0]["tool_call_id"], "call-1")
        self.assertEqual(memory_store.appended[0][1], messages[0])

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
        self.assertEqual(dispatcher.executed, [])
        self.assertEqual(messages[0]["tool_call_id"], "call-bad")
        self.assertIn("bad json", messages[0]["content"])
        self.assertEqual(memory_store.appended[0][1], messages[0])


if __name__ == "__main__":
    unittest.main()
