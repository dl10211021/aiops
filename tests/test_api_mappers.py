import unittest
from types import SimpleNamespace

from api.mappers import (
    agent_runtime_config_response_kwargs,
    agent_runtime_config_saved_response_kwargs,
    active_sessions_response_kwargs,
    all_sessions_poll_response_kwargs,
    approval_decision_response_kwargs,
    approval_execution_response_kwargs,
    approval_request_response_kwargs,
    approval_requests_response_kwargs,
    alert_event_list_query_kwargs,
    alert_event_response_kwargs,
    alert_event_update_kwargs,
    alert_events_response_kwargs,
    alert_webhook_response_kwargs,
    asset_deleted_response_kwargs,
    asset_normalization_applied_response_kwargs,
    asset_normalization_preview_response_kwargs,
    asset_payload,
    asset_response_kwargs,
    asset_saved_response_kwargs,
    asset_types_response_kwargs,
    asset_updated_response_kwargs,
    asset_verification_matrix_response_kwargs,
    asset_verification_run_response_kwargs,
    asset_verification_runs_response_kwargs,
    batch_asset_import_payload,
    batch_asset_import_response_kwargs,
    chat_stream_agent_kwargs,
    cron_job_created_response_kwargs,
    cron_job_deleted_response_kwargs,
    cron_job_payload,
    cron_job_response_kwargs,
    cron_job_run_trigger_response_kwargs,
    cron_jobs_response_kwargs,
    custom_slash_command_deleted_response_kwargs,
    custom_slash_command_saved_response_kwargs,
    custom_slash_command_updated_response_kwargs,
    custom_slash_commands_response_kwargs,
    custom_skill_create_kwargs,
    custom_skill_migration_kwargs,
    custom_skill_rollback_kwargs,
    chat_attachment_preview_response_kwargs,
    chat_stop_response_kwargs,
    dashboard_response_kwargs,
    embedding_config_saved_response_kwargs,
    inspection_run_export_response_kwargs,
    inspection_run_report_response_kwargs,
    inspection_run_response_kwargs,
    inspection_run_summary_response_kwargs,
    inspection_runs_response_kwargs,
    inspection_template_deleted_response_kwargs,
    inspection_template_list_response_kwargs,
    inspection_template_save_payload,
    inspection_template_saved_response_kwargs,
    knowledge_document_deleted_response_kwargs,
    knowledge_document_uploaded_response_kwargs,
    knowledge_documents_response_kwargs,
    memory_item_deleted_response_kwargs,
    memory_export_response_kwargs,
    memory_item_response_kwargs,
    memory_item_restored_response_kwargs,
    memory_item_updated_response_kwargs,
    memory_items_response_kwargs,
    memory_stores_response_kwargs,
    memory_versions_response_kwargs,
    legacy_command_response_kwargs,
    llm_config_response_kwargs,
    models_response_kwargs,
    notification_channel_test_response_kwargs,
    notification_config_response_kwargs,
    notification_config_saved_response_kwargs,
    providers_response_kwargs,
    providers_saved_response_kwargs,
    protocol_verification_overview_response_kwargs,
    safety_policy_response_kwargs,
    safety_policy_saved_response_kwargs,
    safety_policy_test_response_kwargs,
    saved_assets_response_kwargs,
    session_group_response_kwargs,
    session_group_update_kwargs,
    session_closed_response_kwargs,
    session_commands_response_kwargs,
    session_heartbeat_update_kwargs,
    session_heartbeat_updated_response_kwargs,
    session_history_cleared_response_kwargs,
    session_history_export_response_kwargs,
    session_history_message_deleted_response_kwargs,
    session_history_message_feedback_response_kwargs,
    session_history_message_updated_response_kwargs,
    session_history_response_kwargs,
    session_poll_response_kwargs,
    session_permission_update_kwargs,
    session_permission_updated_response_kwargs,
    session_profile_generate_kwargs,
    session_profile_generated_response_kwargs,
    session_profile_response_kwargs,
    session_skills_updated_response_kwargs,
    session_webhook_history_response_kwargs,
    session_webhook_preview_response_kwargs,
    session_webhook_delivery_kwargs,
    session_webhook_sent_response_kwargs,
    skill_created_response_kwargs,
    skill_detail_response_kwargs,
    skill_migration_response_kwargs,
    skill_registry_response_kwargs,
    skill_rollback_response_kwargs,
    skill_scan_response_kwargs,
    skill_validation_response_kwargs,
    skill_versions_response_kwargs,
    system_info_response_kwargs,
    tool_catalog_response_kwargs,
    tool_approval_response_kwargs,
    user_interaction_submitted_response_kwargs,
)
from api.schemas import (
    AlertEventUpdateRequest,
    AssetPayload,
    BatchAssetImportItem,
    ChatRequest,
    CreateSkillRequest,
    CronAddRequest,
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
                "orchestration_mode": "single",
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

    def test_cron_job_payload_preserves_request_fields(self):
        req = CronAddRequest(
            cron_expr="*/15 * * * *",
            message="inspect database group",
            host="10.0.0.8",
            username="ops",
            agent_profile="deep",
            password="secret",
            asset_id=7,
            target_scope="tag",
            scope_value="prod-db",
            template_id="mysql-basic",
            notification_channel="wechat",
            retry_count=2,
            active_skills=["mysql-health", "disk-check"],
        )

        self.assertEqual(
            cron_job_payload(req),
            {
                "cron_expr": "*/15 * * * *",
                "message": "inspect database group",
                "host": "10.0.0.8",
                "username": "ops",
                "agent_profile": "deep",
                "password": "secret",
                "private_key_path": None,
                "asset_id": 7,
                "target_scope": "tag",
                "scope_value": "prod-db",
                "template_id": "mysql-basic",
                "notification_channel": "wechat",
                "retry_count": 2,
                "active_skills": ["mysql-health", "disk-check"],
            },
        )

    def test_cron_job_response_kwargs_preserve_route_shapes(self):
        job = {"job_id": "job-1", "status": "active"}
        jobs = [job]
        run = {"id": "run-1", "status": "completed"}
        report = {"run_id": "run-1", "summary": {"target_count": 1}}
        export_payload = {
            "format": "markdown",
            "content_type": "text/markdown",
            "content": "# 巡检报告",
        }
        summary = {"total_runs": 1, "success_rate": 100.0}
        result = {"job_id": "job-1", "status": "completed"}

        self.assertEqual(
            cron_job_created_response_kwargs(job),
            {
                "status": "success",
                "message": "已成功添加定时巡检计划: job-1",
                "data": job,
            },
        )
        self.assertEqual(
            cron_jobs_response_kwargs(jobs),
            {"status": "success", "data": {"jobs": jobs}},
        )
        self.assertEqual(
            cron_job_deleted_response_kwargs("job-1"),
            {"status": "success", "message": "巡检计划 job-1 已取消。"},
        )
        self.assertEqual(
            cron_job_response_kwargs(job, "巡检计划已更新"),
            {
                "status": "success",
                "message": "巡检计划已更新",
                "data": {"job": job},
            },
        )
        self.assertEqual(
            cron_job_run_trigger_response_kwargs(result),
            {
                "status": "success",
                "message": "巡检计划已手动触发",
                "data": {"result": result},
            },
        )
        self.assertEqual(
            inspection_runs_response_kwargs([run]),
            {"status": "success", "data": {"runs": [run]}},
        )
        self.assertEqual(
            inspection_run_summary_response_kwargs(summary),
            {"status": "success", "data": {"summary": summary}},
        )
        self.assertEqual(
            inspection_run_response_kwargs(run),
            {"status": "success", "data": {"run": run}},
        )
        self.assertEqual(
            inspection_run_report_response_kwargs(report),
            {"status": "success", "data": {"report": report}},
        )
        self.assertEqual(
            inspection_run_export_response_kwargs(export_payload),
            {"status": "success", "data": export_payload},
        )

    def test_dashboard_response_kwargs_preserves_payload(self):
        payload = {"summary": {"asset_total": 2}, "alerts": {"open": 1}}

        self.assertEqual(
            dashboard_response_kwargs(payload),
            {"status": "success", "data": payload},
        )

    def test_asset_payload_preserves_request_fields(self):
        req = AssetPayload(
            remark="Prometheus",
            host="prom.local",
            port=9090,
            username="api",
            password="secret",
            asset_type="prometheus",
            protocol="http_api",
            agent_profile="default",
            extra_args={"api_token": "token", "category": "monitor"},
            skills=["prometheus"],
            tags=["monitor"],
        )

        self.assertEqual(
            asset_payload(req),
            {
                "remark": "Prometheus",
                "host": "prom.local",
                "port": 9090,
                "username": "api",
                "password": "secret",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "agent_profile": "default",
                "extra_args": {"api_token": "token", "category": "monitor"},
                "skills": ["prometheus"],
                "tags": ["monitor"],
            },
        )

    def test_batch_asset_import_payload_preserves_request_fields(self):
        item = BatchAssetImportItem(
            remark="Linux",
            host="10.0.0.10",
            username="root",
            password="secret",
            tags=["prod"],
        )

        self.assertEqual(
            batch_asset_import_payload([item]),
            [
                {
                    "remark": "Linux",
                    "host": "10.0.0.10",
                    "port": 22,
                    "username": "root",
                    "password": "secret",
                    "asset_type": "ssh",
                    "protocol": None,
                    "agent_profile": "default",
                    "extra_args": {},
                    "skills": [],
                    "tags": ["prod"],
                }
            ],
        )

    def test_asset_response_kwargs_preserve_route_shapes(self):
        asset = {"id": 1, "host": "prom.local", "password": "********"}
        assets = [asset]
        asset_types = {"types": [{"id": "linux"}], "categories": []}

        self.assertEqual(
            saved_assets_response_kwargs(assets),
            {"status": "success", "data": {"assets": assets}},
        )
        self.assertEqual(
            asset_saved_response_kwargs(),
            {"status": "success", "message": "资产已保存"},
        )
        self.assertEqual(
            asset_types_response_kwargs(asset_types),
            {"status": "success", "data": asset_types},
        )
        self.assertEqual(
            asset_response_kwargs(asset),
            {"status": "success", "data": {"asset": asset}},
        )
        self.assertEqual(
            asset_updated_response_kwargs(asset),
            {
                "status": "success",
                "message": "资产已更新",
                "data": {"asset": asset},
            },
        )
        self.assertEqual(
            asset_deleted_response_kwargs(),
            {"status": "success", "message": "资产已成功移除金库。"},
        )
        self.assertEqual(
            batch_asset_import_response_kwargs({"imported": 2, "total": 3}),
            {"status": "success", "message": "成功导入 2/3 条资产。"},
        )

    def test_asset_normalization_response_kwargs_preserve_route_shapes(self):
        plan = {
            "changes": [],
            "duplicates": [],
            "summary": {"assets_scanned": 2},
        }
        report = {
            "backup_path": "asset_cleanup_backup.json",
            "removed_ids": [1],
            "summary": {"duplicates_removed": 1},
        }

        self.assertEqual(
            asset_normalization_preview_response_kwargs(plan),
            {"status": "success", "data": plan},
        )
        self.assertEqual(
            asset_normalization_applied_response_kwargs(report),
            {
                "status": "success",
                "message": "资产规范化清理完成",
                "data": report,
            },
        )

    def test_system_info_response_kwargs_preserves_payload(self):
        payload = {"detected": True, "lib_dir": "D:/oracle/instantclient"}

        self.assertEqual(
            system_info_response_kwargs(payload),
            {"status": "success", "data": payload},
        )

    def test_notification_response_kwargs_preserve_route_shapes(self):
        config = {"wechat_enabled": True, "smtp_port": 465}

        self.assertEqual(
            notification_config_response_kwargs(config),
            {"status": "success", "data": config},
        )
        self.assertEqual(
            notification_config_saved_response_kwargs(),
            {"status": "success", "message": "告警通道配置已保存并生效"},
        )
        self.assertEqual(
            notification_channel_test_response_kwargs("发送成功"),
            {"status": "success", "message": "发送成功"},
        )

    def test_config_response_kwargs_preserve_route_shapes(self):
        models = [{"id": "openai|gpt-4o", "name": "gpt-4o"}]
        llm_config = {"base_url": "https://api.example/v1", "api_key": "********"}
        runtime_config = {"chat_max_steps": 80, "headless_max_steps": 60}
        providers = [{"id": "openai", "api_key": "********"}]
        policy = {"rules": []}
        policy_result = {"action": "deny", "reason": "blocked"}

        self.assertEqual(
            models_response_kwargs(models),
            {"status": "success", "data": {"models": models}},
        )
        self.assertEqual(
            llm_config_response_kwargs(llm_config),
            {"status": "success", "data": llm_config},
        )
        self.assertEqual(
            agent_runtime_config_response_kwargs(runtime_config),
            {"status": "success", "data": {"config": runtime_config}},
        )
        self.assertEqual(
            agent_runtime_config_saved_response_kwargs(runtime_config),
            {
                "status": "success",
                "data": {"config": runtime_config},
                "message": "Agent 执行保护配置已保存",
            },
        )
        self.assertEqual(
            embedding_config_saved_response_kwargs("text-embedding", 1024),
            {
                "status": "success",
                "message": "Embedding 配置已更新: model=text-embedding, dim=1024",
            },
        )
        self.assertEqual(
            providers_response_kwargs(providers),
            {"status": "success", "data": {"providers": providers}},
        )
        self.assertEqual(
            providers_saved_response_kwargs(),
            {"status": "success", "message": "供应商配置已保存"},
        )
        self.assertEqual(
            safety_policy_response_kwargs(policy),
            {"status": "success", "data": {"policy": policy}},
        )
        self.assertEqual(
            safety_policy_saved_response_kwargs(policy),
            {
                "status": "success",
                "message": "安全策略已保存",
                "data": {"policy": policy},
            },
        )
        self.assertEqual(
            safety_policy_test_response_kwargs(policy_result),
            {"status": "success", "data": {"result": policy_result}},
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

    def test_alert_event_kwargs_preserve_route_shapes(self):
        alert = {"id": "alert-1", "status": "open"}
        alerts = [alert]
        webhook_result = {"message": "告警已接收", "data": {"alert": alert}}

        self.assertEqual(
            alert_event_list_query_kwargs("open", "critical", "db.local", 20),
            {
                "status": "open",
                "severity": "critical",
                "host": "db.local",
                "limit": 20,
            },
        )
        self.assertEqual(
            alert_event_update_kwargs(
                AlertEventUpdateRequest(
                    status="acknowledged",
                    assignee="ops",
                    note="checking",
                )
            ),
            {
                "status": "acknowledged",
                "assignee": "ops",
                "note": "checking",
            },
        )
        self.assertEqual(
            alert_events_response_kwargs(alerts),
            {"status": "success", "data": {"alerts": alerts}},
        )
        self.assertEqual(
            alert_event_response_kwargs(alert),
            {"status": "success", "data": {"alert": alert}},
        )
        self.assertEqual(
            alert_webhook_response_kwargs(webhook_result),
            {
                "status": "success",
                "message": "告警已接收",
                "data": {"alert": alert},
            },
        )

    def test_knowledge_document_response_kwargs_preserve_route_shapes(self):
        files = ["runbook.md", "network.log"]
        memory_item = {"path": "sessions/sid-1/memory.md"}
        versions = [{"operation": "created"}]
        stores = [{"id": "sessions"}]

        self.assertEqual(
            knowledge_document_uploaded_response_kwargs("文档已注入知识库"),
            {"status": "success", "message": "文档已注入知识库"},
        )
        self.assertEqual(
            knowledge_documents_response_kwargs(files),
            {"status": "success", "data": {"files": files}},
        )
        self.assertEqual(
            knowledge_document_deleted_response_kwargs("文档已删除"),
            {"status": "success", "message": "文档已删除"},
        )
        self.assertEqual(
            memory_items_response_kwargs([memory_item]),
            {"status": "success", "data": {"items": [memory_item]}},
        )
        self.assertEqual(
            memory_item_response_kwargs(memory_item),
            {"status": "success", "data": {"item": memory_item}},
        )
        self.assertEqual(
            memory_versions_response_kwargs(versions),
            {"status": "success", "data": {"versions": versions}},
        )
        self.assertEqual(
            memory_stores_response_kwargs(stores),
            {"status": "success", "data": {"stores": stores}},
        )
        self.assertEqual(
            memory_item_updated_response_kwargs(memory_item),
            {"status": "success", "message": "记忆已更新", "data": {"item": memory_item}},
        )
        self.assertEqual(
            memory_item_restored_response_kwargs({"version_id": "v1"}),
            {"status": "success", "message": "记忆版本已恢复", "data": {"version": {"version_id": "v1"}}},
        )
        self.assertEqual(
            memory_export_response_kwargs({"stores": stores}),
            {"status": "success", "data": {"export": {"stores": stores}}},
        )
        self.assertEqual(
            memory_item_deleted_response_kwargs("sessions/sid-1/memory.md"),
            {"status": "success", "message": "记忆已删除: sessions/sid-1/memory.md"},
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

    def test_session_runtime_response_kwargs_preserve_route_shapes(self):
        updates = {"sid-1": [{"role": "assistant", "content": "ok"}]}
        messages = [{"id": 1, "role": "user", "content": "hello"}]
        message = {"id": 1, "role": "user", "content": "updated"}
        sessions = {"sid-1": {"host": "10.0.0.10"}}
        catalog = {"toolsets": []}

        self.assertEqual(
            session_permission_updated_response_kwargs(),
            {"status": "success", "message": "权限已实时更新"},
        )
        self.assertEqual(
            session_heartbeat_updated_response_kwargs(),
            {"status": "success", "message": "心跳巡检状态已更新"},
        )
        self.assertEqual(
            all_sessions_poll_response_kwargs(updates),
            {"status": "success", "data": {"updates": updates}},
        )
        self.assertEqual(
            session_history_response_kwargs(messages),
            {"status": "success", "data": {"messages": messages}},
        )
        self.assertEqual(
            session_history_cleared_response_kwargs(),
            {"status": "success", "message": "会话记录已清空"},
        )
        self.assertEqual(
            session_history_message_updated_response_kwargs(message),
            {
                "status": "success",
                "data": {"message": message},
                "message": "消息已更新",
            },
        )
        self.assertEqual(
            session_history_message_feedback_response_kwargs(message),
            {
                "status": "success",
                "data": {"message": message},
                "message": "反馈已记录",
            },
        )
        self.assertEqual(
            session_history_message_deleted_response_kwargs(),
            {"status": "success", "message": "消息已删除"},
        )
        self.assertEqual(
            session_skills_updated_response_kwargs(),
            {"status": "success", "message": "挂载技能已实时更新"},
        )
        self.assertEqual(
            active_sessions_response_kwargs(sessions),
            {"status": "success", "data": {"sessions": sessions}},
        )
        self.assertEqual(
            tool_catalog_response_kwargs(catalog),
            {"status": "success", "data": catalog},
        )

    def test_session_command_webhook_and_export_response_kwargs_preserve_route_shapes(self):
        command = {"id": "inspect", "label": "巡检"}
        commands = [command]
        payload = {"payload_type": "markdown"}
        deliveries = [{"id": 1, "status": "success"}]

        self.assertEqual(
            session_commands_response_kwargs({"commands": commands}),
            {"status": "success", "data": {"commands": commands}},
        )
        self.assertEqual(
            custom_slash_commands_response_kwargs(commands),
            {"status": "success", "data": {"commands": commands}},
        )
        self.assertEqual(
            custom_slash_command_saved_response_kwargs(command),
            {
                "status": "success",
                "message": "快捷命令已保存",
                "data": {"command": command},
            },
        )
        self.assertEqual(
            custom_slash_command_updated_response_kwargs(command),
            {
                "status": "success",
                "message": "快捷命令已更新",
                "data": {"command": command},
            },
        )
        self.assertEqual(
            custom_slash_command_deleted_response_kwargs(),
            {"status": "success", "message": "快捷命令已删除"},
        )
        self.assertEqual(
            session_webhook_sent_response_kwargs(payload),
            {"status": "success", "message": "Webhook 已发送", "data": payload},
        )
        self.assertEqual(
            session_webhook_preview_response_kwargs(payload),
            {"status": "success", "data": payload},
        )
        self.assertEqual(
            session_webhook_history_response_kwargs(deliveries),
            {"status": "success", "data": {"deliveries": deliveries}},
        )
        self.assertEqual(
            session_closed_response_kwargs(),
            {"status": "success", "message": "Connection closed safely"},
        )
        self.assertEqual(
            session_history_export_response_kwargs("# 会话"),
            {"status": "success", "data": {"markdown": "# 会话"}},
        )

    def test_interaction_approval_and_skill_response_kwargs_preserve_route_shapes(self):
        attachment = {"filename": "runbook.txt", "text": "hello"}
        approval = {"id": "approval-1", "status": "pending"}
        approvals = [approval]
        execution = SimpleNamespace(
            status="success",
            message="rollback complete",
            approval=approval,
            result={"version_id": "v1"},
        )
        command_result = {"stdout": "ok"}
        registry = {"registry": []}
        detail = {"skill_id": "safe-skill", "content": "---"}
        created = {"message": "技能已创建", "data": {"skill_id": "safe-skill"}}
        validation = {"valid": True, "issues": []}
        versions = [{"id": "v1"}]
        rollback = {"status": "success", "message": "已回滚", "data": {"id": "v1"}}
        migrated = {"message": "技能已导入"}

        self.assertEqual(
            chat_attachment_preview_response_kwargs(attachment),
            {"status": "success", "data": {"attachment": attachment}},
        )
        self.assertEqual(
            user_interaction_submitted_response_kwargs(),
            {"status": "success", "message": "交互输入已提交。"},
        )
        self.assertEqual(
            approval_requests_response_kwargs(approvals),
            {"status": "success", "data": {"approvals": approvals}},
        )
        self.assertEqual(
            approval_request_response_kwargs(approval),
            {"status": "success", "data": {"approval": approval}},
        )
        self.assertEqual(
            approval_decision_response_kwargs(approval),
            {"status": "success", "message": "审批已处理", "data": {"approval": approval}},
        )
        self.assertEqual(
            approval_execution_response_kwargs(execution),
            {
                "status": "success",
                "message": "rollback complete",
                "data": {"approval": approval, "result": {"version_id": "v1"}},
            },
        )
        self.assertEqual(
            chat_stop_response_kwargs(),
            {"status": "success", "message": "已发送中止信号。"},
        )
        self.assertEqual(
            legacy_command_response_kwargs(command_result),
            {"status": "success", "data": command_result},
        )
        self.assertEqual(
            skill_scan_response_kwargs({"message": "扫描完成"}),
            {"status": "success", "message": "扫描完成"},
        )
        self.assertEqual(
            skill_registry_response_kwargs(registry),
            {"status": "success", "data": registry},
        )
        self.assertEqual(
            skill_detail_response_kwargs(detail),
            {"status": "success", "data": detail},
        )
        self.assertEqual(
            skill_created_response_kwargs(created),
            {"status": "success", "message": "技能已创建", "data": created["data"]},
        )
        self.assertEqual(
            skill_validation_response_kwargs(validation),
            {"status": "success", "data": validation},
        )
        self.assertEqual(
            skill_versions_response_kwargs(versions),
            {"status": "success", "data": {"versions": versions}},
        )
        self.assertEqual(
            skill_rollback_response_kwargs(rollback),
            {"status": "success", "message": "已回滚", "data": {"id": "v1"}},
        )
        self.assertEqual(
            skill_migration_response_kwargs(migrated),
            {"status": "success", "message": "技能已导入"},
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
