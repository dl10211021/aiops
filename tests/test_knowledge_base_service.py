import asyncio
import io
import os
import shutil
import sys
import unittest
import zipfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from core.knowledge_base_service import (
    KnowledgeBaseServiceError,
    approve_vault_candidate,
    build_vault_knowledge_graph,
    compile_vault_source_candidate,
    create_vault_export_zip,
    ingest_knowledge_document,
    import_vault_archive,
    list_vault_compile_queue,
    list_vault_candidates,
    list_vault_articles,
    list_vault_source_records,
    list_knowledge_document_records,
    read_vault_article,
    read_vault_candidate,
    remove_knowledge_document_record,
    remove_vault_source_record,
    safe_knowledge_filename,
    search_vault_knowledge,
    update_vault_candidate,
)


class FakeUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = io.BytesIO(content)


class FakeKnowledgeBase:
    def __init__(self, name: str, ingest_status: str = "success", message: str = "ok"):
        self.kb_dir = str(Path.cwd() / "tests" / f"tmp_knowledge_base_service_{name}")
        Path(self.kb_dir).mkdir(parents=True, exist_ok=True)
        self.ingest_status = ingest_status
        self.message = message
        self.ingested_path = None

    async def ingest_document(self, file_path, *_args):
        self.ingested_path = file_path
        return {"status": self.ingest_status, "message": self.message}

    async def list_documents(self):
        return ["runbook.txt"]

    async def delete_document(self, filename):
        return {"status": "success", "message": f"已成功从知识库中移除 {filename}"}


class TestKnowledgeBaseService(unittest.TestCase):
    def setUp(self):
        self.vault_dir = Path.cwd() / "tests" / "tmp_knowledge_vault"
        os.environ["OPSCORE_KNOWLEDGE_VAULT_DIR"] = str(self.vault_dir)

    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_knowledge_base_service_*"):
            shutil.rmtree(path, ignore_errors=True)
        shutil.rmtree(self.vault_dir, ignore_errors=True)
        os.environ.pop("OPSCORE_KNOWLEDGE_VAULT_DIR", None)

    def test_safe_filename_rejects_unsupported_extension(self):
        with self.assertRaises(KnowledgeBaseServiceError) as ctx:
            safe_knowledge_filename("../payload.exe")

        self.assertEqual(ctx.exception.status_code, 415)
        self.assertEqual(ctx.exception.detail, "不支持的知识库文件类型: .exe")

    def test_ingest_document_writes_safe_file_and_returns_message(self):
        kb = FakeKnowledgeBase("success", message="注入成功")
        upload = FakeUpload("运维 runbook.md", b"# hello")

        with patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertEqual(message, "注入成功")
        self.assertIsNotNone(kb.ingested_path)
        written_path = Path(kb.ingested_path)
        self.assertTrue(written_path.exists())
        self.assertEqual(written_path.read_bytes(), b"# hello")
        self.assertTrue(written_path.name.endswith(".md"))
        self.assertNotIn(" ", written_path.name)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(len(vault_records), 1)
        self.assertEqual(vault_records[0]["original_filename"], "运维 runbook.md")
        self.assertEqual(vault_records[0]["compile_status"], "pending_ai_compile")
        self.assertTrue(vault_records[0]["source_path"].startswith("raw/uploads/"))
        self.assertTrue(vault_records[0]["note_path"].startswith("wiki/sources/"))
        self.assertTrue((self.vault_dir / vault_records[0]["source_path"]).exists())
        self.assertTrue((self.vault_dir / vault_records[0]["note_path"]).exists())
        self.assertTrue((self.vault_dir / "index.md").exists())
        self.assertTrue((self.vault_dir / "log.md").exists())
        self.assertTrue((self.vault_dir / "purpose.md").exists())
        self.assertTrue((self.vault_dir / "schema.md").exists())
        self.assertTrue((self.vault_dir / "state" / "compile_queue.json").exists())
        queue = list_vault_compile_queue(self.vault_dir)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["original_filename"], "运维 runbook.md")
        self.assertEqual(queue[0]["compile_stage"], "uploaded")
        self.assertEqual(queue[0]["status_label"], "等待辅助模型编译")

    def test_ingest_failure_keeps_vault_copy_for_offline_compile(self):
        kb = FakeKnowledgeBase("ingest_error", ingest_status="error", message="文档内容提取或向量化失败")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertIn("已保存到 Obsidian Vault", message)
        self.assertIn("向量注入失败", message)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "failed")
        self.assertEqual(vault_records[0]["vector_error"], "文档内容提取或向量化失败")

    def test_list_and_delete_documents_wrap_kb_manager(self):
        kb = FakeKnowledgeBase("records")

        files = asyncio.run(list_knowledge_document_records(kb))
        message = asyncio.run(remove_knowledge_document_record(kb, "runbook.txt"))

        self.assertEqual(files, [{"filename": "runbook.txt", "status": "legacy_vector"}])
        self.assertEqual(message, "已成功从知识库中移除 runbook.txt")

    def test_records_use_default_kb_manager_when_not_injected(self):
        kb = FakeKnowledgeBase("default")
        fake_rag = ModuleType("core.rag")
        fake_rag.kb_manager = kb

        with patch.dict(sys.modules, {"core.rag": fake_rag}):
            files = asyncio.run(list_knowledge_document_records())
            message = asyncio.run(remove_knowledge_document_record("runbook.txt"))

        self.assertEqual(files, [{"filename": "runbook.txt", "status": "legacy_vector"}])
        self.assertEqual(message, "已成功从知识库中移除 runbook.txt")

    def test_delete_missing_document_maps_to_404(self):
        class MissingKnowledgeBase(FakeKnowledgeBase):
            async def delete_document(self, filename):
                return {"status": "error", "message": "知识库为空"}

        with self.assertRaises(KnowledgeBaseServiceError) as ctx:
            asyncio.run(remove_knowledge_document_record(MissingKnowledgeBase("missing"), "missing.txt"))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "知识库为空")

    def test_remove_vault_source_record_deletes_source_and_note(self):
        kb = FakeKnowledgeBase("remove_vault", message="注入成功")
        upload = FakeUpload("Oracle 故障.docx", b"doc")

        with patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")):
            asyncio.run(ingest_knowledge_document(kb, upload))

        record = list_vault_source_records(self.vault_dir)[0]
        self.assertTrue(remove_vault_source_record(record["filename"], self.vault_dir))
        self.assertEqual(list_vault_source_records(self.vault_dir), [])
        self.assertFalse((self.vault_dir / record["source_path"]).exists())
        self.assertFalse((self.vault_dir / record["note_path"]).exists())

    def test_compile_vault_source_candidate_writes_review_candidate(self):
        kb = FakeKnowledgeBase("compile_candidate", message="注入成功")
        upload = FakeUpload("巡检记录.txt", "CPU 正常\n内存正常\n".encode("utf-8"))

        with patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")):
            asyncio.run(ingest_knowledge_document(kb, upload))

        record = list_vault_source_records(self.vault_dir)[0]
        updated = asyncio.run(
            compile_vault_source_candidate(
                record["source_session_id"],
                use_ai=False,
                vault_dir=self.vault_dir,
            )
        )

        self.assertEqual(updated["compile_status"], "awaiting_review")
        self.assertEqual(updated["compile_stage"], "candidate_generated")
        self.assertTrue(updated["candidate_path"].startswith("wiki/candidates/"))
        candidate_path = self.vault_dir / updated["candidate_path"]
        self.assertTrue(candidate_path.exists())
        candidate_text = candidate_path.read_text(encoding="utf-8")
        self.assertIn("待人工确认", candidate_text)
        self.assertIn("CPU 正常", candidate_text)
        detail = read_vault_candidate(record["source_session_id"], vault_dir=self.vault_dir)
        self.assertIn("CPU 正常", detail["content"])
        saved = update_vault_candidate(
            record["source_session_id"],
            content=detail["content"] + "\n\n## 人工补充\n\n确认可入库。",
            content_sha256=detail["content_sha256"],
            vault_dir=self.vault_dir,
        )
        self.assertIn("人工补充", saved["content"])
        self.assertEqual(saved["compile_stage"], "candidate_edited")
        with self.assertRaises(KnowledgeBaseServiceError) as stale_ctx:
            update_vault_candidate(
                record["source_session_id"],
                content=saved["content"] + "\n旧版本覆盖",
                content_sha256=detail["content_sha256"],
                vault_dir=self.vault_dir,
            )
        self.assertEqual(stale_ctx.exception.status_code, 409)
        candidates = list_vault_candidates(self.vault_dir)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["review_status"], "pending")

        approved = approve_vault_candidate(
            record["source_session_id"],
            vault_dir=self.vault_dir,
        )
        self.assertEqual(approved["compile_status"], "approved")
        self.assertEqual(approved["compile_stage"], "wiki_approved")
        self.assertTrue(approved["wiki_path"].startswith("wiki/articles/"))
        article_text = (self.vault_dir / approved["wiki_path"]).read_text(encoding="utf-8")
        self.assertIn('review_status: "approved"', article_text)
        self.assertIn('type: "wiki-article"', article_text)
        self.assertEqual(list_vault_compile_queue(self.vault_dir), [])
        articles = list_vault_articles(self.vault_dir)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["review_status"], "approved")
        article_detail = read_vault_article(record["source_session_id"], vault_dir=self.vault_dir)
        self.assertIn("人工补充", article_detail["content"])
        search_results = search_vault_knowledge("CPU", vault_dir=self.vault_dir)
        self.assertTrue(any(item["kind"] == "articles" for item in search_results))
        self.assertTrue(any("CPU" in item["snippet"] or "人工补充" in item["snippet"] for item in search_results))

        related_upload = FakeUpload("网络拓扑.txt", "网关和 Linux 巡检有关联\n".encode("utf-8"))
        with patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")):
            asyncio.run(ingest_knowledge_document(kb, related_upload))
        related_record = [
            item for item in list_vault_source_records(self.vault_dir)
            if item["original_filename"] == "网络拓扑.txt"
        ][0]
        asyncio.run(
            compile_vault_source_candidate(
                related_record["source_session_id"],
                use_ai=False,
                vault_dir=self.vault_dir,
            )
        )
        related_detail = read_vault_candidate(related_record["source_session_id"], vault_dir=self.vault_dir)
        update_vault_candidate(
            related_record["source_session_id"],
            content=related_detail["content"] + "\n\n## 关联知识\n\n- [[巡检记录.txt]]\n",
            content_sha256=related_detail["content_sha256"],
            vault_dir=self.vault_dir,
        )
        approve_vault_candidate(related_record["source_session_id"], vault_dir=self.vault_dir)

        graph = build_vault_knowledge_graph(vault_dir=self.vault_dir)
        self.assertGreaterEqual(graph["summary"]["article_count"], 2)
        self.assertGreaterEqual(graph["summary"]["node_count"], 2)
        self.assertGreaterEqual(graph["summary"]["edge_count"], 1)
        self.assertGreaterEqual(graph["summary"]["linked_node_count"], 2)
        self.assertEqual(graph["summary"]["relation_counts"]["wikilink"], 1)
        self.assertTrue(all("x" in node and "y" in node and "degree" in node for node in graph["nodes"]))
        archive_path = create_vault_export_zip(vault_dir=self.vault_dir)
        self.assertTrue(archive_path.exists())
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
        self.assertIn("index.md", names)
        self.assertTrue(any(name.startswith("wiki/articles/") for name in names))
        restored = import_vault_archive(
            archive_path.read_bytes(),
            filename="vault.zip",
            vault_dir=self.vault_dir / "restored",
        )
        self.assertGreaterEqual(restored["imported_count"], 1)
        self.assertTrue((self.vault_dir / "restored" / "index.md").exists())
