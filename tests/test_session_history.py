import unittest

from core.session_history import (
    attach_legacy_exec_traces,
    build_session_memory_activity,
    build_session_history_markdown,
    clear_session_history,
    delete_session_message,
    find_session_exec_trace,
    get_user_visible_session_history,
    is_user_visible_history_message,
    session_history_export_title,
    update_session_message_feedback,
    update_session_message_content,
)


class FakeMemoryDB:
    def __init__(self):
        self.cleared = []
        self.deleted = []
        self.feedback = []
        self.updated = []
        self.pending = []
        self.messages = [
            {"role": "system", "content": "hidden"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "tool", "content": "hidden"},
        ]

    def get_messages(self, session_id, for_ui=False, limit=None):
        self.session_id = session_id
        self.for_ui = for_ui
        self.limit = limit
        return self.messages[-limit:] if limit else self.messages

    def clear_history(self, session_id):
        self.cleared.append(session_id)

    def update_message_content(self, session_id, message_id, content):
        self.updated.append((session_id, message_id, content))
        return {"id": message_id, "content": content}

    def delete_message(self, session_id, message_id):
        self.deleted.append((session_id, message_id))

    def update_message_feedback(self, session_id, message_id, rating, note=None):
        self.feedback.append((session_id, message_id, rating, note))
        return {"id": message_id, "feedback": {"rating": rating, "note": note or ""}}

    def list_pending_memory_conflicts(self, limit=100):
        return self.pending[:limit]


class TestSessionHistory(unittest.TestCase):
    def test_get_user_visible_session_history_filters_system_and_tool_roles(self):
        memory_db = FakeMemoryDB()

        messages = get_user_visible_session_history(memory_db, "sid-1")

        self.assertEqual(memory_db.session_id, "sid-1")
        self.assertTrue(memory_db.for_ui)
        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )

    def test_get_user_visible_session_history_passes_limit_to_memory_store(self):
        memory_db = FakeMemoryDB()
        memory_db.messages = [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "new"},
        ]

        messages = get_user_visible_session_history(memory_db, "sid-1", limit=1)

        self.assertEqual(memory_db.limit, 1)
        self.assertEqual(messages, [{"role": "assistant", "content": "new"}])

    def test_find_session_exec_trace_matches_evidence_and_message_preview(self):
        memory_db = FakeMemoryDB()
        memory_db.messages = [
            {"role": "user", "content": "检查数据库"},
            {
                "id": 9,
                "role": "assistant",
                "content": "已经查询。",
                "exec_trace": [
                    {
                        "tool": "db_execute_query",
                        "toolCallId": "call-db-1",
                        "evidenceId": "tev-sid-1-call-1",
                        "status": "done",
                    }
                ],
            },
        ]

        result = find_session_exec_trace(memory_db, "sid-1", evidence_id="tev-sid-1-call-1")

        self.assertIsNotNone(result)
        self.assertEqual(result["trace"]["tool"], "db_execute_query")
        self.assertEqual(result["message"]["id"], 9)
        self.assertEqual(result["message"]["preview"], "已经查询。")

    def test_find_session_exec_trace_requires_lookup_key(self):
        memory_db = FakeMemoryDB()

        with self.assertRaises(ValueError):
            find_session_exec_trace(memory_db, "sid-1")

    def test_manual_stop_system_message_is_user_visible_for_audit(self):
        memory_db = FakeMemoryDB()
        memory_db.messages = [
            {"role": "system", "content": "hidden"},
            {
                "role": "system",
                "content": "本轮任务已手动停止。",
                "memory_type": "manual_stop",
                "visible_to_user": True,
            },
            {"role": "tool", "content": "hidden"},
        ]

        messages = get_user_visible_session_history(memory_db, "sid-1")

        self.assertEqual(
            messages,
            [
                {
                    "role": "system",
                    "content": "本轮任务已手动停止。",
                    "memory_type": "manual_stop",
                    "visible_to_user": True,
                }
            ],
        )
        self.assertTrue(is_user_visible_history_message(messages[0]))

    def test_attach_legacy_exec_traces_rebuilds_tool_results_for_ui(self):
        messages = [
            {"role": "user", "content": "检查 Windows 服务"},
            {
                "role": "assistant",
                "content": "我来执行只读检查。",
                "tool_calls": [
                    {
                        "id": "call-winrm",
                        "type": "function",
                        "function": {
                            "name": "winrm_execute_command",
                            "arguments": '{"command": "Get-Service"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-winrm",
                "name": "winrm_execute_command",
                "content": '{"success": true, "output": "Spooler Running"}',
            },
        ]

        hydrated = attach_legacy_exec_traces(messages)

        trace = hydrated[1]["exec_trace"][0]
        self.assertEqual(trace["tool"], "winrm_execute_command")
        self.assertEqual(trace["args"], '{"command": "Get-Service"}')
        self.assertEqual(trace["status"], "done")
        self.assertEqual(trace["resultMeta"]["output"], "Spooler Running")
        self.assertEqual(trace["resultMeta"]["tool_policy"]["name"], "winrm_execute_command")
        self.assertEqual(trace["resultMeta"]["tool_policy"]["evidence_family"], "host_cli")
        self.assertNotIn("exec_trace", messages[1])

    def test_attach_legacy_exec_traces_covers_asset_tool_families(self):
        tool_calls = [
            ("call-linux", "linux_execute_command", '{"command": "uptime"}'),
            ("call-db", "db_execute_query", '{"sql": "select 1 from dual"}'),
            ("call-net", "network_cli_execute_command", '{"command": "show interface brief"}'),
            ("call-winrm", "winrm_execute_command", '{"command": "Get-Process"}'),
        ]
        messages = [
            {
                "role": "assistant",
                "content": "我会按资产协议执行只读检查。",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": arguments},
                    }
                    for call_id, tool_name, arguments in tool_calls
                ],
            }
        ]
        messages.extend(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": tool_name,
                "content": '{"success": true, "output": "ok"}',
            }
            for call_id, tool_name, _arguments in tool_calls
        )

        hydrated = attach_legacy_exec_traces(messages)

        traces = hydrated[0]["exec_trace"]
        self.assertEqual(
            [trace["tool"] for trace in traces],
            [
                "linux_execute_command",
                "db_execute_query",
                "network_cli_execute_command",
                "winrm_execute_command",
            ],
        )
        self.assertEqual([trace["status"] for trace in traces], ["done", "done", "done", "done"])
        self.assertEqual(
            [trace["resultMeta"]["tool_policy"]["evidence_family"] for trace in traces],
            ["host_cli", "database", "network", "host_cli"],
        )

    def test_attach_legacy_exec_traces_marks_blocked_or_failed_results(self):
        messages = [
            {
                "role": "assistant",
                "content": "执行检查。",
                "tool_calls": [
                    {
                        "id": "call-blocked",
                        "type": "function",
                        "function": {
                            "name": "linux_execute_command",
                            "arguments": '{"command": "rm -rf /"}',
                        },
                    },
                    {
                        "id": "call-failed",
                        "type": "function",
                        "function": {
                            "name": "db_execute_query",
                            "arguments": '{"sql": "drop table t"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-blocked",
                "content": '{"status": "blocked", "error": "安全策略阻止"}',
            },
            {
                "role": "tool",
                "tool_call_id": "call-failed",
                "content": '{"success": false, "output": "", "error": "权限不足"}',
            },
        ]

        hydrated = attach_legacy_exec_traces(messages)

        self.assertEqual([trace["status"] for trace in hydrated[0]["exec_trace"]], ["error", "error"])

    def test_attach_legacy_exec_traces_is_not_limited_to_known_tool_names(self):
        messages = [
            {
                "role": "assistant",
                "content": "执行自定义资产检查。",
                "tool_calls": [
                    {
                        "id": "call-custom",
                        "type": "function",
                        "function": {
                            "name": "custom_asset_protocol_probe",
                            "arguments": '{"target": "asset-created-session"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-custom",
                "content": '{"success": true, "output": "custom ok"}',
            },
        ]

        hydrated = attach_legacy_exec_traces(messages)

        self.assertEqual(hydrated[0]["exec_trace"][0]["tool"], "custom_asset_protocol_probe")
        self.assertEqual(hydrated[0]["exec_trace"][0]["status"], "done")
        self.assertEqual(hydrated[0]["exec_trace"][0]["resultMeta"]["output"], "custom ok")
        self.assertEqual(
            hydrated[0]["exec_trace"][0]["resultMeta"]["tool_policy"]["name"],
            "custom_asset_protocol_probe",
        )

    def test_attach_legacy_exec_traces_preserves_existing_trace(self):
        messages = [
            {
                "role": "assistant",
                "content": "已有新格式轨迹",
                "exec_trace": [{"tool": "db_execute_query", "status": "done"}],
                "tool_calls": [
                    {
                        "id": "call-db",
                        "function": {"name": "db_execute_query", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-db",
                "content": '{"success": false, "error": "denied"}',
            },
        ]

        hydrated = attach_legacy_exec_traces(messages)

        self.assertEqual(
            hydrated[0]["exec_trace"],
            [{"tool": "db_execute_query", "status": "done"}],
        )

    def test_clear_update_and_delete_delegate_to_memory_db(self):
        memory_db = FakeMemoryDB()

        clear_session_history(memory_db, "sid-1")
        updated = update_session_message_content(memory_db, "sid-1", 7, "new")
        feedback = update_session_message_feedback(
            memory_db,
            "sid-1",
            8,
            "up",
            note="很好",
        )
        delete_session_message(memory_db, "sid-1", 7)

        self.assertEqual(memory_db.cleared, ["sid-1"])
        self.assertEqual(memory_db.updated, [("sid-1", 7, "new")])
        self.assertEqual(updated, {"id": 7, "content": "new"})
        self.assertEqual(memory_db.feedback, [("sid-1", 8, "up", "很好")])
        self.assertEqual(feedback, {"id": 8, "feedback": {"rating": "up", "note": "很好"}})
        self.assertEqual(memory_db.deleted, [("sid-1", 7)])

    def test_session_history_export_title_prefers_active_session_remark(self):
        title = session_history_export_title(
            {"sid-1": {"info": {"remark": "生产 MySQL"}}},
            "sid-1",
        )

        self.assertEqual(title, "生产 MySQL")
        self.assertEqual(session_history_export_title({}, "sid-1"), "sid-1")

    def test_build_session_history_markdown_uses_for_ui_messages_and_title(self):
        memory_db = FakeMemoryDB()

        markdown = build_session_history_markdown(
            memory_db,
            {"sid-1": {"info": {"remark": "生产 MySQL"}}},
            "sid-1",
        )

        self.assertEqual(memory_db.session_id, "sid-1")
        self.assertTrue(memory_db.for_ui)
        self.assertIn("# Chat History: 生产 MySQL", markdown)
        self.assertIn("## User\nhi", markdown)
        self.assertIn("## AI Assistant\nhello", markdown)
        self.assertNotIn("hidden", markdown)

    def test_build_session_memory_activity_collects_refs_feedback_and_pending(self):
        memory_db = FakeMemoryDB()
        memory_db.messages = [
            {
                "id": 7,
                "role": "assistant",
                "content": "回答内容很好，应该沉淀。",
                "memory_refs": [{"path": "global/foo.md", "scope_id": "global"}],
                "feedback": {
                    "rating": "up",
                    "created_at": "2026-05-04 08:00:00",
                    "memory_policy": "pending_review",
                },
            },
            {
                "id": 8,
                "role": "assistant",
                "content": "错误回答。",
                "feedback": {"rating": "down", "note": "风险误判"},
            },
        ]
        memory_db.pending = [
            {"path": "sessions/sid-1/foo.md", "reason": "内容冲突"},
            {"path": "sessions/sid-2/foo.md", "reason": "其他会话"},
        ]

        activity = build_session_memory_activity(memory_db, "sid-1")

        self.assertEqual(activity["summary"]["referenced_count"], 1)
        self.assertEqual(activity["summary"]["promoted_count"], 0)
        self.assertEqual(activity["summary"]["pending_candidate_count"], 1)
        self.assertEqual(activity["summary"]["rejected_count"], 1)
        self.assertEqual(activity["summary"]["pending_conflict_count"], 2)
        self.assertEqual(activity["referenced"][0]["message_id"], 7)
        self.assertEqual(activity["feedback"][0]["memory_policy"], "pending_review")
        self.assertEqual(activity["feedback"][1]["memory_policy"], "do_not_promote_answer")
        self.assertEqual(activity["pending_conflicts"][1]["operation"], "negative_feedback")
        self.assertEqual(activity["pending_conflicts"][1]["reason"], "风险误判")
