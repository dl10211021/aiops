import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from api import (
    approval_routes,
    chat_routes,
    connection_routes,
    routes,
    session_runtime_routes,
    skill_routes,
)
from api.schemas import (
    ApprovalDecisionRequest,
    CommandRequest,
    CreateSkillRequest,
    MigrateRequest,
    SkillRollbackRequest,
    SkillValidationRequest,
    UserInteractionResponseRequest,
)


class FakeUploadFile:
    filename = "runbook.txt"
    content_type = "text/plain"

    async def read(self, _size=-1):
        return b"hello"


class TestInteractionApprovalSkillRoutes(unittest.TestCase):
    def test_approval_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/session/{session_id}/approve", paths)
        self.assertIn("/session/{session_id}/interaction", paths)
        self.assertIn("/approvals", paths)
        self.assertIn("/approvals/{approval_id}", paths)
        self.assertIn("/approvals/{approval_id}/decision", paths)
        self.assertIn("/approvals/{approval_id}/execute", paths)

    def test_chat_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/chat", paths)
        self.assertIn("/session/{session_id}/chat/stream", paths)
        self.assertIn("/chat/attachments/preview", paths)

    def test_chat_attachment_preview_preserves_response_shape(self):
        attachment = {"filename": "runbook.txt", "text": "hello"}

        with patch(
            "api.chat_routes._preview_attachment_content",
            return_value=attachment,
        ):
            response = asyncio.run(
                chat_routes.preview_chat_attachment(FakeUploadFile())
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"attachment": attachment})

    def test_resume_chat_stream_rejects_missing_run(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(chat_routes.resume_session_chat_stream("missing-session"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_interaction_and_approval_routes_preserve_response_shapes(self):
        approval = {"id": "approval-1", "status": "pending"}
        execution = SimpleNamespace(
            status="success",
            message="rollback complete",
            approval=approval,
            result={"version_id": "v1"},
        )

        with patch("api.approval_routes.submit_user_interaction_response") as submit:
            interaction_response = asyncio.run(
                approval_routes.respond_user_interaction(
                    "sid-1",
                    UserInteractionResponseRequest(
                        request_id="interaction-1",
                        value="yes",
                    ),
                )
            )

        with patch("api.approval_routes.list_approval_request_records", return_value=[approval]):
            list_response = asyncio.run(approval_routes.list_approval_requests(status="pending"))

        with patch("api.approval_routes.get_approval_request_record", return_value=approval):
            get_response = asyncio.run(approval_routes.get_approval_request("approval-1"))

        with patch("api.approval_routes.decide_approval_request_record", return_value=approval):
            decision_response = asyncio.run(
                approval_routes.decide_approval_request(
                    "approval-1",
                    ApprovalDecisionRequest(approved=True),
                )
            )

        with patch("api.approval_routes.execute_custom_skill_rollback_approval", return_value=execution):
            execute_response = asyncio.run(approval_routes.execute_approval_request("approval-1"))

        with patch("api.session_runtime_routes.request_session_stop") as request_stop:
            stop_response = asyncio.run(session_runtime_routes.stop_chat_session("sid-1"))

        submit.assert_called_once()
        request_stop.assert_called_once()
        self.assertEqual(interaction_response.status, "success")
        self.assertEqual(interaction_response.message, "交互输入已提交。")
        self.assertEqual(list_response.data, {"approvals": [approval]})
        self.assertEqual(get_response.data, {"approval": approval})
        self.assertEqual(decision_response.message, "审批已处理")
        self.assertEqual(decision_response.data, {"approval": approval})
        self.assertEqual(execute_response.status, "success")
        self.assertEqual(execute_response.message, "rollback complete")
        self.assertEqual(
            execute_response.data,
            {"approval": approval, "result": {"version_id": "v1"}},
        )
        self.assertEqual(stop_response.status, "success")
        self.assertEqual(stop_response.message, "已发送中止信号。")

    def test_legacy_command_route_preserves_response_shape(self):
        result = {"stdout": "ok"}

        with patch("api.connection_routes.execute_legacy_command_record", return_value=result):
            response = asyncio.run(
                connection_routes.execute_remote_command(
                    CommandRequest(session_id="sid-1", command="uptime")
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, result)

    def test_skill_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/skills/scan", paths)
        self.assertIn("/skills/registry", paths)
        self.assertIn("/skills/registry/{skill_id}", paths)
        self.assertIn("/skills/create", paths)
        self.assertIn("/skills/validate", paths)
        self.assertIn("/skills/{skill_id}/versions", paths)
        self.assertIn("/skills/{skill_id}/rollback", paths)
        self.assertIn("/skills/migrate", paths)

    def test_skill_routes_preserve_response_shapes(self):
        registry = {"registry": [{"id": "safe-skill"}]}
        detail = {"skill_id": "safe-skill", "content": "---"}
        created = {"message": "技能已创建", "data": {"skill_id": "safe-skill"}}
        validation = {"valid": True, "issues": []}
        versions = [{"id": "v1"}]
        rollback = {"status": "success", "message": "已回滚", "data": {"id": "v1"}}
        migrated = {"message": "技能已导入"}

        with patch("api.skill_routes.scan_custom_skill_catalog", return_value={"message": "扫描完成"}):
            scan_response = asyncio.run(skill_routes.scan_skills())

        with patch("api.skill_routes.list_custom_skill_catalog", return_value=registry):
            registry_response = asyncio.run(skill_routes.get_skill_registry())

        with patch("api.skill_routes.get_custom_skill_detail_record", return_value=detail):
            detail_response = asyncio.run(skill_routes.get_skill_detail("safe-skill"))

        with patch("api.skill_routes.create_custom_skill_record", return_value=created):
            create_response = asyncio.run(
                skill_routes.create_skill(
                    CreateSkillRequest(
                        skill_id="safe-skill",
                        description="desc",
                        instructions="body",
                    )
                )
            )

        with patch("api.skill_routes.validate_skill_candidate", return_value=validation):
            validation_response = asyncio.run(
                skill_routes.validate_skill(
                    SkillValidationRequest(
                        skill_id="safe-skill",
                        file_name="SKILL.md",
                        content="---",
                    )
                )
            )

        with patch("api.skill_routes.list_custom_skill_version_records", return_value=versions):
            versions_response = asyncio.run(skill_routes.list_skill_versions("safe-skill"))

        with patch("api.skill_routes.rollback_custom_skill_version_record", return_value=rollback):
            rollback_response = asyncio.run(
                skill_routes.rollback_skill_version(
                    "safe-skill",
                    SkillRollbackRequest(version_id="v1"),
                )
            )

        with patch("api.skill_routes.migrate_custom_skill_record", return_value=migrated):
            migrate_response = asyncio.run(
                skill_routes.migrate_skill(
                    MigrateRequest(
                        source_path="D:/market/safe-skill",
                        target_dir_name="safe-skill",
                    )
                )
            )

        self.assertEqual(scan_response.message, "扫描完成")
        self.assertEqual(registry_response.data, registry)
        self.assertEqual(detail_response.data, detail)
        self.assertEqual(create_response.message, "技能已创建")
        self.assertEqual(create_response.data, {"skill_id": "safe-skill"})
        self.assertEqual(validation_response.data, validation)
        self.assertEqual(versions_response.data, {"versions": versions})
        self.assertEqual(rollback_response.message, "已回滚")
        self.assertEqual(rollback_response.data, {"id": "v1"})
        self.assertEqual(migrate_response.message, "技能已导入")


if __name__ == "__main__":
    unittest.main()
