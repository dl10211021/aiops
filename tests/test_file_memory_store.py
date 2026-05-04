import json
import shutil
import unittest
import uuid
from pathlib import Path

from core.file_memory_store import FileMemoryStore, memory_scope_path, safe_memory_segment


class FileMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_file_memory_{uuid.uuid4().hex}"
        self.store = FileMemoryStore(self.tmp_path)

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def test_append_memory_writes_markdown_and_version_log(self):
        version = self.store.append_memory(
            scope_id="asset:ssh:10.0.0.1:22",
            summary="【记忆类型】纠错经验\n【核心记忆】不要直接建议 ufw enable。",
            source_session_id="sid-1",
            metadata={"source": "feedback"},
        )

        memory_path = self.tmp_path / "assets" / "ssh_10.0.0.1_22" / "memory.md"
        version_files = list((self.tmp_path / "versions").glob("*.jsonl"))

        self.assertTrue(memory_path.exists())
        self.assertEqual(version["operation"], "created")
        self.assertEqual(version["path"], "assets/ssh_10.0.0.1_22/memory.md")
        self.assertEqual(len(version_files), 1)
        self.assertIn("不要直接建议 ufw enable", memory_path.read_text(encoding="utf-8"))

        events = [
            json.loads(line)
            for line in version_files[0].read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(events[0]["operation"], "created")
        self.assertEqual(events[0]["source_session_id"], "sid-1")

    def test_search_returns_relevant_scope_entries_without_duplicates(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】Linux 巡检需要先看 systemctl failed。",
            source_session_id="sid-1",
        )
        self.store.append_memory(
            scope_id="asset-host:10.0.0.1",
            summary="【核心记忆】Oracle 资产优先检查活跃会话和锁等待。",
            source_session_id="sid-2",
        )

        results = self.store.search(
            scope_ids=["sid-1", "asset-host:10.0.0.1"],
            query="Oracle 锁等待",
            limit=2,
        )

        self.assertEqual(results[0]["_memory_scope_id"], "asset-host:10.0.0.1")
        self.assertIn("Oracle", results[0]["summary"])
        self.assertEqual(len(results), 2)

    def test_list_read_delete_and_versions_support_management_ui(self):
        self.store.append_memory(
            scope_id="asset-host:10.0.0.8",
            summary="【核心记忆】巡检前先确认只读模式。",
            source_session_id="sid-8",
        )

        items = self.store.list_memories()
        detail = self.store.read_memory(items[0]["path"])
        deleted = self.store.delete_memory(items[0]["path"], actor="tester")
        versions = self.store.list_versions()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["entries"], 1)
        self.assertIn("只读模式", items[0]["preview"])
        self.assertIn("只读模式", detail["content"])
        self.assertEqual(deleted["operation"], "deleted")
        operations = [version["operation"] for version in versions]
        self.assertIn("deleted", operations)
        deleted_versions = [
            version for version in versions if version["operation"] == "deleted"
        ]
        self.assertEqual(deleted_versions[0]["metadata"]["actor"], "tester")
        self.assertEqual(self.store.list_memories(), [])

    def test_memory_paths_are_scoped_and_sanitized(self):
        self.assertEqual(safe_memory_segment("../evil host"), "evil_host")
        self.assertEqual(
            memory_scope_path("asset-kind:oracle/sql").as_posix(),
            "asset_kinds/oracle_sql/memory.md",
        )


if __name__ == "__main__":
    unittest.main()
