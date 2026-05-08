import asyncio
import io
import json
import os
import shutil
import sys
import time
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
    get_knowledge_vector_store_status,
    _resolve_kb_manager,
    _KnowledgeUploadStorage,
    list_vault_compile_queue,
    list_vault_candidates,
    list_vault_articles,
    list_vault_source_records,
    list_knowledge_document_page,
    list_knowledge_document_records,
    read_knowledge_document_record,
    read_vault_article,
    read_vault_candidate,
    reindex_knowledge_document_record,
    remove_knowledge_document_record,
    remove_vault_source_record,
    build_vault_rag_context_for_prompt,
    redact_sensitive_rag_text,
    safe_knowledge_filename,
    search_vault_knowledge,
    update_vault_candidate,
    _knowledge_reindex_timeout_seconds,
    _knowledge_setup_timeout_seconds,
)
from core.local_embedding import DEFAULT_LOCAL_EMBEDDING_MODEL


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


class SlowKnowledgeBase(FakeKnowledgeBase):
    async def ingest_document(self, file_path, *_args):
        self.ingested_path = file_path
        await asyncio.sleep(0.2)
        return {"status": "success", "message": "should not finish"}


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

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
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

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertIn("已保存到资料库", message)
        self.assertIn("检索索引未完成", message)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "failed")
        self.assertIn("向量模型没有返回可用结果", vault_records[0]["vector_error"])
        records = asyncio.run(list_knowledge_document_records(kb))
        self.assertIn("向量模型没有返回可用结果", records[0]["vector_error"])

    def test_ingest_times_out_slow_vector_index_without_blocking_upload(self):
        kb = SlowKnowledgeBase("upload_timeout", message="too slow")
        upload = FakeUpload("runbook.txt", b"hello")

        with (
            patch.dict(os.environ, {"OPSCORE_KNOWLEDGE_REINDEX_TIMEOUT_SECONDS": "0.1"}),
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertIn("已保存到资料库", message)
        self.assertIn("向量索引超过 0.1 秒", message)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "failed")
        self.assertIn("向量索引超过 0.1 秒", vault_records[0]["vector_error"])
        self.assertTrue((self.vault_dir / vault_records[0]["source_path"]).exists())

    def test_ingest_times_out_slow_vector_client_setup_without_blocking_upload(self):
        kb = FakeKnowledgeBase("setup_timeout", message="should not ingest")
        upload = FakeUpload("runbook.txt", b"hello")

        def slow_embedding_client(_model_id):
            time.sleep(0.2)
            return object(), "fake-embedding"

        with (
            patch.dict(os.environ, {"OPSCORE_KNOWLEDGE_REINDEX_TIMEOUT_SECONDS": "0.1"}),
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", side_effect=slow_embedding_client),
        ):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertIn("已保存到资料库", message)
        self.assertIn("向量模型初始化超过 0.1 秒", message)
        self.assertIsNone(kb.ingested_path)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "failed")
        self.assertIn("向量模型初始化超过 0.1 秒", vault_records[0]["vector_error"])

    def test_ingest_can_defer_vector_index_for_api_upload(self):
        kb = FakeKnowledgeBase("defer_index", message="should not ingest")
        upload = FakeUpload("runbook.txt", b"hello")

        message = asyncio.run(ingest_knowledge_document(kb, upload, index_now=False))

        self.assertIn("已保存到资料库", message)
        self.assertIn("向量索引未同步执行", message)
        self.assertIsNone(kb.ingested_path)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "pending")
        self.assertIn("重建索引", vault_records[0]["vector_error"])

    def test_ingest_deferred_default_upload_uses_lightweight_storage(self):
        class ExplodingRagManager:
            @property
            def kb_dir(self):
                raise AssertionError("deferred upload should not import RAG runtime")

            def materialize(self):
                raise AssertionError("deferred upload should not materialize LanceDB")

        upload_dir = Path.cwd() / "tests" / "tmp_knowledge_base_service_default_upload"
        fake_rag = ModuleType("core.rag")
        fake_rag.kb_manager = ExplodingRagManager()

        with (
            patch.object(_KnowledgeUploadStorage, "kb_dir", str(upload_dir)),
            patch.dict(sys.modules, {"core.rag": fake_rag}),
        ):
            message = asyncio.run(ingest_knowledge_document(FakeUpload("runbook.txt", b"hello"), index_now=False))

        self.assertIn("向量索引未同步执行", message)
        self.assertTrue(any(upload_dir.glob("runbook*.txt")))
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "pending")

    def test_resolve_kb_manager_can_skip_lazy_materialization_for_upload(self):
        class LazyManager:
            kb_dir = "knowledge_base"

            def __init__(self):
                self.materialized = False

            def materialize(self):
                self.materialized = True
                raise AssertionError("upload path should not materialize LanceDB before persisting")

        lazy_manager = LazyManager()
        fake_rag = ModuleType("core.rag")
        fake_rag.kb_manager = lazy_manager

        with patch.dict(sys.modules, {"core.rag": fake_rag}):
            resolved = _resolve_kb_manager(materialize=False)

        self.assertIs(resolved, lazy_manager)
        self.assertFalse(lazy_manager.materialized)

    def test_ingest_embedding_model_not_found_skips_vector_index(self):
        kb = FakeKnowledgeBase(
            "model_not_found",
            ingest_status="error",
            message='向量模型调用失败：Error code: 404 - {"error":"model not found"}',
        )
        upload = FakeUpload("runbook.txt", b"hello")

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("missing-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "missing-embedding")),
        ):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertIn("RAG 索引跳过", message)
        self.assertIn("向量模型不可用", message)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "skipped")
        records = asyncio.run(list_knowledge_document_records(kb))
        self.assertEqual(records[0]["vector_status"], "skipped")
        self.assertIn("离线 RAG 检索", records[0]["vector_error"])

    def test_ingest_without_embedding_model_skips_vector_index(self):
        kb = FakeKnowledgeBase("no_embedding", message="should not ingest")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            message = asyncio.run(ingest_knowledge_document(kb, upload))

        self.assertIn("已保存到资料库", message)
        self.assertIn("未配置向量模型", message)
        self.assertIsNone(kb.ingested_path)
        vault_records = list_vault_source_records(self.vault_dir)
        self.assertEqual(vault_records[0]["vector_status"], "skipped")
        self.assertIn("未配置向量模型", vault_records[0]["vector_error"])

    def test_read_knowledge_document_record_returns_safe_text_preview(self):
        kb = FakeKnowledgeBase("read_preview", message="注入成功")
        upload = FakeUpload("巡检记录.txt", "CPU 正常\n内存正常\n".encode("utf-8"))

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            asyncio.run(ingest_knowledge_document(kb, upload))

        record = list_vault_source_records(self.vault_dir)[0]
        preview = read_knowledge_document_record(record["filename"], vault_dir=self.vault_dir)

        self.assertEqual(preview["filename"], record["filename"])
        self.assertEqual(preview["content"], "CPU 正常\n内存正常\n")
        self.assertTrue(preview["preview_available"])
        self.assertFalse(preview["truncated"])
        self.assertEqual(preview["content_type"], "text")

    def test_list_knowledge_document_page_filters_and_reports_vector_store(self):
        kb = FakeKnowledgeBase("page", message="注入成功")
        uploads = [
            FakeUpload("Linux 巡检.txt", "CPU 正常\n".encode("utf-8")),
            FakeUpload("Oracle 说明.md", "数据库连接正常\n".encode("utf-8")),
        ]

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            for upload in uploads:
                asyncio.run(ingest_knowledge_document(kb, upload))

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            page = asyncio.run(
                list_knowledge_document_page(
                    kb,
                    query="Oracle",
                    vector_status="skipped",
                    extension=".md",
                    page=1,
                    per_page=10,
                    sort="name_asc",
                )
            )

        self.assertEqual(page["pagination"]["total"], 1)
        self.assertEqual(page["summary"]["total"], 2)
        self.assertEqual(page["summary"]["filtered"], 1)
        self.assertEqual(page["summary"]["vector_counts"]["skipped"], 2)
        self.assertEqual(page["files"][0]["original_filename"], "Oracle 说明.md")
        self.assertEqual(page["vector_store"]["status"], "missing_embedding_model")
        self.assertEqual(page["vector_store"]["database"], "LanceDB")

    def test_reindex_knowledge_document_record_handles_missing_embedding_model(self):
        kb = FakeKnowledgeBase("reindex_no_embedding", message="should not ingest")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            asyncio.run(ingest_knowledge_document(kb, upload))
            record = list_vault_source_records(self.vault_dir)[0]
            result = asyncio.run(
                reindex_knowledge_document_record(
                    record["filename"],
                    kb,
                    vault_dir=self.vault_dir,
                )
            )

        self.assertEqual(result["vector_status"], "skipped")
        self.assertIn("未配置向量模型", result["message"])

    def test_local_embedding_default_reindex_timeout_allows_model_warmup(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPSCORE_KNOWLEDGE_REINDEX_TIMEOUT_SECONDS", None)
            with patch("core.embedding_config.get_embedding_config", return_value=(DEFAULT_LOCAL_EMBEDDING_MODEL, 1024)):
                self.assertGreaterEqual(_knowledge_reindex_timeout_seconds(), 180.0)
                self.assertGreaterEqual(_knowledge_setup_timeout_seconds(180.0), 120.0)

    def test_reindex_knowledge_document_record_rebuilds_vector_index(self):
        kb = FakeKnowledgeBase("reindex_success", message="注入成功")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            asyncio.run(ingest_knowledge_document(kb, upload))
        record = list_vault_source_records(self.vault_dir)[0]

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
            result = asyncio.run(
                reindex_knowledge_document_record(
                    record["filename"],
                    kb,
                    vault_dir=self.vault_dir,
                )
            )

        self.assertEqual(result["vector_status"], "indexed")
        self.assertEqual(result["message"], "注入成功")
        self.assertEqual(kb.ingested_path, str(self.vault_dir / record["source_path"]))

    def test_reindex_knowledge_document_record_times_out_slow_vector_rebuild(self):
        kb = SlowKnowledgeBase("reindex_timeout", message="too slow")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            asyncio.run(ingest_knowledge_document(kb, upload))
        record = list_vault_source_records(self.vault_dir)[0]

        with (
            patch.dict(os.environ, {"OPSCORE_KNOWLEDGE_REINDEX_TIMEOUT_SECONDS": "0.1"}),
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
            result = asyncio.run(
                reindex_knowledge_document_record(
                    record["filename"],
                    kb,
                    vault_dir=self.vault_dir,
                )
            )

        self.assertEqual(result["vector_status"], "failed")
        self.assertIn("向量重建超过", result["message"])

    def test_reindex_knowledge_document_record_times_out_default_manager_resolution(self):
        kb = FakeKnowledgeBase("reindex_manager_timeout", message="ok")
        upload = FakeUpload("runbook.txt", b"hello")

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            asyncio.run(ingest_knowledge_document(kb, upload))
        record = list_vault_source_records(self.vault_dir)[0]

        def slow_resolve(_manager=None):
            time.sleep(0.2)
            return kb

        with (
            patch.dict(os.environ, {"OPSCORE_KNOWLEDGE_REINDEX_TIMEOUT_SECONDS": "0.1"}),
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
            patch("core.knowledge_base_service._resolve_kb_manager", side_effect=slow_resolve),
        ):
            result = asyncio.run(
                reindex_knowledge_document_record(
                    record["filename"],
                    vault_dir=self.vault_dir,
                )
            )

        self.assertEqual(result["vector_status"], "failed")
        self.assertIn("向量库初始化超过", result["message"])

    def test_vector_store_status_reports_actionable_state(self):
        with patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)):
            status = get_knowledge_vector_store_status(
                summary={"vector_counts": {"indexed": 2, "failed": 1, "skipped": 1, "pending": 3}},
            )

        self.assertEqual(status["status"], "needs_attention")
        self.assertEqual(status["status_label"], "部分资料索引失败")
        self.assertEqual(status["failed_count"], 1)
        self.assertTrue(status["model_configured"])
        self.assertIn("重建", status["recommended_action"])
        self.assertGreaterEqual(status["reindex_timeout_seconds"], 0.1)

    def test_list_and_delete_documents_wrap_kb_manager(self):
        kb = FakeKnowledgeBase("records")
        legacy_copy = Path(kb.kb_dir) / "runbook.txt"
        legacy_copy.write_text("legacy upload copy", encoding="utf-8")

        files = asyncio.run(list_knowledge_document_records(kb))
        message = asyncio.run(remove_knowledge_document_record(kb, "runbook.txt"))

        self.assertEqual(files, [{"filename": "runbook.txt", "status": "legacy_vector"}])
        self.assertEqual(message, "已成功从知识库中移除 runbook.txt")
        self.assertFalse(legacy_copy.exists())

    def test_records_use_default_kb_manager_when_not_injected(self):
        kb = FakeKnowledgeBase("default")
        fake_rag = ModuleType("core.rag")
        fake_rag.kb_manager = kb

        with patch.dict(sys.modules, {"core.rag": fake_rag}):
            files = asyncio.run(list_knowledge_document_records())

        self.assertEqual(files, [{"filename": "runbook.txt", "status": "legacy_vector"}])

    def test_remove_default_document_uses_lightweight_storage(self):
        upload_dir = Path.cwd() / "tests" / "tmp_knowledge_base_service_default_remove"

        with patch.object(_KnowledgeUploadStorage, "kb_dir", str(upload_dir)):
            asyncio.run(ingest_knowledge_document(FakeUpload("runbook.txt", b"hello"), index_now=False))
            record = list_vault_source_records(self.vault_dir)[0]
            message = asyncio.run(remove_knowledge_document_record(record["filename"]))

        self.assertIn("资料库移除", message)
        self.assertEqual(list_vault_source_records(self.vault_dir), [])
        self.assertFalse((upload_dir / "runbook.txt").exists())

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

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
            asyncio.run(ingest_knowledge_document(kb, upload))

        record = list_vault_source_records(self.vault_dir)[0]
        self.assertTrue(remove_vault_source_record(record["filename"], self.vault_dir))
        self.assertEqual(list_vault_source_records(self.vault_dir), [])
        self.assertFalse((self.vault_dir / record["source_path"]).exists())
        self.assertFalse((self.vault_dir / record["note_path"]).exists())

    def test_rag_prompt_context_redacts_sensitive_values(self):
        redacted = redact_sensitive_rag_text(
            "CPU 正常\n密码: TopSecret123\napi_token=token-abc\nPasswordAuthentication yes\n"
            "| 资产 | 账号 | 密码 |\n| --- | --- | --- |\n| kmstest | chroot | TableSecret123 |"
            "\n| kmstest | chroot | WeakSecret123! |"
            "\nkmstest 192.168.11.132 chroot PlainSecret123!"
        )

        self.assertIn("CPU 正常", redacted)
        self.assertIn("PasswordAuthentication yes", redacted)
        self.assertIn("kmstest", redacted)
        self.assertIn("[已隐藏]", redacted)
        self.assertNotIn("TopSecret123", redacted)
        self.assertNotIn("token-abc", redacted)
        self.assertNotIn("TableSecret123", redacted)
        self.assertNotIn("WeakSecret123!", redacted)
        self.assertNotIn("PlainSecret123!", redacted)

    def test_build_vault_rag_context_for_prompt_returns_redacted_evidence(self):
        kb = FakeKnowledgeBase("rag_context", message="注入成功")
        upload = FakeUpload(
            "账号巡检.txt",
            "Linux CPU 正常\n账号 chroot\n密码: TopSecret123\n".encode("utf-8"),
        )

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
            asyncio.run(ingest_knowledge_document(kb, upload))

        result = build_vault_rag_context_for_prompt("CPU", vault_dir=self.vault_dir)

        self.assertIn("[OpsCore RAG 证据上下文]", result["context"])
        self.assertIn("Linux CPU 正常", result["context"])
        self.assertIn("[已隐藏]", result["context"])
        self.assertNotIn("TopSecret123", result["context"])
        self.assertGreaterEqual(len(result["references"]), 1)
        self.assertEqual(result["references"][0]["source_type"], "rag")

    def test_rag_prompt_context_matches_natural_language_entity_query_without_vector_index(self):
        kb = FakeKnowledgeBase("rag_entity_query", message="should not index")
        upload = FakeUpload(
            "账号台账.txt",
            (
                "| 资产 | 地址 | 用途 | 账号 | 密码 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| kmstest | 192.168.11.132 | Issue 服务器 | chroot | TopSecret123 |\n"
            ).encode("utf-8"),
        )

        with patch("core.embedding_config.get_embedding_config", return_value=("", 3072)):
            asyncio.run(ingest_knowledge_document(kb, upload))

        search_results = search_vault_knowledge("请帮我查询 kmstest 账号信息", vault_dir=self.vault_dir)
        result = build_vault_rag_context_for_prompt(
            "请帮我查询 kmstest 账号信息",
            vault_dir=self.vault_dir,
        )

        self.assertGreaterEqual(len(search_results), 1)
        self.assertIn("[已隐藏]", search_results[0]["snippet"])
        self.assertNotIn("TopSecret123", search_results[0]["snippet"])
        self.assertIn("kmstest", result["context"])
        self.assertIn("192.168.11.132", result["context"])
        self.assertIn("[已隐藏]", result["context"])
        self.assertNotIn("TopSecret123", result["context"])
        self.assertGreaterEqual(len(result["references"]), 1)

    def test_compile_vault_source_candidate_writes_review_candidate(self):
        kb = FakeKnowledgeBase("compile_candidate", message="注入成功")
        upload = FakeUpload("巡检记录.txt", "CPU 正常\n内存正常\n".encode("utf-8"))

        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
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
        self.assertIn("待确认", candidate_text)
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
        with (
            patch("core.embedding_config.get_embedding_config", return_value=("fake-embedding", 1024)),
            patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
        ):
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

        manifest_path = self.vault_dir / "state" / "sources.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.append(
            {
                **manifest[0],
                "id": "src-duplicate",
                "source_session_id": "source-session-duplicate",
            }
        )
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        graph = build_vault_knowledge_graph(vault_dir=self.vault_dir)
        self.assertGreaterEqual(graph["summary"]["article_count"], 2)
        self.assertGreaterEqual(graph["summary"]["node_count"], 2)
        self.assertGreaterEqual(graph["summary"]["edge_count"], 1)
        self.assertGreaterEqual(graph["summary"]["linked_node_count"], 2)
        self.assertEqual(graph["summary"]["relation_counts"]["wikilink"], 1)
        self.assertTrue(all("x" in node and "y" in node and "degree" in node for node in graph["nodes"]))
        node_ids = [node["id"] for node in graph["nodes"]]
        self.assertEqual(len(node_ids), len(set(node_ids)))
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
