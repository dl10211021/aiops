import unittest

from core.session_history_service import (
    SessionHistoryServiceError,
    clear_session_history_messages,
    create_session_run_learning_candidate_record,
    delete_session_history_message_record,
    export_session_history_markdown_record,
    find_session_history_evidence_trace,
    get_session_memory_activity_record,
    get_session_run_learning_preview_record,
    get_session_run_trace_record,
    collect_observability_run_trace_evidence_records,
    list_session_run_trace_records,
    list_session_history_messages,
    search_session_context_records,
    update_session_history_message_feedback_record,
    update_session_history_message_record,
)


class FakeMemoryDB:
    def __init__(self, messages=None):
        self.cleared = []
        self.deleted = []
        self.feedback = []
        self.updated = []
        self.messages = messages if messages is not None else [
            {"role": "system", "content": "hidden"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        self.file_memory_store = None

    def get_messages(self, session_id, for_ui=False):
        self.session_id = session_id
        self.for_ui = for_ui
        return self.messages

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
        return []


class FailingMemoryDB:
    def __init__(self, exc):
        self.exc = exc

    def get_messages(self, *_args, **_kwargs):
        raise self.exc

    def clear_history(self, *_args, **_kwargs):
        raise self.exc

    def update_message_content(self, *_args, **_kwargs):
        raise self.exc

    def delete_message(self, *_args, **_kwargs):
        raise self.exc

    def update_message_feedback(self, *_args, **_kwargs):
        raise self.exc


class FakeFileMemoryStore:
    def __init__(self):
        self.appended = []
        self.resolved = []
        self.candidates = []
        self.learning_candidates = []

    def append_memory(self, *, scope_id, summary, source_session_id, metadata=None):
        self.appended.append((scope_id, summary, source_session_id, metadata or {}))
        candidate = {
            "candidate_id": "memcand_run",
            "source_session_id": source_session_id,
            "candidate_type": (metadata or {}).get("candidate_type"),
            "summary": summary,
        }
        self.candidates.insert(0, candidate)
        return {"version_id": "v1", "metadata": metadata or {}, "summary": summary}

    def list_candidate_entries(self, limit=50, review_statuses=None):
        return self.candidates[:limit]

    def list_learning_candidates(self, limit=50, target_type=""):
        items = [
            item
            for item in self.learning_candidates
            if not target_type or item.get("target_type") == target_type
        ]
        return items[:limit]

    def resolve_candidate_entry(self, candidate_id, action, actor="user"):
        self.resolved.append((candidate_id, action, actor))
        learning_candidate = {
            "id": "learncand_run",
            "target_type": "runbook",
            "status": "draft",
            "source_candidate_id": candidate_id,
            "source_session_id": "sid-1",
            "run_id": "run-2",
        }
        self.learning_candidates.insert(0, learning_candidate)
        return {"version_id": "v2", "learning_candidate": learning_candidate}


class TestSessionHistoryService(unittest.TestCase):
    def test_session_history_operations_delegate_to_memory_db(self):
        memory_db = FakeMemoryDB()

        messages = list_session_history_messages("sid-1", memory_db=memory_db)
        clear_session_history_messages("sid-1", memory_db=memory_db)
        updated = update_session_history_message_record(
            "sid-1",
            7,
            "new",
            memory_db=memory_db,
        )
        feedback = update_session_history_message_feedback_record(
            "sid-1",
            8,
            "down",
            note="不准确",
            memory_db=memory_db,
        )
        delete_session_history_message_record("sid-1", 7, memory_db=memory_db)

        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
        self.assertEqual(memory_db.cleared, ["sid-1"])
        self.assertEqual(memory_db.updated, [("sid-1", 7, "new")])
        self.assertEqual(updated, {"id": 7, "content": "new"})
        self.assertEqual(memory_db.feedback, [("sid-1", 8, "down", "不准确")])
        self.assertEqual(
            feedback,
            {"id": 8, "feedback": {"rating": "down", "note": "不准确"}},
        )
        self.assertEqual(memory_db.deleted, [("sid-1", 7)])

    def test_find_session_history_evidence_trace_returns_single_trace(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 12,
                    "role": "assistant",
                    "content": "执行完成",
                    "exec_trace": [
                        {
                            "tool": "linux_execute_command",
                            "toolCallId": "call-linux-1",
                            "evidence": {"evidence_id": "tev-sid-1-call-1"},
                            "status": "done",
                        }
                    ],
                }
            ]
        )

        result = find_session_history_evidence_trace(
            "sid-1",
            evidence_id="tev-sid-1-call-1",
            memory_db=memory_db,
        )

        self.assertEqual(result["trace"]["tool"], "linux_execute_command")
        self.assertEqual(result["message"]["id"], 12)

    def test_find_session_history_evidence_trace_falls_back_to_run_trace_tool_event(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 21,
                    "role": "system",
                    "content": "tool finished",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-1",
                    "run_event_type": "tool:after",
                    "run_event_ts": 10.0,
                    "run_event_payload": {
                        "run_id": "run-1",
                        "tool_name": "db_execute_query",
                        "tool_call_id": "call-db-1",
                        "status": "done",
                        "evidence_id": "tev-sid-1-call-db-1",
                        "evidence": {
                            "evidence_id": "tev-sid-1-call-db-1",
                            "tool_name": "db_execute_query",
                            "input_summary": "select 1",
                            "result_status": "done",
                        },
                        "result_meta": {"row_count": 1},
                    },
                }
            ]
        )

        result = find_session_history_evidence_trace(
            "sid-1",
            evidence_id="tev-sid-1-call-db-1",
            memory_db=memory_db,
        )

        self.assertEqual(result["trace"]["tool"], "db_execute_query")
        self.assertEqual(result["trace"]["toolCallId"], "call-db-1")
        self.assertEqual(result["trace"]["evidenceId"], "tev-sid-1-call-db-1")
        self.assertEqual(result["trace"]["resultMeta"]["row_count"], 1)
        self.assertEqual(result["source"], "run_trace")
        self.assertEqual(result["message"]["id"], 21)

    def test_find_session_history_evidence_trace_maps_missing_to_404(self):
        memory_db = FakeMemoryDB([])

        with self.assertRaises(SessionHistoryServiceError) as ctx:
            find_session_history_evidence_trace("sid-1", evidence_id="missing", memory_db=memory_db)

        self.assertEqual(ctx.exception.status_code, 404)

    def test_search_session_context_records_matches_messages_and_run_trace(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 12,
                    "role": "assistant",
                    "content": "Oracle 连接池异常，建议查看慢 SQL。",
                    "created_at": "2026-05-18 10:00:00",
                    "exec_trace": [
                        {
                            "tool": "db_execute_query",
                            "toolCallId": "call-db-1",
                            "evidence": {"evidence_id": "tev-db-1", "output_preview": "slow sql found"},
                            "status": "done",
                        }
                    ],
                },
                {
                    "id": 21,
                    "role": "system",
                    "content": "【AIOps Run Trace】tool after",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-1",
                    "run_event_type": "tool:after",
                    "run_event_ts": 10.0,
                    "run_event_payload": {
                        "run_id": "run-1",
                        "tool_name": "db_execute_query",
                        "tool_call_id": "call-db-1",
                        "status": "done",
                        "evidence_id": "tev-db-1",
                        "evidence": {
                            "evidence_id": "tev-db-1",
                            "tool_name": "db_execute_query",
                            "output_preview": "Oracle slow SQL evidence",
                        },
                        "result_meta": {"approval_ref": "approval-db-1"},
                    },
                },
            ]
        )

        result = search_session_context_records("sid-1", query="Oracle slow", memory_db=memory_db)

        self.assertEqual(result["query"], "Oracle slow")
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["summary"]["by_type"]["message"], 1)
        self.assertEqual(result["summary"]["by_type"]["run_trace"], 1)
        self.assertEqual(result["results"][0]["type"], "message")
        self.assertEqual(result["results"][0]["message_id"], 12)
        self.assertEqual(result["results"][0]["evidence_refs"][0]["id"], "tev-db-1")
        self.assertEqual(result["results"][1]["type"], "run_trace")
        self.assertEqual(result["results"][1]["run_id"], "run-1")
        self.assertEqual(result["results"][1]["evidence_refs"][0]["id"], "tev-db-1")

    def test_collect_observability_run_trace_evidence_records_matches_investigation(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 4,
                    "role": "system",
                    "content": "tool done",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-1",
                    "run_event_type": "tool:after",
                    "run_event_payload": {
                        "session_id": "sid-1",
                        "run_id": "run-1",
                        "tool_name": "linux_execute_command",
                        "tool_call_id": "call-1",
                        "evidence_id": "tev-sid-1-call-1",
                        "status": "done",
                        "context": {
                            "investigation_id": "inv-1",
                            "observability_task_id": "inv-1-os",
                        },
                        "evidence": {
                            "evidence_id": "tev-sid-1-call-1",
                            "investigation_id": "inv-1",
                            "observability_task_id": "inv-1-os",
                            "output_preview": "load average ok",
                        },
                    },
                },
                {
                    "id": 5,
                    "role": "system",
                    "content": "other tool",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-2",
                    "run_event_type": "tool:after",
                    "run_event_payload": {
                        "session_id": "sid-1",
                        "run_id": "run-2",
                        "tool_name": "db_execute_query",
                        "tool_call_id": "call-2",
                        "evidence_id": "tev-sid-1-call-2",
                        "context": {"investigation_id": "other"},
                    },
                },
            ]
        )

        records = collect_observability_run_trace_evidence_records(
            "inv-1",
            session_ids=["sid-1"],
            memory_db=memory_db,
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["session_id"], "sid-1")
        self.assertEqual(records[0]["task_id"], "inv-1-os")
        self.assertEqual(records[0]["trace_result"]["trace"]["evidenceId"], "tev-sid-1-call-1")
        self.assertEqual(records[0]["trace_result"]["run"]["run_id"], "run-1")

    def test_value_errors_map_to_not_found(self):
        memory_db = FailingMemoryDB(ValueError("message not found"))

        with self.assertRaises(SessionHistoryServiceError) as update_ctx:
            update_session_history_message_record("sid-1", 7, "new", memory_db=memory_db)
        with self.assertRaises(SessionHistoryServiceError) as delete_ctx:
            delete_session_history_message_record("sid-1", 7, memory_db=memory_db)
        with self.assertRaises(SessionHistoryServiceError) as feedback_ctx:
            update_session_history_message_feedback_record(
                "sid-1",
                7,
                "up",
                memory_db=memory_db,
            )

        self.assertEqual(update_ctx.exception.status_code, 404)
        self.assertEqual(delete_ctx.exception.status_code, 404)
        self.assertEqual(feedback_ctx.exception.status_code, 404)

    def test_internal_errors_map_to_500(self):
        memory_db = FailingMemoryDB(RuntimeError("db unavailable"))

        with self.assertRaises(SessionHistoryServiceError) as list_ctx:
            list_session_history_messages("sid-1", memory_db=memory_db)
        with self.assertRaises(SessionHistoryServiceError) as clear_ctx:
            clear_session_history_messages("sid-1", memory_db=memory_db)

        self.assertEqual(list_ctx.exception.status_code, 500)
        self.assertEqual(clear_ctx.exception.status_code, 500)

    def test_export_session_history_markdown_uses_session_remark_title(self):
        memory_db = FakeMemoryDB()

        markdown = export_session_history_markdown_record(
            {"sid-1": {"info": {"remark": "生产数据库"}}},
            "sid-1",
            memory_db=memory_db,
        )

        self.assertIn("# Chat History: 生产数据库", markdown)
        self.assertIn("## User", markdown)

    def test_get_session_memory_activity_record_uses_injected_db(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 7,
                    "role": "assistant",
                    "content": "hi",
                    "memory_refs": [{"path": "global/foo.md", "scope_id": "global"}],
                }
            ]
        )

        activity = get_session_memory_activity_record("sid-1", memory_db=memory_db)

        self.assertEqual(activity["summary"]["referenced_count"], 1)

    def test_list_session_run_trace_records_uses_injected_db(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 3,
                    "role": "system",
                    "content": "【AIOps Run Trace】运行结束：状态=completed",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-1",
                    "run_event_type": "run:end",
                    "run_event_payload": {"session_id": "sid-1", "status": "completed", "run_id": "run-1"},
                }
            ]
        )

        events = list_session_run_trace_records("sid-1", memory_db=memory_db)
        trace = get_session_run_trace_record("sid-1", memory_db=memory_db)

        self.assertEqual(events[0]["event_type"], "run:end")
        self.assertEqual(events[0]["payload"]["status"], "completed")
        self.assertEqual(trace["runs"][0]["run_id"], "run-1")
        self.assertEqual(trace["runs"][0]["status"], "completed")

    def test_get_session_run_trace_record_filters_by_run_id(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 3,
                    "role": "system",
                    "content": "run 1",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-1",
                    "run_event_type": "run:start",
                    "run_event_payload": {"session_id": "sid-1", "run_id": "run-1"},
                },
                {
                    "id": 4,
                    "role": "system",
                    "content": "run 2",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-2",
                    "run_event_type": "run:start",
                    "run_event_payload": {"session_id": "sid-1", "run_id": "run-2"},
                },
            ]
        )

        trace = get_session_run_trace_record("sid-1", run_id="run-2", memory_db=memory_db)

        self.assertEqual([event["run_id"] for event in trace["events"]], ["run-2"])
        self.assertEqual([run["run_id"] for run in trace["runs"]], ["run-2"])

    def test_get_session_run_learning_preview_record_uses_injected_db(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 4,
                    "role": "system",
                    "content": "tool done",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-2",
                    "run_event_type": "tool:after",
                    "run_event_payload": {
                        "session_id": "sid-1",
                        "run_id": "run-2",
                        "tool_name": "db_execute_query",
                        "tool_call_id": "call-db",
                        "evidence_id": "tev-db",
                        "status": "done",
                    },
                }
            ]
        )

        preview = get_session_run_learning_preview_record("sid-1", memory_db=memory_db)

        self.assertTrue(preview["eligible"])
        self.assertEqual(preview["evidence_refs"][0]["id"], "tev-db")
        self.assertEqual(preview["evidence_refs"][0]["tool"], "db_execute_query")

    def test_create_session_run_learning_candidate_promotes_preview_to_runbook_draft(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 4,
                    "role": "system",
                    "content": "tool done",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-2",
                    "run_event_type": "tool:after",
                    "run_event_payload": {
                        "session_id": "sid-1",
                        "run_id": "run-2",
                        "tool_name": "db_execute_query",
                        "tool_call_id": "call-db",
                        "evidence_id": "tev-db",
                        "status": "done",
                    },
                }
            ]
        )
        memory_db.file_memory_store = FakeFileMemoryStore()

        result = create_session_run_learning_candidate_record(
            "sid-1",
            run_id="run-2",
            actor="tester",
            memory_db=memory_db,
        )

        self.assertEqual(result["learning_candidate"]["id"], "learncand_run")
        self.assertEqual(memory_db.file_memory_store.resolved, [("memcand_run", "to_runbook", "tester")])
        metadata = memory_db.file_memory_store.appended[0][3]
        self.assertEqual(metadata["source"], "run_trace_learning_preview")
        self.assertEqual(metadata["review_status"], "pending")
        self.assertEqual(metadata["candidate_type"], "run_trace_runbook_preview")
        self.assertFalse(metadata["retrieval_enabled"])
        self.assertEqual(metadata["evidence_refs"][0]["id"], "tev-db")

    def test_create_session_run_learning_candidate_is_idempotent_per_run(self):
        memory_db = FakeMemoryDB(
            [
                {
                    "id": 4,
                    "role": "system",
                    "content": "tool done",
                    "memory_type": "aiops_run_trace",
                    "run_id": "run-2",
                    "run_event_type": "tool:after",
                    "run_event_payload": {
                        "session_id": "sid-1",
                        "run_id": "run-2",
                        "tool_name": "db_execute_query",
                        "tool_call_id": "call-db",
                        "evidence_id": "tev-db",
                        "status": "done",
                    },
                }
            ]
        )
        store = FakeFileMemoryStore()
        store.learning_candidates = [
            {
                "id": "learncand_existing",
                "target_type": "runbook",
                "status": "draft",
                "source_session_id": "sid-1",
                "run_id": "run-2",
            }
        ]
        memory_db.file_memory_store = store

        result = create_session_run_learning_candidate_record("sid-1", run_id="run-2", memory_db=memory_db)

        self.assertTrue(result["deduped"])
        self.assertEqual(result["learning_candidate"]["id"], "learncand_existing")
        self.assertEqual(store.appended, [])
        self.assertEqual(store.resolved, [])

    def test_create_session_run_learning_candidate_rejects_preview_without_evidence(self):
        memory_db = FakeMemoryDB([])
        memory_db.file_memory_store = FakeFileMemoryStore()

        with self.assertRaises(SessionHistoryServiceError) as ctx:
            create_session_run_learning_candidate_record("sid-1", memory_db=memory_db)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_export_session_history_markdown_maps_empty_history_to_404(self):
        memory_db = FakeMemoryDB([])

        with self.assertRaises(SessionHistoryServiceError) as ctx:
            export_session_history_markdown_record({}, "sid-empty", memory_db=memory_db)

        self.assertEqual(ctx.exception.status_code, 404)
