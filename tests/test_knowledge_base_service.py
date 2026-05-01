import asyncio
import io
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core.knowledge_base_service import (
    KnowledgeBaseServiceError,
    ingest_knowledge_document,
    list_knowledge_document_records,
    remove_knowledge_document_record,
    safe_knowledge_filename,
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
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_knowledge_base_service_*"):
            shutil.rmtree(path, ignore_errors=True)

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

    def test_ingest_failure_maps_to_422(self):
        kb = FakeKnowledgeBase("ingest_error", ingest_status="error", message="文档内容提取或向量化失败")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")):
            with self.assertRaises(KnowledgeBaseServiceError) as ctx:
                asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "文档内容提取或向量化失败")

    def test_list_and_delete_documents_wrap_kb_manager(self):
        kb = FakeKnowledgeBase("records")

        files = asyncio.run(list_knowledge_document_records(kb))
        message = asyncio.run(remove_knowledge_document_record(kb, "runbook.txt"))

        self.assertEqual(files, ["runbook.txt"])
        self.assertEqual(message, "已成功从知识库中移除 runbook.txt")

    def test_delete_missing_document_maps_to_404(self):
        class MissingKnowledgeBase(FakeKnowledgeBase):
            async def delete_document(self, filename):
                return {"status": "error", "message": "知识库为空"}

        with self.assertRaises(KnowledgeBaseServiceError) as ctx:
            asyncio.run(remove_knowledge_document_record(MissingKnowledgeBase("missing"), "missing.txt"))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "知识库为空")
