import unittest

from core.session_history import (
    build_session_history_markdown,
    clear_session_history,
    delete_session_message,
    get_user_visible_session_history,
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

    def update_message_feedback(self, session_id, message_id, rating, note=None):
        self.feedback.append((session_id, message_id, rating, note))
        return {"id": message_id, "feedback": {"rating": rating, "note": note or ""}}


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
