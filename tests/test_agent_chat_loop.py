import unittest
from unittest.mock import patch

from core.agent_chat_loop import (
    _assistant_orchestration_labels,
    _assistant_review_thinking_mode,
    _build_trace_review_prompt,
    _native_execution_intent,
    _review_messages,
    _resolve_model_orchestration,
    _should_force_native_tool_first,
    append_assistant_trace_review,
    build_successful_execution_memory,
    run_chat_agent_loop,
)
from core.agent_sse import sse_event


class FakeMemoryStore:
    def __init__(self):
        self.appended = []

    def append_message(self, session_id, message):
        self.appended.append((session_id, message))

    async def compress_and_store_ltm(
        self,
        session_id,
        emb_client,
        embedding_model,
        primary_model_id=None,
        memory_scope_ids=None,
    ):
        return None


class TraceMemoryStore(FakeMemoryStore):
    def __init__(self):
        super().__init__()
        self.updated_exec_traces = []

    def append_message(self, session_id, message):
        super().append_message(session_id, message)
        return len(self.appended)

    def update_message_exec_trace(self, session_id, message_id, exec_trace):
        self.updated_exec_traces.append((session_id, message_id, exec_trace))


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)

    def warning(self, *message):
        self.messages.append(message)


async def no_sleep(_seconds):
    return None


async def collect_chat_loop_events(**overrides):
    memory_store = overrides.pop("memory_store", FakeMemoryStore())
    cancel_flags = overrides.pop("cancel_flags", {"sid-1": False})
    scheduler_calls = []

    def scheduler(**kwargs):
        scheduler_calls.append(kwargs)

    base_kwargs = {
        "session_id": "sid-1",
        "model_name": "model-a",
        "thinking_mode": "off",
        "messages": [],
        "context": {"session_id": "sid-1", "memory_scope_ids": ["sid-1"]},
        "tools": [{"name": "tool"}],
        "memory_store": memory_store,
        "dispatcher": object(),
        "cancel_flags": cancel_flags,
        "emb_client": "emb-client",
        "embedding_model": "emb-model",
        "event_logger": FakeLogger(),
        "sleep": no_sleep,
        "compression_scheduler": scheduler,
    }
    base_kwargs.update(overrides)
    events = []
    async for event in run_chat_agent_loop(**base_kwargs):
        events.append(event)
    return events, base_kwargs, memory_store, cancel_flags, scheduler_calls


class AgentChatLoopTests(unittest.IsolatedAsyncioTestCase):
    def test_structured_context_intent_can_force_native_tool_without_keywords(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "db_execute_query",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        intent = _native_execution_intent(
            messages=[{"role": "user", "content": "帮我处理一下这个问题"}],
            context={
                "target_scope": "asset",
                "asset_type": "oracle",
                "protocol": "oracle",
                "execution_intent": {
                    "requires_live_evidence": True,
                    "allowed_tool_family": "native_asset_protocol",
                    "reason": "快捷指令声明需要现场证据",
                    "source": "slash_command",
                },
            },
            tools=tools,
        )

        self.assertTrue(intent.requires_live_evidence)
        self.assertEqual(intent.allowed_tool_family, "native_asset_protocol")
        self.assertEqual(intent.source, "slash_command")
        self.assertEqual(intent.first_step_tool_names, ("db_execute_query",))

    def test_tool_boundary_question_does_not_force_native_execution(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "linux_execute_command",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        self.assertFalse(
            _should_force_native_tool_first(
                messages=[{"role": "user", "content": "说明当前资产可用工具和正确使用边界"}],
                context={"target_scope": "asset", "asset_type": "linux", "protocol": "ssh"},
                tools=tools,
            )
        )

    def test_split_orchestration_labels_assistant_when_delegated(self):
        with (
            patch(
                "core.agent_chat_loop.get_assistant_model_config",
                return_value={"enabled": True, "model_id": "provider|assistant", "tasks": {}},
            ),
            patch("core.agent_chat_loop.resolve_assistant_model_id", return_value="provider|assistant"),
            patch("core.agent_chat_loop.assistant_thinking_mode", return_value="high"),
            patch("core.agent_chat_loop.assistant_task_enabled", return_value=False),
        ):
            orchestration = _resolve_model_orchestration("provider|main", "split")

        self.assertTrue(orchestration["enabled"])
        self.assertTrue(orchestration["assistant_delegated"])
        labels = _assistant_orchestration_labels(orchestration)
        self.assertIn("辅助模型随后负责选择工具", labels["intent"])
        self.assertIn("辅助模型正在选择工具", labels["tool"])
        self.assertIn("辅助模型正在整理最终回复", labels["final"])

    def test_split_orchestration_labels_primary_takeover_without_assistant(self):
        with (
            patch(
                "core.agent_chat_loop.get_assistant_model_config",
                return_value={"enabled": False, "model_id": "provider|assistant", "tasks": {}},
            ),
            patch("core.agent_chat_loop.resolve_assistant_model_id", return_value="provider|main"),
            patch("core.agent_chat_loop.assistant_thinking_mode", return_value="high"),
            patch("core.agent_chat_loop.assistant_task_enabled", return_value=False),
        ):
            orchestration = _resolve_model_orchestration("provider|main", "split")

        self.assertTrue(orchestration["enabled"])
        self.assertFalse(orchestration["assistant_delegated"])
        labels = _assistant_orchestration_labels(orchestration)
        self.assertIn("接管辅助模型职责", labels["intent"])
        self.assertIn("主模型正在接管工具选择", labels["tool"])
        self.assertIn("主模型正在整理最终回复", labels["final"])

    def test_fast_orchestration_uses_single_flow_and_disables_auxiliary_review_tasks(self):
        def task_enabled(task: str):
            return task in {"completion_check", "trace_review", "risk_advice"}

        with (
            patch(
                "core.agent_chat_loop.get_assistant_model_config",
                return_value={"enabled": True, "model_id": "provider|assistant", "tasks": {}},
            ),
            patch("core.agent_chat_loop.resolve_assistant_model_id", return_value="provider|assistant"),
            patch("core.agent_chat_loop.assistant_thinking_mode", return_value="high"),
            patch("core.agent_chat_loop.assistant_task_enabled", side_effect=task_enabled),
        ):
            orchestration = _resolve_model_orchestration("provider|main", "fast")

        self.assertFalse(orchestration["enabled"])
        self.assertEqual(orchestration["mode"], "fast")
        self.assertEqual(orchestration["assistant_thinking_mode"], "high")
        self.assertFalse(orchestration["completion_check"])
        self.assertFalse(orchestration["trace_review"])
        self.assertFalse(orchestration["risk_advice"])

    def test_successful_execution_memory_marks_assistant_self_confirmation_policy(self):
        memory = build_successful_execution_memory(
            session_id="sid-1",
            context={
                "asset_type": "linux",
                "protocol": "ssh",
                "host": "10.0.0.1",
                "port": 22,
                "allow_modifications": False,
            },
            exec_trace=[
                {
                    "tool": "linux_execute_command",
                    "args": "uptime",
                    "result": "load average: 0.01, 0.01, 0.00",
                    "status": "done",
                    "resultMeta": {
                        "tool_policy": {
                            "operation_mode": "read_write",
                            "approval_policy": "guarded_write",
                            "evidence_family": "host_cli",
                        }
                    },
                    "evidenceId": "tev-sid-1-call-1",
                }
            ],
            assistant_content="系统负载正常。",
        )

        self.assertIsNotNone(memory)
        self.assertEqual(memory["memory_type"], "successful_execution")
        self.assertIn("【保留方式】成功经验", memory["content"])
        self.assertIn("辅助模型根据上下文自确认", memory["content"])
        self.assertIn("无需用户每次点赞", memory["content"])
        self.assertIn("只可作为当前会话后续轮次", memory["content"])
        self.assertIn("工具=Linux/Unix 命令 (`linux_execute_command`)", memory["content"])
        self.assertIn("策略=read_write/guarded_write/host_cli", memory["content"])
        self.assertIn("运行=-", memory["content"])
        self.assertIn("证据=tev-sid-1-call-1", memory["content"])
        self.assertNotIn("工具=linux_execute_command;", memory["content"])
        self.assertNotIn("同类资产排查", memory["content"])

    def test_successful_execution_memory_keeps_retry_runtime_context(self):
        memory = build_successful_execution_memory(
            session_id="sid-1",
            context={
                "asset_type": "monitor",
                "protocol": "http_api",
                "host": "elk.local",
                "port": 5601,
                "allow_modifications": False,
            },
            exec_trace=[
                {
                    "tool": "monitoring_api_query",
                    "args": "GET /api/status",
                    "result": '{"status":"OK"}',
                    "status": "done",
                    "resultMeta": {
                        "runtime_execution": {
                            "attempts": 2,
                            "max_attempts": 2,
                            "retried": True,
                            "final_status": "success",
                        }
                    },
                }
            ],
            assistant_content="Kibana 状态正常。",
        )

        self.assertIsNotNone(memory)
        self.assertIn("运行=retry:2/2", memory["content"])

    def test_trace_review_prompt_localizes_tool_names_for_audit(self):
        prompt = _build_trace_review_prompt(
            {
                "asset_type": "oracle",
                "protocol": "oracle",
                "host": "db.local",
                "port": 1521,
                "allow_modifications": False,
            },
            [
                {
                    "tool": "db_execute_query",
                    "args": "select 1 from dual",
                    "result": "1",
                    "status": "done",
                    "resultMeta": {
                        "tool_policy": {
                            "operation_mode": "read_write",
                            "approval_policy": "guarded_write",
                            "evidence_family": "database",
                        },
                        "runtime_policy": {
                            "attempts": 2,
                            "max_attempts": 2,
                            "retried": True,
                            "final_status": "error",
                            "error_type": "tool_timeout",
                            "timeout_seconds": 30,
                        },
                    },
                    "evidenceId": "tev-sid-1-call-1",
                }
            ],
            "数据库只读检查完成。",
            want_trace_review=True,
            want_risk_advice=True,
        )

        self.assertIn("工具：数据库 SQL 执行 (`db_execute_query`)", prompt)
        self.assertIn("策略：read_write/guarded_write/database", prompt)
        self.assertIn("运行：timeout:30s,retry:2/2", prompt)
        self.assertIn("证据：tev-sid-1-call-1", prompt)
        self.assertNotIn("工具：db_execute_query\n", prompt)
        self.assertIn("【思维链审查】", prompt)
        self.assertIn("【风险建议】", prompt)

    def test_review_messages_keep_system_prompt_first(self):
        messages = _review_messages(
            [
                {"role": "system", "content": "old system"},
                {"role": "user", "content": "question"},
                {"role": "assistant", "content": "draft"},
            ],
            "review prompt",
        )

        self.assertEqual(messages[0], {"role": "system", "content": "review prompt"})
        self.assertEqual([message["role"] for message in messages], ["system", "user", "assistant"])

    def test_review_thinking_mode_defaults_to_configured_mode(self):
        self.assertEqual(_assistant_review_thinking_mode("high"), "high")

    async def test_trace_review_uses_system_first_review_messages(self):
        captured = {}

        async def fake_collect(**kwargs):
            captured["messages"] = kwargs["messages"]
            return "【思维链审查】完整\n【风险建议】暂无明确风险证据"

        exec_trace = [
            {
                "tool": "linux_execute_command",
                "args": "uptime",
                "result": "load average: 0.01",
                "status": "done",
            }
        ]
        with (
            patch("core.agent_chat_loop.assistant_task_enabled", return_value=True),
            patch("core.agent_chat_loop._collect_review_model_text", side_effect=fake_collect),
        ):
            await append_assistant_trace_review(
                model_name="model-a",
                thinking_mode="off",
                messages=[
                    {"role": "system", "content": "chat system"},
                    {"role": "user", "content": "巡检"},
                    {"role": "assistant", "content": "调用工具"},
                ],
                context={"asset_type": "linux", "protocol": "ssh", "host": "h", "port": 22},
                exec_trace=exec_trace,
                assistant_content="完成",
                event_logger=FakeLogger(),
            )

        self.assertEqual(captured["messages"][0]["role"], "system")
        self.assertIn("【思维链审查】", captured["messages"][0]["content"])
        self.assertEqual([message["role"] for message in captured["messages"]], ["system", "user", "assistant"])
        self.assertEqual(exec_trace[-2]["tool"], "思维链审查")

    def test_successful_execution_memory_skips_interrupted_turn(self):
        memory = build_successful_execution_memory(
            session_id="sid-1",
            context={"asset_type": "linux", "protocol": "ssh", "host": "h", "port": 22},
            exec_trace=[{"tool": "ssh", "args": "uptime", "result": "ok", "status": "done"}],
            assistant_content="完成",
            interrupted=True,
        )

        self.assertIsNone(memory)

    async def test_streams_assistant_message_done_and_schedules_ltm(self):
        async def streamer(**kwargs):
            kwargs["state"].assistant_content = "完成"
            yield "stream-event"

        events, kwargs, memory_store, _cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(assistant_streamer=streamer)
        )

        self.assertEqual(
            events,
            [
                sse_event({"type": "status", "content": "🤖 AI 正在分析并规划执行路径..."}),
                sse_event({"type": "status", "content": "💭 思考中..."}),
                "stream-event",
                sse_event({"type": "done"}),
            ],
        )
        self.assertEqual(kwargs["messages"], [{"role": "assistant", "content": "完成"}])
        self.assertEqual(memory_store.appended, [("sid-1", kwargs["messages"][0])])
        self.assertEqual(scheduler_calls[0]["session_id"], "sid-1")
        self.assertEqual(scheduler_calls[0]["emb_client"], "emb-client")
        self.assertEqual(
            scheduler_calls[0]["memory_scope_ids"],
            ["sid-1"],
        )

    async def test_cancel_before_streaming_resets_flag_without_ltm_schedule(self):
        async def streamer(**_kwargs):
            raise AssertionError("streamer should not run after cancellation")

        events, _kwargs, _memory_store, cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(
                cancel_flags={"sid-1": True},
                assistant_streamer=streamer,
            )
        )

        self.assertEqual(
            events,
            [
                sse_event({"type": "status", "content": "🤖 AI 正在分析并规划执行路径..."}),
                sse_event({"type": "error", "content": "任务已被手动中止。"}),
                sse_event({"type": "done"}),
            ],
        )
        self.assertFalse(cancel_flags["sid-1"])
        self.assertEqual(scheduler_calls, [])

    async def test_cancel_after_tool_processing_skips_success_memory_and_ltm_schedule(self):
        flags = {"sid-1": False}

        async def streamer(**kwargs):
            state = kwargs["state"]
            state.tool_calls = [{"id": "call-1", "function": {"name": "ssh", "arguments": "{}"}}]
            yield "stream-event"

        async def processor(**kwargs):
            kwargs["trace_collector"]({"type": "tool_start", "tool": "ssh", "args": "uptime"})
            kwargs["trace_collector"]({"type": "tool_end", "tool": "ssh", "result": "ok", "status": "done"})
            flags[kwargs["session_id"]] = True
            yield "tool-event"

        events, _kwargs, memory_store, cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(
                cancel_flags=flags,
                assistant_streamer=streamer,
                tool_call_processor=processor,
            )
        )

        self.assertFalse(cancel_flags["sid-1"])
        self.assertIn(sse_event({"type": "error", "content": "任务已被手动中止。"}), events)
        self.assertEqual(scheduler_calls, [])
        self.assertEqual(
            [message.get("memory_type") for _sid, message in memory_store.appended],
            [None],
        )

    async def test_attaches_memory_references_to_visible_assistant_message(self):
        async def streamer(**kwargs):
            kwargs["state"].assistant_content = "基于历史记忆完成"
            yield "stream-event"

        events, kwargs, memory_store, _cancel_flags, _scheduler_calls = (
            await collect_chat_loop_events(
                assistant_streamer=streamer,
                memory_references=[{"scope_id": "sid-1", "summary_preview": "历史偏好"}],
            )
        )

        self.assertIn("stream-event", events)
        self.assertIn(
            sse_event(
                {
                    "type": "memory_refs",
                    "refs": [{"scope_id": "sid-1", "summary_preview": "历史偏好"}],
                }
            ),
            events,
        )
        self.assertEqual(kwargs["messages"][0]["memory_refs"][0]["summary_preview"], "历史偏好")
        self.assertEqual(memory_store.appended[0][1]["memory_refs"][0]["scope_id"], "sid-1")

    async def test_keeps_memory_references_for_final_answer_after_tool_calls(self):
        turn = {"count": 0}

        async def streamer(**kwargs):
            turn["count"] += 1
            if turn["count"] == 1:
                kwargs["state"].assistant_content = "先查证据"
                kwargs["state"].tool_calls = [{"id": "call-1"}]
                return
            kwargs["state"].assistant_content = "最终回答"
            if False:
                yield "unused"

        async def tool_processor(**_kwargs):
            if False:
                yield "unused"

        events, kwargs, memory_store, _cancel_flags, _scheduler_calls = (
            await collect_chat_loop_events(
                assistant_streamer=streamer,
                tool_call_processor=tool_processor,
                memory_references=[{"source_type": "rag", "title": "账号规范"}],
                max_steps_resolver=lambda _mode: 2,
            )
        )

        self.assertNotIn("memory_refs", kwargs["messages"][0])
        self.assertEqual(kwargs["messages"][1]["memory_refs"][0]["title"], "账号规范")
        self.assertEqual(memory_store.appended[1][1]["memory_refs"][0]["source_type"], "rag")
        self.assertIn(
            sse_event({"type": "memory_refs", "refs": [{"source_type": "rag", "title": "账号规范"}]}),
            events,
        )

    async def test_attaches_tool_exec_trace_to_final_answer_after_tool_calls(self):
        turn = {"count": 0}
        memory_store = TraceMemoryStore()

        async def streamer(**kwargs):
            turn["count"] += 1
            if turn["count"] == 1:
                kwargs["state"].assistant_content = "先执行只读命令"
                kwargs["state"].tool_calls = [{"id": "call-1"}]
                return
            kwargs["state"].assistant_content = "巡检完成"
            if False:
                yield "unused"

        async def tool_processor(**kwargs):
            kwargs["trace_collector"](
                {
                    "type": "tool_start",
                    "tool": "network_cli_execute",
                    "args": "display current-configuration",
                }
            )
            kwargs["trace_collector"](
                {
                    "type": "tool_end",
                    "tool": "network_cli_execute",
                    "result": "sysname CoreSwitch",
                    "status": "done",
                }
            )
            yield "tool-event"

        with patch("core.agent_chat_loop.assistant_task_enabled", return_value=False):
            events, kwargs, _memory_store, _cancel_flags, _scheduler_calls = (
                await collect_chat_loop_events(
                    memory_store=memory_store,
                    assistant_streamer=streamer,
                    tool_call_processor=tool_processor,
                    max_steps_resolver=lambda _mode: 2,
                )
            )

        self.assertIn("tool-event", events)
        self.assertEqual(memory_store.updated_exec_traces[0][0], "sid-1")
        self.assertEqual(memory_store.updated_exec_traces[0][1], 1)
        final_message = kwargs["messages"][-1]
        self.assertEqual(final_message["content"], "巡检完成")
        self.assertEqual(final_message["exec_trace"][0]["tool"], "network_cli_execute")
        self.assertEqual(final_message["exec_trace"][0]["args"], "display current-configuration")
        self.assertIn("sysname CoreSwitch", final_message["exec_trace"][0]["result"])
        self.assertEqual(memory_store.appended[-1][1]["exec_trace"], final_message["exec_trace"])

    async def test_current_asset_execution_request_forces_native_tool_first(self):
        turn = {"count": 0}
        seen = []
        memory_store = TraceMemoryStore()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "db_execute_query",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        async def streamer(**kwargs):
            turn["count"] += 1
            seen.append(
                {
                    "tool_choice": kwargs.get("tool_choice"),
                    "tools": [tool["function"]["name"] for tool in kwargs.get("tools") or []],
                    "last_message": kwargs["messages"][-1]["content"],
                }
            )
            if turn["count"] == 1:
                kwargs["state"].assistant_content = ""
                kwargs["state"].tool_calls = [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "db_execute_query", "arguments": '{"sql":"select 1 from dual"}'},
                    }
                ]
                return
            kwargs["state"].assistant_content = "Oracle 在线"
            if False:
                yield "unused"

        async def tool_processor(**kwargs):
            kwargs["trace_collector"](
                {
                    "type": "tool_start",
                    "tool": "db_execute_query",
                    "args": "select 1 from dual",
                }
            )
            kwargs["trace_collector"](
                {
                    "type": "tool_end",
                    "tool": "db_execute_query",
                    "result": "1",
                    "status": "done",
                }
            )
            yield "tool-event"

        with patch("core.agent_chat_loop.assistant_task_enabled", return_value=False):
            events, kwargs, _memory_store, _cancel_flags, _scheduler_calls = (
                await collect_chat_loop_events(
                    memory_store=memory_store,
                    messages=[
                        {
                            "role": "user",
                            "content": "请快速检查当前资产 oracle/oracle 172.17.1.207 的运行状态。",
                        }
                    ],
                    context={
                        "session_id": "sid-1",
                        "asset_type": "oracle",
                        "protocol": "oracle",
                        "host": "172.17.1.207",
                        "port": 1521,
                        "memory_scope_ids": ["sid-1"],
                    },
                    tools=tools,
                    assistant_streamer=streamer,
                    tool_call_processor=tool_processor,
                    max_steps_resolver=lambda _mode: 2,
                )
            )

        self.assertIn(
            sse_event({"type": "status", "content": "🧰 正在强制调用当前会话原生工具采集证据..."}),
            events,
        )
        self.assertEqual(seen[0]["tool_choice"], "required")
        self.assertEqual(seen[0]["tools"], ["db_execute_query"])
        self.assertIn("必须先调用当前会话原生协议工具", seen[0]["last_message"])
        self.assertEqual(seen[1]["tool_choice"], "auto")
        self.assertEqual(kwargs["messages"][-1]["exec_trace"][0]["tool"], "db_execute_query")

    async def test_current_network_api_asset_request_forces_native_tool_first(self):
        turn = {"count": 0}
        seen = []
        memory_store = TraceMemoryStore()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "network_api_request",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        async def streamer(**kwargs):
            turn["count"] += 1
            seen.append(
                {
                    "tool_choice": kwargs.get("tool_choice"),
                    "tools": [tool["function"]["name"] for tool in kwargs.get("tools") or []],
                    "last_message": kwargs["messages"][-1]["content"],
                }
            )
            if turn["count"] == 1:
                kwargs["state"].assistant_content = ""
                kwargs["state"].tool_calls = [
                    {
                        "id": "call-fw-api",
                        "type": "function",
                        "function": {
                            "name": "network_api_request",
                            "arguments": '{"method":"get","endpoint":"/api/v1/system/status"}',
                        },
                    }
                ]
                return
            kwargs["state"].assistant_content = "防火墙 API 状态正常"
            if False:
                yield "unused"

        async def tool_processor(**kwargs):
            kwargs["trace_collector"](
                {
                    "type": "tool_start",
                    "tool": "network_api_request",
                    "args": "GET /api/v1/system/status",
                }
            )
            kwargs["trace_collector"](
                {
                    "type": "tool_end",
                    "tool": "network_api_request",
                    "result": '{"success": true, "status": "OK"}',
                    "status": "done",
                }
            )
            yield "tool-event"

        with patch("core.agent_chat_loop.assistant_task_enabled", return_value=False):
            events, kwargs, _memory_store, _cancel_flags, _scheduler_calls = (
                await collect_chat_loop_events(
                    memory_store=memory_store,
                    messages=[
                        {
                            "role": "user",
                            "content": "请通过当前资产防火墙 API 检查运行状态。",
                        }
                    ],
                    context={
                        "session_id": "sid-fw-api",
                        "asset_type": "firewall",
                        "protocol": "http_api",
                        "host": "fw.local",
                        "port": 443,
                        "memory_scope_ids": ["sid-fw-api"],
                    },
                    tools=tools,
                    assistant_streamer=streamer,
                    tool_call_processor=tool_processor,
                    max_steps_resolver=lambda _mode: 2,
                )
            )

        self.assertIn(
            sse_event({"type": "status", "content": "🧰 正在强制调用当前会话原生工具采集证据..."}),
            events,
        )
        self.assertEqual(seen[0]["tool_choice"], "required")
        self.assertEqual(seen[0]["tools"], ["network_api_request"])
        self.assertIn("必须先调用当前会话原生协议工具", seen[0]["last_message"])
        final_trace = kwargs["messages"][-1]["exec_trace"][0]
        self.assertEqual(final_trace["tool"], "network_api_request")
        self.assertEqual(final_trace["args"], "GET /api/v1/system/status")

    async def test_forced_native_tool_request_discards_direct_answer_and_retries(self):
        turn = {"count": 0}
        memory_store = TraceMemoryStore()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "db_execute_query",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        async def streamer(**kwargs):
            turn["count"] += 1
            if turn["count"] == 1:
                kwargs["state"].assistant_content = "没有查数据库也直接生成的报告"
                return
            if turn["count"] == 2:
                kwargs["state"].tool_calls = [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "db_execute_query", "arguments": '{"sql":"select 1 from dual"}'},
                    }
                ]
                return
            kwargs["state"].assistant_content = "基于工具结果完成"
            if False:
                yield "unused"

        async def tool_processor(**kwargs):
            kwargs["trace_collector"](
                {
                    "type": "tool_start",
                    "tool": "db_execute_query",
                    "args": "select 1 from dual",
                }
            )
            kwargs["trace_collector"](
                {
                    "type": "tool_end",
                    "tool": "db_execute_query",
                    "result": "1",
                    "status": "done",
                }
            )
            yield "tool-event"

        with patch("core.agent_chat_loop.assistant_task_enabled", return_value=False):
            events, kwargs, _memory_store, _cancel_flags, _scheduler_calls = (
                await collect_chat_loop_events(
                    memory_store=memory_store,
                    messages=[
                        {
                            "role": "user",
                            "content": "请只读检查 oracle/oracle 172.17.1.207 的表空间使用率。",
                        }
                    ],
                    context={
                        "session_id": "sid-1",
                        "asset_type": "oracle",
                        "protocol": "oracle",
                        "host": "172.17.1.207",
                        "port": 1521,
                        "memory_scope_ids": ["sid-1"],
                    },
                    tools=tools,
                    assistant_streamer=streamer,
                    tool_call_processor=tool_processor,
                    max_steps_resolver=lambda _mode: 3,
                )
            )

        self.assertIn(
            sse_event({"type": "status", "content": "⚠️ 模型未发起工具调用，已丢弃直接回答并重新约束工具调用..."}),
            events,
        )
        self.assertNotIn(
            "没有查数据库也直接生成的报告",
            [message.get("content") for message in kwargs["messages"]],
        )
        self.assertEqual(kwargs["messages"][-1]["content"], "基于工具结果完成")
        self.assertEqual(kwargs["messages"][-1]["exec_trace"][0]["tool"], "db_execute_query")

    async def test_processes_tools_then_emits_step_limit_summary(self):
        async def streamer(**kwargs):
            kwargs["state"].assistant_content = "需要工具"
            kwargs["state"].tool_calls = [{"id": "call-1"}]
            if False:
                yield "unused"

        tool_processor_calls = []

        async def tool_processor(**kwargs):
            tool_processor_calls.append(kwargs)
            yield "tool-event"

        async def step_summary(**kwargs):
            yield f"summary:{kwargs['max_steps']}"

        events, kwargs, memory_store, _cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(
                assistant_streamer=streamer,
                tool_call_processor=tool_processor,
                step_summary_streamer=step_summary,
                max_steps_resolver=lambda _mode: 1,
            )
        )

        self.assertEqual(events[-2:], ["tool-event", "summary:1"])
        self.assertEqual(tool_processor_calls[0]["iteration"], 0)
        self.assertEqual(tool_processor_calls[0]["messages"], kwargs["messages"])
        self.assertEqual(memory_store.appended[0][1]["tool_calls"], [{"id": "call-1"}])
        self.assertEqual(len(scheduler_calls), 1)


if __name__ == "__main__":
    unittest.main()
