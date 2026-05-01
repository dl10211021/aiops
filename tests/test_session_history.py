import unittest

from core.session_history import (
    clear_session_history,
    delete_session_message,
    get_user_visible_session_history,
    update_session_message_content,
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
            {"role": "tool", "content": "hidden"},
        ]

    def clear_history(self, session_id):
        self.cleared.append(session_id)

    def update_message_content(self, session_id, message_id, content):
        self.updated.append((session_id, message_id, content))
        return {"id": message_id, "content": content}

    def delete_message(self, session_id, message_id):
        self.deleted.append((session_id, message_id))


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

    def test_clear_update_and_delete_delegate_to_memory_db(self):
        memory_db = FakeMemoryDB()

        clear_session_history(memory_db, "sid-1")
        updated = update_session_message_content(memory_db, "sid-1", 7, "new")
        delete_session_message(memory_db, "sid-1", 7)

        self.assertEqual(memory_db.cleared, ["sid-1"])
        self.assertEqual(memory_db.updated, [("sid-1", 7, "new")])
        self.assertEqual(updated, {"id": 7, "content": "new"})
        self.assertEqual(memory_db.deleted, [("sid-1", 7)])
