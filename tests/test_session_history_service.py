import unittest

from core.session_history_service import (
    SessionHistoryServiceError,
    clear_session_history_messages,
    delete_session_history_message_record,
    export_session_history_markdown_record,
    list_session_history_messages,
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

    def test_export_session_history_markdown_maps_empty_history_to_404(self):
        memory_db = FakeMemoryDB([])

        with self.assertRaises(SessionHistoryServiceError) as ctx:
            export_session_history_markdown_record({}, "sid-empty", memory_db=memory_db)

        self.assertEqual(ctx.exception.status_code, 404)
