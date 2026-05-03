import json
import shutil
import sqlite3
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from core.session_message_store import SessionMessageStore, sanitize_message_sequence


class SessionMessageStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = (
            Path.cwd() / "tests" / f"tmp_session_message_store_{uuid.uuid4().hex}"
        )
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_path / "messages.db"
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message_json TEXT,
                    is_compressed INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        self.store = SessionMessageStore(self._connect, Lock())

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _insert_message(
        self,
        session_id: str,
        message: dict,
        is_compressed: int = 0,
    ) -> int:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "INSERT INTO memory (session_id, message_json, is_compressed) VALUES (?, ?, ?)",
                (session_id, json.dumps(message, ensure_ascii=False), is_compressed),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def test_append_and_get_messages_preserves_ui_ids_and_filters_runtime_notices(self):
        self.store.append_message("sid-1", {"role": "user", "content": "hi"})
        self.store.append_message(
            "sid-1",
            {
                "role": "user",
                "content": "[System Auto Reply] Tools execution complete.",
            },
        )
        self.store.append_message(
            "sid-1",
            {"role": "assistant", "content": "[System Notice: hidden]"},
        )
        self.store.append_message("sid-1", {"role": "assistant", "content": "hello"})

        messages = self.store.get_messages("sid-1", for_ui=True)

        self.assertEqual([msg["content"] for msg in messages], ["hi", "hello"])
        self.assertEqual([msg["role"] for msg in messages], ["user", "assistant"])
        self.assertTrue(all("_memory_id" in msg for msg in messages))

    def test_model_context_filters_protocol_retry_noise_but_ui_keeps_it(self):
        noise = {
            "role": "assistant",
            "content": "我将通过本地脚本 run_winrm.py 尝试 Windows 密码试错。",
        }
        normal = {"role": "assistant", "content": "正常巡检结果"}
        self.store.append_message("sid-1", noise)
        self.store.append_message("sid-1", normal)

        self.assertEqual(self.store.get_messages("sid-1", for_ui=False), [normal])
        self.assertEqual(
            [msg["content"] for msg in self.store.get_messages("sid-1", for_ui=True)],
            [noise["content"], normal["content"]],
        )

    def test_sanitize_sequence_removes_orphan_and_incomplete_tool_calls(self):
        messages = sanitize_message_sequence(
            [
                {"role": "user", "content": "inspect"},
                {"role": "tool", "tool_call_id": "orphan", "content": "orphan"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": "call-a"}, {"id": "call-b"}],
                },
                {"role": "tool", "tool_call_id": "call-a", "content": "partial"},
                {"role": "user", "content": "next"},
            ]
        )

        self.assertEqual(
            [msg["role"] for msg in messages],
            ["user", "assistant", "user"],
        )
        self.assertNotIn("tool_calls", messages[1])
        self.assertEqual(messages[1]["content"], "[Action aborted or incomplete]")

    def test_update_delete_and_clear_history_apply_visible_message_rules(self):
        user_id = self._insert_message("sid-1", {"role": "user", "content": "old"})
        assistant_id = self._insert_message(
            "sid-1",
            {
                "role": "assistant",
                "content": "old answer",
                "tool_calls": [{"id": "call-a"}],
            },
        )
        tool_id = self._insert_message(
            "sid-1",
            {"role": "tool", "tool_call_id": "call-a", "content": "result"},
        )

        updated = self.store.update_message_content("sid-1", assistant_id, "new answer")
        self.assertEqual(updated["_memory_id"], assistant_id)
        self.assertEqual(updated["content"], "new answer")
        self.assertIn("edited_at", updated)
        self.assertNotIn("tool_calls", updated)

        with self.assertRaisesRegex(ValueError, "只能删除用户消息或 AI 输出"):
            self.store.delete_message("sid-1", tool_id)

        self.store.delete_message("sid-1", user_id)
        self.assertEqual(
            [msg["content"] for msg in self.store.get_messages("sid-1")],
            ["new answer"],
        )

        self.store.clear_history("sid-1")
        self.assertEqual(self.store.get_messages("sid-1", for_ui=True), [])


if __name__ == "__main__":
    unittest.main()
