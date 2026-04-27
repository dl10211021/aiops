import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from api import routes


class TestApiErrorSemantics(unittest.TestCase):
    def test_poll_missing_session_returns_404(self):
        with patch.dict(routes.ssh_manager.active_sessions, {}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.poll_session_messages("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_disconnect_missing_session_returns_404(self):
        with patch.object(routes.ssh_manager, "disconnect", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.close_ssh_connection("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_session_history_internal_error_returns_500(self):
        class FakeMemoryDB:
            def get_messages(self, *_args, **_kwargs):
                raise RuntimeError("db unavailable")

            def clear_history(self, *_args, **_kwargs):
                raise RuntimeError("db unavailable")

        with patch("core.memory.memory_db", FakeMemoryDB()):
            with self.assertRaises(HTTPException) as get_ctx:
                asyncio.run(routes.get_session_history("sid-1"))
            with self.assertRaises(HTTPException) as delete_ctx:
                asyncio.run(routes.delete_session_history("sid-1"))

        self.assertEqual(get_ctx.exception.status_code, 500)
        self.assertEqual(delete_ctx.exception.status_code, 500)

    def test_knowledge_upload_rejects_unsupported_extension_with_415(self):
        upload = UploadFile(filename="payload.exe", file=io.BytesIO(b"nope"))

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(routes.upload_knowledge_document(upload))

        self.assertEqual(ctx.exception.status_code, 415)

    def test_knowledge_upload_ingest_failure_returns_422(self):
        class FakeKnowledgeBase:
            def __init__(self, kb_dir: str):
                self.kb_dir = kb_dir

            async def ingest_document(self, *_args, **_kwargs):
                return {"status": "error", "message": "文档内容提取或向量化失败"}

        with tempfile.TemporaryDirectory() as tmp:
            upload = UploadFile(filename="runbook.txt", file=io.BytesIO(b"hello"))
            with (
                patch("core.rag.kb_manager", FakeKnowledgeBase(tmp)),
                patch("core.llm_factory.get_embedding_client_and_model", return_value=(object(), "fake-embedding")),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(routes.upload_knowledge_document(upload))

        self.assertEqual(ctx.exception.status_code, 422)

    def test_knowledge_list_and_delete_errors_use_http_status(self):
        class FakeKnowledgeBase:
            async def list_documents(self):
                raise RuntimeError("lancedb unavailable")

            async def delete_document(self, _filename):
                return {"status": "error", "message": "知识库为空"}

        with patch("core.rag.kb_manager", FakeKnowledgeBase()):
            with self.assertRaises(HTTPException) as list_ctx:
                asyncio.run(routes.list_knowledge_documents())
            with self.assertRaises(HTTPException) as delete_ctx:
                asyncio.run(routes.delete_knowledge_document("missing.txt"))

        self.assertEqual(list_ctx.exception.status_code, 500)
        self.assertEqual(delete_ctx.exception.status_code, 404)

    def test_notification_test_missing_config_and_unknown_channel_use_http_errors(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(HTTPException) as wechat_ctx:
                asyncio.run(
                    routes.test_notification_channel(
                        routes.TestNotificationRequest(channel="wechat")
                    )
                )
            with self.assertRaises(HTTPException) as dingtalk_ctx:
                asyncio.run(
                    routes.test_notification_channel(
                        routes.TestNotificationRequest(channel="dingtalk")
                    )
                )
            with self.assertRaises(HTTPException) as email_ctx:
                asyncio.run(
                    routes.test_notification_channel(
                        routes.TestNotificationRequest(channel="email")
                    )
                )
            with self.assertRaises(HTTPException) as unknown_ctx:
                asyncio.run(
                    routes.test_notification_channel(
                        routes.TestNotificationRequest(channel="sms")
                    )
                )

        self.assertEqual(wechat_ctx.exception.status_code, 400)
        self.assertEqual(dingtalk_ctx.exception.status_code, 400)
        self.assertEqual(email_ctx.exception.status_code, 400)
        self.assertEqual(unknown_ctx.exception.status_code, 422)

    def test_notification_send_failure_returns_bad_gateway(self):
        with (
            patch.dict("os.environ", {"WECHAT_WEBHOOK_URL": "https://example.invalid/webhook"}, clear=True),
            patch("urllib.request.urlopen", side_effect=OSError("network down")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    routes.test_notification_channel(
                        routes.TestNotificationRequest(channel="wechat")
                    )
                )

        self.assertEqual(ctx.exception.status_code, 502)

    def test_session_export_empty_and_internal_errors_use_http_status(self):
        class EmptyMemoryDB:
            def get_messages(self, *_args, **_kwargs):
                return []

        class FailingMemoryDB:
            def get_messages(self, *_args, **_kwargs):
                raise RuntimeError("db unavailable")

        with patch("core.memory.memory_db", EmptyMemoryDB()):
            with self.assertRaises(HTTPException) as empty_ctx:
                asyncio.run(routes.export_session_history("sid-empty"))

        with patch("core.memory.memory_db", FailingMemoryDB()):
            with self.assertRaises(HTTPException) as failing_ctx:
                asyncio.run(routes.export_session_history("sid-error"))

        self.assertEqual(empty_ctx.exception.status_code, 404)
        self.assertEqual(failing_ctx.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
