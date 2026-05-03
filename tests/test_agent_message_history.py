import unittest

from core.agent_message_history import build_chat_message_history


class FakeMemoryStore:
    def __init__(self, messages):
        self.messages = messages
        self.appended = []

    def get_messages(self, session_id):
        self.read_session_id = session_id
        return self.messages

    def append_message(self, session_id, message):
        self.appended.append((session_id, message))


class AgentMessageHistoryTests(unittest.TestCase):
    def test_builds_history_without_old_system_prompts_and_persists_safe_user_message(self):
        memory_store = FakeMemoryStore(
            [
                {"role": "system", "content": "old-system"},
                {"role": "assistant", "content": "上一轮结果"},
            ]
        )
        attachments = [
            {
                "filename": "screen.png",
                "kind": "image",
                "content_type": "image/png",
                "data_url": "data:image/png;base64,AAA",
                "size": 10,
            }
        ]

        messages = build_chat_message_history(
            memory_store=memory_store,
            session_id="sid-history",
            system_prompt="new-system",
            user_message="看图",
            user_display_message="看图-展示文本",
            user_attachments=attachments,
            model_name="gpt-4o",
        )

        self.assertEqual(memory_store.read_session_id, "sid-history")
        self.assertEqual(messages[0], {"role": "system", "content": "new-system"})
        self.assertEqual(messages[1], {"role": "assistant", "content": "上一轮结果"})
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(messages[2]["content"][0], {"type": "text", "text": "看图"})
        self.assertEqual(
            messages[2]["content"][1],
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
        )
        self.assertEqual(memory_store.appended[0][0], "sid-history")
        self.assertEqual(memory_store.appended[0][1]["content"], "看图-展示文本")
        self.assertNotIn("data_url", memory_store.appended[0][1]["attachments"][0])

    def test_uses_user_message_when_display_message_is_blank(self):
        memory_store = FakeMemoryStore([])

        messages = build_chat_message_history(
            memory_store=memory_store,
            session_id="sid-history",
            system_prompt="system",
            user_message="原始消息",
            user_display_message=None,
            user_attachments=[],
            model_name="text-only-model",
        )

        self.assertEqual(messages[-1], {"role": "user", "content": "原始消息"})
        self.assertEqual(
            memory_store.appended,
            [("sid-history", {"role": "user", "content": "原始消息"})],
        )


if __name__ == "__main__":
    unittest.main()
