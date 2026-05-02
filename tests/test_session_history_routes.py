import asyncio
import unittest
from unittest.mock import patch

from api import routes


class FakeMemoryDB:
    def __init__(self):
        self.messages = [
            {"id": 1, "role": "user", "content": "hello"},
            {"id": 2, "role": "assistant", "content": "hi"},
        ]
        self.cleared = []
        self.updated = []
        self.deleted = []

    def get_messages(self, session_id, for_ui=False):
        return self.messages

    def clear_history(self, session_id):
        self.cleared.append(session_id)

    def update_message_content(self, session_id, message_id, content):
        message = {"id": message_id, "role": "user", "content": content}
        self.updated.append((session_id, message_id, content))
        return message

    def delete_message(self, session_id, message_id):
        self.deleted.append((session_id, message_id))


class TestSessionHistoryRoutes(unittest.TestCase):
    def test_session_history_routes_preserve_response_shapes(self):
        memory_db = FakeMemoryDB()

        with patch("core.memory.memory_db", memory_db):
            list_response = asyncio.run(routes.get_session_history("sid-1"))
            clear_response = asyncio.run(routes.delete_session_history("sid-1"))
            update_response = asyncio.run(
                routes.update_session_history_message(
                    "sid-1",
                    1,
                    routes.SessionMessageUpdateRequest(content="updated"),
                )
            )
            delete_response = asyncio.run(
                routes.delete_session_history_message("sid-1", 1)
            )

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
        self.assertEqual(memory_db.cleared, ["sid-1"])
        self.assertEqual(memory_db.updated, [("sid-1", 1, "updated")])
        self.assertEqual(memory_db.deleted, [("sid-1", 1)])


if __name__ == "__main__":
    unittest.main()
