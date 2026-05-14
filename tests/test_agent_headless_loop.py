import json
import unittest
from unittest.mock import patch

from core.agent_headless_loop import run_headless_agent_loop


class FakeLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, *args):
        self.warnings.append(args)


class FakeDispatcher:
    def __init__(self, *, approval_required=False):
        self.approval_required = approval_required
        self.executed = []

    def check_approval_needed(self, tool_name, args, context):
        if self.approval_required:
            return True, "需要审批"
        return False, ""

    async def route_and_execute(self, tool_name, args, context):
        self.executed.append((tool_name, args, context))
        return {"status": "OK"}


def stream_executor_factory(calls):
    async def executor(model_name, messages, thinking_mode, tools=None):
        chunks = calls.pop(0)
        for chunk in chunks:
            yield chunk

    return executor


class AgentHeadlessLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_report_when_model_finishes_without_tools(self):
        messages = [{"role": "system", "content": "sys"}]

        report = await run_headless_agent_loop(
            model_name="model",
            messages=messages,
            tools=[],
            context={"session_id": "sid"},
            session_id="sid",
            agent_profile="default",
            host="host.local",
            dispatcher=FakeDispatcher(),
            event_logger=FakeLogger(),
            stream_executor=stream_executor_factory(
                [[{"type": "content", "content": "巡检完成"}]]
            ),
            max_steps=3,
        )

        self.assertEqual(report, "来自 default Agent (host.local) 的协同任务报告：\n巡检完成")
        self.assertEqual(messages, [{"role": "system", "content": "sys"}])

    async def test_executes_tool_then_uses_next_iteration_report(self):
        messages = [{"role": "system", "content": "sys"}]
        context = {"session_id": "sid"}
        dispatcher = FakeDispatcher()

        report = await run_headless_agent_loop(
            model_name="model",
            messages=messages,
            tools=[],
            context=context,
            session_id="sid",
            agent_profile="default",
            host="host.local",
            dispatcher=dispatcher,
            event_logger=FakeLogger(),
            stream_executor=stream_executor_factory(
                [
                    [
                        {"type": "thinking", "content": "分析"},
                        {"type": "content", "content": "准备执行"},
                        {
                            "type": "tool_calls",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "linux_execute_command",
                                        "arguments": json.dumps({"command": "uptime"}),
                                    },
                                }
                            ],
                        },
                    ],
                    [{"type": "content", "content": "最终完成"}],
                ]
            ),
            max_steps=3,
        )

        self.assertEqual(report, "来自 default Agent (host.local) 的协同任务报告：\n最终完成")
        self.assertEqual(
            dispatcher.executed,
            [("linux_execute_command", {"command": "uptime"}, context)],
        )
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["reasoning_content"], "分析")
        self.assertEqual(messages[2]["role"], "tool")
        self.assertEqual(messages[2]["content"], "{'status': 'OK'}")

    async def test_returns_step_limit_report_when_tools_never_finish(self):
        tool_call = {
            "id": "call-1",
            "function": {
                "name": "linux_execute_command",
                "arguments": json.dumps({"command": "uptime"}),
            },
        }

        report = await run_headless_agent_loop(
            model_name="model",
            messages=[],
            tools=[],
            context={"session_id": "sid"},
            session_id="sid",
            agent_profile="default",
            host="host.local",
            dispatcher=FakeDispatcher(),
            event_logger=FakeLogger(),
            stream_executor=stream_executor_factory(
                [[{"type": "content", "content": "还在执行"}, {"type": "tool_calls", "tool_calls": [tool_call]}]]
            ),
            max_steps=1,
        )

        self.assertEqual(
            report,
            "任务达到 1 步执行保护上限，系统已停止继续调用工具。以下是最后一轮阶段性结果：还在执行",
        )

    async def test_headless_blocks_high_risk_action_even_when_policy_allows(self):
        messages = [{"role": "system", "content": "sys"}]
        dispatcher = FakeDispatcher()

        with patch("core.agent_headless_loop.record_headless_approval_block") as record:
            record.return_value = {"id": "call-1"}
            report = await run_headless_agent_loop(
                model_name="model",
                messages=messages,
                tools=[],
                context={
                    "session_id": "sid",
                    "execution_mode": "headless",
                    "allow_modifications": True,
                    "asset_type": "linux",
                    "protocol": "ssh",
                },
                session_id="sid",
                agent_profile="default",
                host="host.local",
                dispatcher=dispatcher,
                event_logger=FakeLogger(),
                stream_executor=stream_executor_factory(
                    [
                        [
                            {"type": "content", "content": "准备变更"},
                            {
                                "type": "tool_calls",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "function": {
                                            "name": "linux_execute_command",
                                            "arguments": json.dumps({"command": "systemctl restart nginx"}),
                                        },
                                    }
                                ],
                            },
                        ],
                        [{"type": "content", "content": "已阻断"}],
                    ]
                ),
                max_steps=3,
            )

        self.assertEqual(report, "来自 default Agent (host.local) 的协同任务报告：\n已阻断")
        self.assertEqual(dispatcher.executed, [])
        record.assert_called_once()
        self.assertIn("高风险动作", record.call_args.kwargs["reason"])

    async def test_headless_blocks_runtime_policy_approval_gate(self):
        messages = [{"role": "system", "content": "sys"}]
        dispatcher = FakeDispatcher()

        with patch("core.agent_headless_loop.record_headless_approval_block") as record:
            record.return_value = {"id": "call-delete"}
            report = await run_headless_agent_loop(
                model_name="model",
                messages=messages,
                tools=[],
                context={"session_id": "sid", "execution_mode": "headless"},
                session_id="sid",
                agent_profile="default",
                host="host.local",
                dispatcher=dispatcher,
                event_logger=FakeLogger(),
                stream_executor=stream_executor_factory(
                    [
                        [
                            {"type": "content", "content": "准备清理"},
                            {
                                "type": "tool_calls",
                                "tool_calls": [
                                    {
                                        "id": "call-delete",
                                        "function": {
                                            "name": "memory_delete",
                                            "arguments": json.dumps({"key": "old"}),
                                        },
                                    }
                                ],
                            },
                        ],
                        [{"type": "content", "content": "已阻断"}],
                    ]
                ),
                max_steps=3,
            )

        self.assertEqual(report, "来自 default Agent (host.local) 的协同任务报告：\n已阻断")
        self.assertEqual(dispatcher.executed, [])
        record.assert_called_once()
        self.assertIn("工具执行策略要求审批", record.call_args.kwargs["reason"])


if __name__ == "__main__":
    unittest.main()
