import asyncio
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from core.dispatcher_memory_tools import execute_memory_tool
from core.file_memory_store import FileMemoryStore


class DispatcherMemoryToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_dispatcher_memory_{uuid.uuid4().hex}"
        self.store = FileMemoryStore(self.tmp_path)
        self.context = {
            "session_id": "sid-1",
            "host": "10.0.0.1",
            "port": 22,
            "protocol": "ssh",
            "asset_type": "linux",
            "memory_scope_ids": ["sid-1", "asset-host:10.0.0.1"],
        }

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def test_memory_write_list_read_edit_delete_roundtrip(self):
        with patch("core.memory.memory_db.file_memory_store", self.store):
            write_result = json.loads(
                asyncio.run(
                    execute_memory_tool(
                        "memory_write",
                        {
                            "scope": "current_host",
                            "content": "【核心记忆】这台主机的 SSH 高频登录来自 OpsCore 本机采集，不作为异常。",
                        },
                        self.context,
                    )
                )
            )
            list_result = json.loads(
                asyncio.run(execute_memory_tool("memory_list", {"query": "SSH 高频登录"}, self.context))
            )
            path = list_result["results"][0]["_memory_path"]
            read_result = json.loads(
                asyncio.run(execute_memory_tool("memory_read", {"path": path}, self.context))
            )
            edited_content = read_result["memory"]["content"] + "\n【禁用条件】来源 IP 变化时必须重新确认。"
            edit_result = json.loads(
                asyncio.run(
                    execute_memory_tool(
                        "memory_edit",
                        {
                            "path": path,
                            "content": edited_content,
                            "content_sha256": read_result["memory"]["content_sha256"],
                        },
                        self.context,
                    )
                )
            )
            delete_result = json.loads(
                asyncio.run(execute_memory_tool("memory_delete", {"path": path}, self.context))
            )

        self.assertEqual(write_result["status"], "SUCCESS")
        self.assertEqual(write_result["version"]["operation"], "created")
        self.assertEqual(read_result["status"], "SUCCESS")
        self.assertIn("OpsCore 本机采集", read_result["memory"]["content"])
        self.assertEqual(edit_result["version"]["operation"], "modified")
        self.assertEqual(delete_result["version"]["operation"], "deleted")

    def test_memory_list_without_query_is_context_scoped(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】当前会话记忆。",
            source_session_id="sid-1",
        )
        self.store.append_memory(
            scope_id="sid-other",
            summary="【核心记忆】其他会话记忆。",
            source_session_id="sid-other",
        )

        with patch("core.memory.memory_db.file_memory_store", self.store):
            result = json.loads(asyncio.run(execute_memory_tool("memory_list", {}, self.context)))

        previews = [item["preview"] for item in result["memories"]]
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(len(previews), 1)
        self.assertIn("当前会话记忆", previews[0])


if __name__ == "__main__":
    unittest.main()
