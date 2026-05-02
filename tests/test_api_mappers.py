import unittest

from api.mappers import (
    asset_verification_matrix_response_kwargs,
    asset_verification_run_response_kwargs,
    asset_verification_runs_response_kwargs,
    chat_stream_agent_kwargs,
    custom_skill_create_kwargs,
    custom_skill_migration_kwargs,
    custom_skill_rollback_kwargs,
    inspection_template_deleted_response_kwargs,
    inspection_template_list_response_kwargs,
    inspection_template_save_payload,
    inspection_template_saved_response_kwargs,
    session_group_response_kwargs,
    session_group_update_kwargs,
    session_heartbeat_update_kwargs,
    session_poll_response_kwargs,
    session_permission_update_kwargs,
    session_profile_generate_kwargs,
    session_profile_generated_response_kwargs,
    session_profile_response_kwargs,
    session_webhook_delivery_kwargs,
    tool_approval_response_kwargs,
    protocol_verification_overview_response_kwargs,
)
from api.schemas import (
    ChatRequest,
    CreateSkillRequest,
    HeartbeatUpdateRequest,
    InspectionTemplatePayload,
    MigrateRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
    SessionProfileGenerateRequest,
    SessionWebhookSendRequest,
    SkillRollbackRequest,
)


class TestApiMappers(unittest.TestCase):
    def test_chat_stream_agent_kwargs_preserves_request_fields(self):
        req = ChatRequest(
            session_id="sid-1",
            message="查一下磁盘",
            display_message="/inspect disk",
            model_name="ops-model",
            thinking_mode="high",
            attachments=[{"kind": "text", "filename": "note.txt", "text": "context"}],
        )

        self.assertEqual(
            chat_stream_agent_kwargs(req),
            {
                "session_id": "sid-1",
                "user_message": "查一下磁盘",
                "user_display_message": "/inspect disk",
                "model_name": "ops-model",
                "thinking_mode": "high",
                "user_attachments": req.attachments,
            },
        )

    def test_chat_stream_agent_kwargs_defaults_blank_thinking_mode_to_off(self):
        req = ChatRequest(session_id="sid-1", message="hello", thinking_mode="")

        self.assertEqual(chat_stream_agent_kwargs(req)["thinking_mode"], "off")

    def test_session_webhook_delivery_kwargs_preserves_all_request_fields(self):
        req = SessionWebhookSendRequest(
            webhook_url="https://ops.example.com/hook",
            payload_type="summary",
            channel="wechat",
            title="日报",
            model_name="ops-model",
            allow_private_targets=True,
        )

        self.assertEqual(
            session_webhook_delivery_kwargs(req),
            {
                "webhook_url": "https://ops.example.com/hook",
                "payload_type": "summary",
                "channel": "wechat",
                "title": "日报",
                "model_name": "ops-model",
                "allow_private_targets": True,
            },
        )

    def test_session_runtime_update_kwargs_preserve_request_fields(self):
        self.assertEqual(
            session_permission_update_kwargs(
                PermissionUpdateRequest(allow_modifications=True)
            ),
            {"allow_modifications": True},
        )
        self.assertEqual(
            session_heartbeat_update_kwargs(
                HeartbeatUpdateRequest(heartbeat_enabled=True, master_interval=180)
            ),
            {"heartbeat_enabled": True, "master_interval": 180},
        )
        self.assertEqual(
            session_heartbeat_update_kwargs(HeartbeatUpdateRequest(heartbeat_enabled=False)),
            {"heartbeat_enabled": False, "master_interval": None},
        )
        self.assertEqual(
            session_group_update_kwargs(SessionGroupUpdateRequest(group_name="数据库核心组")),
            {"group_name": "数据库核心组"},
        )

    def test_custom_skill_create_kwargs_preserves_all_request_fields(self):
        req = CreateSkillRequest(
            skill_id="disk-check",
            description="磁盘检查",
            instructions="执行磁盘巡检",
            script_name="check_disk.py",
            script_content="print('ok')",
            overwrite_existing=True,
        )

        self.assertEqual(
            custom_skill_create_kwargs(req),
            {
                "skill_id": "disk-check",
                "description": "磁盘检查",
                "instructions": "执行磁盘巡检",
                "script_name": "check_disk.py",
                "script_content": "print('ok')",
                "overwrite_existing": True,
            },
        )

    def test_custom_skill_create_kwargs_preserves_optional_empty_script_fields(self):
        req = CreateSkillRequest(
            skill_id="disk-check",
            description="磁盘检查",
            instructions="执行磁盘巡检",
        )

        self.assertEqual(
            custom_skill_create_kwargs(req),
            {
                "skill_id": "disk-check",
                "description": "磁盘检查",
                "instructions": "执行磁盘巡检",
                "script_name": None,
                "script_content": None,
                "overwrite_existing": False,
            },
        )

    def test_custom_skill_rollback_kwargs_preserves_defaults_and_approval(self):
        self.assertEqual(
            custom_skill_rollback_kwargs(SkillRollbackRequest(version_id="v1")),
            {
                "file_name": "SKILL.md",
                "version_id": "v1",
                "approval_id": None,
            },
        )
        self.assertEqual(
            custom_skill_rollback_kwargs(
                SkillRollbackRequest(
                    file_name="scripts/check.py",
                    version_id="v2",
                    approval_id="approval-1",
                )
            ),
            {
                "file_name": "scripts/check.py",
                "version_id": "v2",
                "approval_id": "approval-1",
            },
        )

    def test_custom_skill_migration_kwargs_preserves_request_fields(self):
        req = MigrateRequest(
            source_path="D:/imports/skill",
            target_dir_name="database-health",
        )

        self.assertEqual(
            custom_skill_migration_kwargs(req),
            {
                "source_path": "D:/imports/skill",
                "target_dir_name": "database-health",
            },
        )

    def test_inspection_template_save_payload_preserves_schema_dump(self):
        req = InspectionTemplatePayload(
            id="linux-basic-custom",
            name="Linux Basic Custom",
            asset_type="linux",
            protocol="ssh",
            enabled=True,
            steps=[
                {
                    "name": "uptime",
                    "title": "Uptime",
                    "tool": "linux_execute_command",
                    "command": "uptime",
                }
            ],
        )

        payload = inspection_template_save_payload(req)

        self.assertEqual(payload["id"], "linux-basic-custom")
        self.assertEqual(payload["name"], "Linux Basic Custom")
        self.assertEqual(payload["asset_type"], "linux")
        self.assertEqual(payload["protocol"], "ssh")
        self.assertTrue(payload["enabled"])
        self.assertEqual(payload["steps"][0]["name"], "uptime")
        self.assertEqual(payload["steps"][0]["tool"], "linux_execute_command")
        self.assertEqual(payload["steps"][0]["command"], "uptime")
        self.assertEqual(payload["steps"][0]["method"], "GET")
        self.assertEqual(payload["steps"][0]["timeout"], 15)

    def test_inspection_template_response_kwargs_preserve_route_shapes(self):
        templates = [{"id": "builtin-linux"}]
        template = {"id": "linux-basic-custom"}

        self.assertEqual(
            inspection_template_list_response_kwargs(templates),
            {"status": "success", "data": {"templates": templates}},
        )
        self.assertEqual(
            inspection_template_saved_response_kwargs(template, "巡检模板已保存"),
            {
                "status": "success",
                "message": "巡检模板已保存",
                "data": {"template": template},
            },
        )
        self.assertEqual(
            inspection_template_deleted_response_kwargs(),
            {"status": "success", "message": "巡检模板已删除"},
        )

    def test_session_profile_kwargs_preserve_route_shapes(self):
        req = SessionProfileGenerateRequest(
            model_name="ops-model",
            include_inspection=False,
        )
        profile = {"session_id": "sid-1", "risk_level": "watch"}

        self.assertEqual(
            session_profile_generate_kwargs(req),
            {"model_name": "ops-model", "include_inspection": False},
        )
        self.assertEqual(
            session_profile_response_kwargs(profile),
            {"status": "success", "data": {"profile": profile}},
        )
        self.assertEqual(
            session_profile_generated_response_kwargs(profile),
            {
                "status": "success",
                "message": "资产画像已生成",
                "data": {"profile": profile},
            },
        )

    def test_asset_verification_response_kwargs_preserve_route_shapes(self):
        overview = {"summary": {"asset_total": 2}, "matrix": []}
        matrix = {"asset": {"id": 2}, "steps": []}
        run = {"id": "run-1", "status": "success"}
        runs = [run]

        self.assertEqual(
            protocol_verification_overview_response_kwargs(overview),
            {"status": "success", "data": overview},
        )
        self.assertEqual(
            asset_verification_matrix_response_kwargs(matrix),
            {"status": "success", "data": {"matrix": matrix}},
        )
        self.assertEqual(
            asset_verification_run_response_kwargs(run),
            {"status": "success", "data": {"run": run}},
        )
        self.assertEqual(
            asset_verification_runs_response_kwargs(runs),
            {"status": "success", "data": {"runs": runs}},
        )

    def test_session_poll_response_kwargs_normalizes_empty_messages(self):
        self.assertEqual(
            session_poll_response_kwargs([]),
            {"status": "success", "data": {"messages": []}},
        )
        self.assertEqual(
            session_poll_response_kwargs(None),
            {"status": "success", "data": {"messages": []}},
        )

    def test_session_poll_response_kwargs_preserves_pending_messages(self):
        messages = [{"role": "assistant", "content": "ok"}]

        self.assertEqual(
            session_poll_response_kwargs(messages),
            {"status": "success", "data": {"messages": messages}},
        )

    def test_session_group_response_kwargs_preserves_route_payload_shape(self):
        self.assertEqual(
            session_group_response_kwargs(
                "sid-1",
                {"tags": ["数据库核心组", "P0"]},
                "数据库核心组",
            ),
            {
                "status": "success",
                "message": "会话分组已更新",
                "data": {
                    "session_id": "sid-1",
                    "tags": ["数据库核心组", "P0"],
                    "group_name": "数据库核心组",
                },
            },
        )

    def test_tool_approval_response_kwargs_omits_data_for_pending_future(self):
        self.assertEqual(
            tool_approval_response_kwargs(
                {
                    "message": "Approval action submitted.",
                    "approval": None,
                    "include_approval": False,
                }
            ),
            {"status": "success", "message": "Approval action submitted."},
        )

    def test_tool_approval_response_kwargs_includes_orphaned_approval_record(self):
        approval = {"id": "call-1", "status": "approved"}

        self.assertEqual(
            tool_approval_response_kwargs(
                {
                    "message": "Approval action recorded.",
                    "approval": approval,
                    "include_approval": True,
                }
            ),
            {
                "status": "success",
                "message": "Approval action recorded.",
                "data": {"approval": approval},
            },
        )


if __name__ == "__main__":
    unittest.main()
