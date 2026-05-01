import unittest

from core.session_history_service import (
    SessionHistoryServiceError,
    clear_session_history_messages,
    delete_session_history_message_record,
    list_session_history_messages,
    update_session_history_message_record,
)


class FakeMemoryDB:
    def __init__(self):
        self.cleared = []
        self.deleted = []
        self.updated = []

    def get_messages(self, session_id, for_ui=False):
        self.session_id = session_id
        self.for_ui = for_ui
        return [
            {"role": "system", "content": "hidden"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

    def clear_history(self, session_id):
        self.cleared.append(session_id)

    def update_message_content(self, session_id, message_id, content):
        self.updated.append((session_id, message_id, content))
        return {"id": message_id, "content": content}

    def delete_message(self, session_id, message_id):
        self.deleted.append((session_id, message_id))


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


class TestSessionHistoryService(unittest.TestCase):
    def test_session_history_operations_delegate_to_memory_db(self):
        memory_db = FakeMemoryDB()

        messages = list_session_history_messages(memory_db, "sid-1")
        clear_session_history_messages(memory_db, "sid-1")
        updated = update_session_history_message_record(memory_db, "sid-1", 7, "new")
        delete_session_history_message_record(memory_db, "sid-1", 7)

        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
        self.assertEqual(memory_db.cleared, ["sid-1"])
        self.assertEqual(memory_db.updated, [("sid-1", 7, "new")])
        self.assertEqual(updated, {"id": 7, "content": "new"})
        self.assertEqual(memory_db.deleted, [("sid-1", 7)])

    def test_value_errors_map_to_not_found(self):
        memory_db = FailingMemoryDB(ValueError("message not found"))

        with self.assertRaises(SessionHistoryServiceError) as update_ctx:
            update_session_history_message_record(memory_db, "sid-1", 7, "new")
        with self.assertRaises(SessionHistoryServiceError) as delete_ctx:
            delete_session_history_message_record(memory_db, "sid-1", 7)

        self.assertEqual(update_ctx.exception.status_code, 404)
        self.assertEqual(delete_ctx.exception.status_code, 404)

    def test_internal_errors_map_to_500(self):
        memory_db = FailingMemoryDB(RuntimeError("db unavailable"))

        with self.assertRaises(SessionHistoryServiceError) as list_ctx:
            list_session_history_messages(memory_db, "sid-1")
        with self.assertRaises(SessionHistoryServiceError) as clear_ctx:
            clear_session_history_messages(memory_db, "sid-1")

        self.assertEqual(list_ctx.exception.status_code, 500)
        self.assertEqual(clear_ctx.exception.status_code, 500)
