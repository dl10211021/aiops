import asyncio
import unittest
from unittest.mock import patch

from api import routes, session_history_routes
from api.schemas import (
    SessionMessageFeedbackRequest,
    SessionMessageUpdateRequest,
    SessionRunLearningCandidateRequest,
)
from core.run_trace_store import RUN_TRACE_MEMORY_TYPE


class FakeMemoryDB:
    def __init__(self):
        self.messages = [
            {"id": 1, "role": "user", "content": "hello"},
            {"id": 2, "role": "assistant", "content": "hi"},
        ]
        self.cleared = []
        self.updated = []
        self.deleted = []
        self.feedback = []

    def get_messages(self, session_id, for_ui=False):
        return self.messages

    def list_pending_memory_conflicts(self, limit=100):
        return [{"path": "sessions/sid-1/conflict.md", "reason": "待确认"}]

    def clear_history(self, session_id):
        self.cleared.append(session_id)

    def update_message_content(self, session_id, message_id, content):
        message = {"id": message_id, "role": "user", "content": content}
        self.updated.append((session_id, message_id, content))
        return message

    def delete_message(self, session_id, message_id):
        self.deleted.append((session_id, message_id))

    def update_message_feedback(self, session_id, message_id, rating, note=None):
        message = {
            "id": message_id,
            "role": "assistant",
            "content": "hi",
            "feedback": {"rating": rating, "note": note or ""},
        }
        self.feedback.append((session_id, message_id, rating, note))
        return message


class TestSessionHistoryRoutes(unittest.TestCase):
    def test_session_history_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/session/{session_id}/history", paths)
        self.assertIn("/session/{session_id}/history/search", paths)
        self.assertIn("/session/{session_id}/history/run-trace", paths)
        self.assertIn("/session/{session_id}/history/run-trace/audit-summary", paths)
        self.assertIn("/session/{session_id}/history/run-trace/learning-preview", paths)
        self.assertIn("/session/{session_id}/history/run-trace/learning-candidate", paths)
        self.assertIn("/session/{session_id}/history/{message_id}", paths)
        self.assertIn("/session/{session_id}/history/{message_id}/feedback", paths)
        self.assertIn("/session/{session_id}/memory/activity", paths)
        self.assertIn("/session/{session_id}/export", paths)

    def test_session_history_routes_preserve_response_shapes(self):
        memory_db = FakeMemoryDB()

        with patch("core.memory.memory_db", memory_db):
            list_response = asyncio.run(session_history_routes.get_session_history("sid-1"))
            search_response = asyncio.run(session_history_routes.search_session_history("sid-1", query="hello"))
            clear_response = asyncio.run(session_history_routes.delete_session_history("sid-1"))
            update_response = asyncio.run(
                session_history_routes.update_session_history_message(
                    "sid-1",
                    1,
                    SessionMessageUpdateRequest(content="updated"),
                )
            )
            delete_response = asyncio.run(
                session_history_routes.delete_session_history_message("sid-1", 1)
            )
            feedback_response = asyncio.run(
                session_history_routes.feedback_session_history_message(
                    "sid-1",
                    2,
                    SessionMessageFeedbackRequest(rating="up"),
                )
            )
            activity_response = asyncio.run(session_history_routes.get_session_memory_activity("sid-1"))
            run_trace_response = asyncio.run(session_history_routes.get_session_run_trace("sid-1"))
            run_trace_filter_response = asyncio.run(
                session_history_routes.get_session_run_trace("sid-1", run_id="run-missing")
            )
            run_trace_audit_response = asyncio.run(
                session_history_routes.get_session_run_trace_audit_summary("sid-1")
            )
            learning_preview_response = asyncio.run(
                session_history_routes.get_session_run_learning_preview("sid-1")
            )
            with patch(
                "api.session_history_routes.create_session_run_learning_candidate_record",
                return_value={"learning_candidate": {"id": "learncand_run"}},
            ):
                learning_candidate_response = asyncio.run(
                    session_history_routes.create_session_run_learning_candidate(
                        "sid-1",
                        SessionRunLearningCandidateRequest(run_id="run-1"),
                    )
                )

        self.assertEqual(list_response.status, "success")
        self.assertEqual(list_response.data, {"messages": memory_db.messages})
        self.assertEqual(search_response.status, "success")
        self.assertEqual(search_response.data["search"]["summary"]["total"], 1)
        self.assertEqual(search_response.data["search"]["results"][0]["type"], "message")
        self.assertEqual(clear_response.status, "success")
        self.assertEqual(clear_response.message, "会话记录已清空")
        self.assertEqual(update_response.status, "success")
        self.assertEqual(update_response.message, "消息已更新")
        self.assertEqual(
            update_response.data,
            {"message": {"id": 1, "role": "user", "content": "updated"}},
        )
        self.assertEqual(delete_response.status, "success")
        self.assertEqual(delete_response.message, "消息已删除")
        self.assertEqual(feedback_response.status, "success")
        self.assertEqual(feedback_response.message, "反馈已记录")
        self.assertEqual(
            feedback_response.data,
            {
                "message": {
                    "id": 2,
                    "role": "assistant",
                    "content": "hi",
                    "feedback": {"rating": "up", "note": ""},
                }
            },
        )
        self.assertEqual(memory_db.cleared, ["sid-1"])
        self.assertEqual(memory_db.updated, [("sid-1", 1, "updated")])
        self.assertEqual(memory_db.deleted, [("sid-1", 1)])
        self.assertEqual(memory_db.feedback, [("sid-1", 2, "up", None)])
        self.assertEqual(activity_response.data["activity"]["summary"]["pending_conflict_count"], 1)
        self.assertEqual(run_trace_response.status, "success")
        self.assertEqual(run_trace_response.data, {"events": [], "runs": []})
        self.assertEqual(run_trace_filter_response.data, {"events": [], "runs": []})
        self.assertEqual(run_trace_audit_response.status, "success")
        self.assertEqual(run_trace_audit_response.data["summary"]["run_count"], 0)
        self.assertEqual(run_trace_audit_response.data["summary"]["unaudited_run_count"], 0)
        self.assertEqual(learning_preview_response.status, "success")
        self.assertEqual(learning_preview_response.data["preview"]["eligible"], False)
        self.assertEqual(learning_candidate_response.status, "success")
        self.assertEqual(learning_candidate_response.message, "学习候选已提交")
        self.assertEqual(learning_candidate_response.data["learning_candidate"]["id"], "learncand_run")

    def test_session_run_trace_audit_summary_counts_context_and_prompt_modules(self):
        memory_db = FakeMemoryDB()
        memory_db.messages = [
            {
                "id": 10,
                "memory_type": RUN_TRACE_MEMORY_TYPE,
                "run_id": "run-1",
                "run_event_type": "run:start",
                "run_event_ts": 100.0,
                "run_event_payload": {
                    "run_id": "run-1",
                    "context": {
                        "context_sources": [
                            {"source": "knowledge_base", "enabled": True, "hit": True, "reference_count": 2},
                            {"source": "asset_profile", "enabled": True, "hit": False, "status": "error"},
                        ],
                        "prompt_modules": {
                            "modules": ["evidence_contract", "rag_context"],
                            "enabled": {"evidence_contract": True, "rag_context": False},
                        },
                    },
                },
                "content": "run start",
            },
            {
                "id": 11,
                "memory_type": RUN_TRACE_MEMORY_TYPE,
                "run_id": "run-2",
                "run_event_type": "run:start",
                "run_event_ts": 200.0,
                "run_event_payload": {"run_id": "run-2"},
                "content": "legacy run start",
            },
        ]

        with patch("core.memory.memory_db", memory_db):
            response = asyncio.run(session_history_routes.get_session_run_trace_audit_summary("sid-1"))

        summary = response.data["summary"]
        self.assertEqual(summary["run_count"], 2)
        self.assertEqual(summary["event_count"], 2)
        self.assertEqual(summary["audited_run_count"], 1)
        self.assertEqual(summary["unaudited_run_count"], 1)
        self.assertEqual(summary["context_sources"], 2)
        self.assertEqual(summary["context_hits"], 1)
        self.assertEqual(summary["context_errors"], 1)
        self.assertEqual(summary["prompt_modules"], 2)
        self.assertEqual(summary["source_counts"]["knowledge_base"]["hit"], 1)
        self.assertEqual(summary["module_counts"]["rag_context"]["disabled"], 1)

    def test_session_run_trace_audit_summary_counts_runtime_execution(self):
        memory_db = FakeMemoryDB()
        memory_db.messages = [
            {
                "id": 10,
                "memory_type": RUN_TRACE_MEMORY_TYPE,
                "run_id": "run-1",
                "run_event_type": "run:start",
                "run_event_ts": 100.0,
                "run_event_payload": {"run_id": "run-1"},
                "content": "run start",
            },
            {
                "id": 11,
                "memory_type": RUN_TRACE_MEMORY_TYPE,
                "run_id": "run-1",
                "run_event_type": "tool:after",
                "run_event_ts": 101.0,
                "run_event_payload": {
                    "run_id": "run-1",
                    "tool_name": "ssh_exec",
                    "status": "error",
                    "result_meta": {
                        "runtime_execution": {
                            "attempts": 2,
                            "max_attempts": 2,
                            "retried": True,
                            "concurrent": True,
                            "final_status": "error",
                            "error_type": "tool_timeout",
                            "timeout_seconds": 30,
                        }
                    },
                },
                "content": "tool timeout",
            },
            {
                "id": 12,
                "memory_type": RUN_TRACE_MEMORY_TYPE,
                "run_id": "run-1",
                "run_event_type": "tool:after",
                "run_event_ts": 102.0,
                "run_event_payload": {
                    "run_id": "run-1",
                    "tool_name": "asset_lookup",
                    "status": "success",
                    "result_meta": {
                        "runtime_execution": {
                            "attempts": 1,
                            "max_attempts": 1,
                            "final_status": "success",
                        }
                    },
                },
                "content": "tool success",
            },
            {
                "id": 13,
                "memory_type": RUN_TRACE_MEMORY_TYPE,
                "run_id": "run-1",
                "run_event_type": "tool:after",
                "run_event_ts": 103.0,
                "run_event_payload": {
                    "run_id": "run-1",
                    "tool_name": "legacy_tool",
                    "status": "success",
                },
                "content": "legacy tool",
            },
        ]

        with patch("core.memory.memory_db", memory_db):
            response = asyncio.run(session_history_routes.get_session_run_trace_audit_summary("sid-1"))

        summary = response.data["summary"]
        self.assertEqual(summary["runtime_tool_count"], 3)
        self.assertEqual(summary["runtime_success_count"], 1)
        self.assertEqual(summary["runtime_error_count"], 1)
        self.assertEqual(summary["runtime_timeout_count"], 1)
        self.assertEqual(summary["runtime_retry_count"], 1)
        self.assertEqual(summary["runtime_concurrent_count"], 1)
        self.assertEqual(summary["runtime_untracked_count"], 1)
        self.assertEqual(summary["runtime_error_types"]["tool_timeout"], 1)

    def test_session_history_export_preserves_response_shape(self):
        with patch(
            "api.session_history_routes.export_session_history_markdown_record",
            return_value="# 生产数据库",
        ):
            response = asyncio.run(session_history_routes.export_session_history("sid-1"))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"markdown": "# 生产数据库"})


if __name__ == "__main__":
    unittest.main()
