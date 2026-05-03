import sqlite3
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from core.slash_command_store import SlashCommandStore


class SlashCommandStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_slash_command_store_{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_path / "commands.db"
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE slash_commands (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    description TEXT,
                    prompt_template TEXT NOT NULL,
                    category TEXT DEFAULT '自定义',
                    scope_type TEXT DEFAULT 'global',
                    asset_type TEXT,
                    protocol TEXT,
                    host TEXT,
                    readonly INTEGER DEFAULT 1,
                    pinned INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        self.store = SlashCommandStore(self._connect, Lock())

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

    def test_save_list_and_delete_slash_command(self):
        saved = self.store.save_slash_command(
            {
                "id": "cmd-1",
                "label": " /inspect ",
                "prompt_template": "检查 {host}",
                "readonly": True,
                "pinned": True,
                "sort_order": 200,
                "protocol": " SSH ",
            }
        )

        self.assertEqual(saved["id"], "cmd-1")
        self.assertEqual(saved["label"], "/inspect")
        self.assertEqual(saved["protocol"], "ssh")
        self.assertEqual(saved["sort_order"], 100)
        self.assertEqual(self.store.list_slash_commands()[0]["id"], "cmd-1")
        self.assertTrue(self.store.delete_slash_command("cmd-1"))
        self.assertFalse(self.store.delete_slash_command("cmd-1"))


if __name__ == "__main__":
    unittest.main()
