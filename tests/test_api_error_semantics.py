import asyncio
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from api import (
    approval_routes,
    asset_routes,
    config_routes,
    connection_routes,
    knowledge_routes,
    notification_routes,
    routes,
    session_history_routes,
    session_runtime_routes,
)
from api.schemas import (
    ToolApprovalRequest,
    BatchAssetImportItem,
    SafetyPolicyTestRequest,
    SafetyPolicyUpdateRequest,
    TestNotificationRequest,
    UserInteractionResponseRequest,
)


class TestApiErrorSemantics(unittest.TestCase):
    def test_poll_missing_session_returns_404(self):
        with patch.dict(session_runtime_routes.ssh_manager.active_sessions, {}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(session_runtime_routes.poll_session_messages("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_disconnect_missing_session_returns_404(self):
        with patch.object(connection_routes.ssh_manager, "disconnect", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(connection_routes.close_ssh_connection("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_session_history_internal_error_returns_500(self):
        class FakeMemoryDB:
            def get_messages(self, *_args, **_kwargs):
                raise RuntimeError("db unavailable")

            def clear_history(self, *_args, **_kwargs):
                raise RuntimeError("db unavailable")

        with patch("core.memory.memory_db", FakeMemoryDB()):
            with self.assertRaises(HTTPException) as get_ctx:
                asyncio.run(session_history_routes.get_session_history("sid-1"))
            with self.assertRaises(HTTPException) as delete_ctx:
                asyncio.run(session_history_routes.delete_session_history("sid-1"))

        self.assertEqual(get_ctx.exception.status_code, 500)
        self.assertEqual(delete_ctx.exception.status_code, 500)

    def test_knowledge_upload_rejects_unsupported_extension_with_415(self):
        upload = UploadFile(filename="payload.exe", file=io.BytesIO(b"nope"))

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(knowledge_routes.upload_knowledge_document(upload))

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
                    asyncio.run(knowledge_routes.upload_knowledge_document(upload))

        self.assertEqual(ctx.exception.status_code, 422)

    def test_knowledge_list_and_delete_errors_use_http_status(self):
        class FakeKnowledgeBase:
            async def list_documents(self):
                raise RuntimeError("lancedb unavailable")

            async def delete_document(self, _filename):
                return {"status": "error", "message": "知识库为空"}

        with patch("core.rag.kb_manager", FakeKnowledgeBase()):
            with self.assertRaises(HTTPException) as list_ctx:
                asyncio.run(knowledge_routes.list_knowledge_documents())
            with self.assertRaises(HTTPException) as delete_ctx:
                asyncio.run(knowledge_routes.delete_knowledge_document("missing.txt"))

        self.assertEqual(list_ctx.exception.status_code, 500)
        self.assertEqual(delete_ctx.exception.status_code, 404)

    def test_notification_test_missing_config_and_unknown_channel_use_http_errors(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(HTTPException) as wechat_ctx:
                asyncio.run(
                    notification_routes.test_notification_channel(
                        TestNotificationRequest(channel="wechat")
                    )
                )
            with self.assertRaises(HTTPException) as dingtalk_ctx:
                asyncio.run(
                    notification_routes.test_notification_channel(
                        TestNotificationRequest(channel="dingtalk")
                    )
                )
            with self.assertRaises(HTTPException) as email_ctx:
                asyncio.run(
                    notification_routes.test_notification_channel(
                        TestNotificationRequest(channel="email")
                    )
                )
            with self.assertRaises(HTTPException) as unknown_ctx:
                asyncio.run(
                    notification_routes.test_notification_channel(
                        TestNotificationRequest(channel="sms")
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
                    notification_routes.test_notification_channel(
                        TestNotificationRequest(channel="wechat")
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
                asyncio.run(session_history_routes.export_session_history("sid-empty"))

        with patch("core.memory.memory_db", FailingMemoryDB()):
            with self.assertRaises(HTTPException) as failing_ctx:
                asyncio.run(session_history_routes.export_session_history("sid-error"))

        self.assertEqual(empty_ctx.exception.status_code, 404)
        self.assertEqual(failing_ctx.exception.status_code, 500)

    def test_legacy_approval_missing_request_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                approval_routes.approve_tool_call(
                    "sid-1",
                    ToolApprovalRequest(
                        tool_call_id="missing-approval",
                        approved=True,
                    ),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_user_interaction_response_resolves_pending_future(self):
        from core.dispatcher import dispatcher

        async def exercise():
            future = asyncio.Future()
            dispatcher.pending_interactions["interaction-1"] = {
                "future": future,
                "session_id": "sid-1",
            }
            try:
                response = await approval_routes.respond_user_interaction(
                    "sid-1",
                    UserInteractionResponseRequest(
                        request_id="interaction-1",
                        value="blue team",
                        label="蓝队方案",
                    ),
                )
                self.assertEqual(response.status, "success")
                self.assertEqual(future.result()["value"], "blue team")
                self.assertEqual(future.result()["label"], "蓝队方案")
            finally:
                dispatcher.pending_interactions.pop("interaction-1", None)

        asyncio.run(exercise())

    def test_user_interaction_missing_request_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                approval_routes.respond_user_interaction(
                    "sid-1",
                    UserInteractionResponseRequest(request_id="missing-interaction"),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_user_interaction_wrong_session_returns_404(self):
        from core.dispatcher import dispatcher

        async def exercise():
            future = asyncio.Future()
            dispatcher.pending_interactions["interaction-2"] = {
                "future": future,
                "session_id": "sid-owner",
            }
            try:
                with self.assertRaises(HTTPException) as ctx:
                    await approval_routes.respond_user_interaction(
                        "sid-other",
                        UserInteractionResponseRequest(
                            request_id="interaction-2",
                            value="should-not-submit",
                        ),
                    )
                self.assertEqual(ctx.exception.status_code, 404)
                self.assertFalse(future.done())
            finally:
                dispatcher.pending_interactions.pop("interaction-2", None)

        asyncio.run(exercise())

    def test_safety_policy_test_endpoint_previews_without_execution(self):
        response = asyncio.run(
            config_routes.test_safety_policy_endpoint(
                SafetyPolicyTestRequest(
                    tool_name="linux_execute_command",
                    command="rm -rf /",
                    allow_modifications=True,
                )
            )
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["result"]["decision"], "deny")

    def test_safety_policy_test_endpoint_returns_business_actions(self):
        response = asyncio.run(
            config_routes.test_safety_policy_endpoint(
                SafetyPolicyTestRequest(
                    tool_name="db_execute_query",
                    sql="ALTER SYSTEM SWITCH LOGFILE",
                    allow_modifications=True,
                    asset_type="oracle",
                    protocol="oracle",
                )
            )
        )

        result = response.data["result"]
        self.assertEqual(response.status, "success")
        self.assertEqual(result["decision"], "approval")
        self.assertEqual(result["primary_action"]["id"], "sql.instance_admin")
        self.assertEqual(result["actions"][0]["label"], "数据库实例管理")

    def test_safety_policy_test_request_rejects_unknown_tool(self):
        with self.assertRaises(ValidationError):
            SafetyPolicyTestRequest(
                tool_name="unknown_execute",
                command="echo ok",
            )

    def test_safety_policy_test_request_accepts_registered_auxiliary_tools(self):
        memcached = SafetyPolicyTestRequest(
            tool_name="memcached_execute_command",
            command="flush_all",
        )
        service_probe = SafetyPolicyTestRequest(
            tool_name="service_probe_request",
            method="GET",
            path="/health",
        )
        snmp = SafetyPolicyTestRequest(
            tool_name="snmp_get",
            oid="1.3.6.1.2.1.1.1.0",
        )

        self.assertEqual(memcached.tool_args(), {"command": "flush_all"})
        self.assertEqual(service_probe.tool_args()["path"], "/health")
        self.assertEqual(snmp.tool_args(), {"oid": "1.3.6.1.2.1.1.1.0"})

    def test_chat_attachment_preview_parses_text_and_xlsx_content(self):
        text_preview = routes._preview_attachment_content(
            "runbook.txt",
            "text/plain",
            "巡检步骤\n1. 查看服务状态".encode("utf-8"),
        )

        xlsx_bytes = io.BytesIO()
        with zipfile.ZipFile(xlsx_bytes, "w") as zf:
            zf.writestr(
                "xl/sharedStrings.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <si><t>资产</t></si><si><t>状态</t></si><si><t>oracle-01</t></si><si><t>异常</t></si>
                </sst>""",
            )
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <sheetData>
                    <row><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row>
                    <row><c t="s"><v>2</v></c><c t="s"><v>3</v></c></row>
                  </sheetData>
                </worksheet>""",
            )

        xlsx_preview = routes._preview_attachment_content(
            "assets.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            xlsx_bytes.getvalue(),
        )
        image_preview = routes._preview_attachment_content(
            "screen.png",
            "image/png",
            b"\x89PNG\r\n\x1a\n",
        )

        self.assertIn("查看服务状态", text_preview["text"])
        self.assertIn("oracle-01", xlsx_preview["text"])
        self.assertEqual(xlsx_preview["rows"], 2)
        self.assertEqual(image_preview["kind"], "image")
        self.assertIn("图片文件：screen.png", image_preview["text"])

    def test_chat_request_normalizes_attachment_metadata_and_rejects_bad_data_url(self):
        req = routes.ChatRequest(
            session_id="sid",
            message="hello",
            attachments=[
                {
                    "filename": "../screen.png",
                    "ext": ".png",
                    "size": 5,
                    "kind": "image",
                    "pages": 2,
                    "rows": 3,
                    "sheets": ["Sheet1", "x" * 120],
                    "truncated": True,
                    "data_url": "data:image/png;base64,aGVsbG8=",
                }
            ],
        )

        self.assertEqual(req.attachments[0]["filename"], "screen.png")
        self.assertEqual(req.attachments[0]["content_type"], "image/png")
        self.assertEqual(req.attachments[0]["pages"], 2)
        self.assertEqual(req.attachments[0]["rows"], 3)
        self.assertEqual(req.attachments[0]["sheets"], ["Sheet1", "x" * 80])
        self.assertTrue(req.attachments[0]["truncated"])
        self.assertNotIn("..", req.attachments[0]["filename"])

        with self.assertRaises(ValidationError):
            routes.ChatRequest(
                session_id="sid",
                message="hello",
                attachments=[
                    {
                        "filename": "bad.txt",
                        "size": 5,
                        "kind": "document",
                        "data_url": "data:image/png;base64,aGVsbG8=",
                    }
                ],
            )

    def test_safety_policy_update_rejects_invalid_regex_with_422(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                config_routes.update_safety_policy_endpoint(
                    SafetyPolicyUpdateRequest(
                        policy={
                            "rules": [
                                {
                                    "id": "bad-regex",
                                    "name": "坏正则",
                                    "decision": "deny",
                                    "matchers": [{"type": "regex", "value": "["}],
                                }
                            ]
                        }
                    )
                )
            )

        self.assertEqual(ctx.exception.status_code, 422)

    def test_models_empty_result_returns_bad_gateway(self):
        with patch("api.config_routes.fetch_model_catalog", return_value=[]):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(config_routes.get_models())

        self.assertEqual(ctx.exception.status_code, 502)

    def test_batch_asset_import_empty_and_internal_errors_use_http_status(self):
        class FailingMemoryDB:
            def save_assets_batch(self, _items):
                raise RuntimeError("sqlite unavailable")

        with self.assertRaises(HTTPException) as empty_ctx:
            asyncio.run(asset_routes.batch_import_assets([]))

        item = BatchAssetImportItem(
            host="10.0.0.10",
            username="root",
        )
        with patch("core.memory.memory_db", FailingMemoryDB()):
            with self.assertRaises(HTTPException) as failing_ctx:
                asyncio.run(asset_routes.batch_import_assets([item]))

        self.assertEqual(empty_ctx.exception.status_code, 422)
        self.assertEqual(failing_ctx.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
