import asyncio
import unittest
from unittest.mock import patch

from api import routes, session_history_routes
from api.schemas import SessionMessageFeedbackRequest, SessionMessageUpdateRequest


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
        self.assertIn("/session/{session_id}/history/run-trace", paths)
        self.assertIn("/session/{session_id}/history/{message_id}", paths)
        self.assertIn("/session/{session_id}/history/{message_id}/feedback", paths)
        self.assertIn("/session/{session_id}/memory/activity", paths)
        self.assertIn("/session/{session_id}/export", paths)

    def test_session_history_routes_preserve_response_shapes(self):
        memory_db = FakeMemoryDB()

        with patch("core.memory.memory_db", memory_db):
            list_response = asyncio.run(session_history_routes.get_session_history("sid-1"))
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

        self.assertEqual(list_response.status, "success")
        self.assertEqual(list_response.data, {"messages": memory_db.messages})
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
