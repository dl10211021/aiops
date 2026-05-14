from pathlib import Path


def test_alert_center_exposes_webhook_integration_panel():
    center_source = Path("frontend/src/components/views/AlertCenter.tsx").read_text(
        encoding="utf-8"
    )
    parts_source = Path("frontend/src/components/views/AlertCenterParts.tsx").read_text(
        encoding="utf-8"
    )
    api_source = Path("frontend/src/api/alerts.ts").read_text(encoding="utf-8")

    assert "sendAlertWebhook" in api_source
    assert "'/webhook/alert'" in api_source
    assert "AlertConsoleHeader" in center_source
    assert "http://127.0.0.1" not in center_source
    assert "window.location.origin" in center_source
    assert "handleCopyWebhookUrl" in center_source
    assert "handleSendTestAlert" in center_source
    assert "OpsCore Webhook Test" in center_source
    assert "告警处理台" in parts_source
    assert "复制地址" in parts_source
    assert "发送测试告警" in parts_source
    assert "接入地址和测试" in parts_source
    assert "同一机器同类告警 30 分钟内不重复拉 AI" in parts_source
    assert "配置告警流程" in parts_source


def test_alert_center_uses_source_type_for_display_labels():
    parts_source = Path("frontend/src/components/views/AlertCenterParts.tsx").read_text(
        encoding="utf-8"
    )
    detail_source = Path("frontend/src/components/views/AlertDetail.tsx").read_text(
        encoding="utf-8"
    )

    assert "alertSourceLabel(alert.source_family || alert.source_type || alert.source)" in parts_source
    assert "alertSourceLabel(alert.source_family || alert.source_type || alert.source)" in detail_source


def test_alert_detail_shows_policy_and_ai_automation_fields():
    detail_source = Path("frontend/src/components/views/AlertDetail.tsx").read_text(
        encoding="utf-8"
    )
    types_source = Path("frontend/src/types/index.ts").read_text(encoding="utf-8")

    assert "影响对象" in detail_source
    assert "平台动作" in detail_source
    assert "AI 与会话" in detail_source
    assert "alert.automation_decision?.run_ai" in detail_source
    assert "notification_plan" in types_source
    assert "automation_decision" in types_source


def test_alert_queue_shows_classification_noise_and_ai_decision():
    parts_source = Path("frontend/src/components/views/AlertCenterParts.tsx").read_text(
        encoding="utf-8"
    )
    display_source = Path("frontend/src/components/views/alertDisplay.ts").read_text(
        encoding="utf-8"
    )

    assert "alertQueueClassLabel(alert)" in parts_source
    assert "alertNoiseActionLabel(alert.noise_action)" in parts_source
    assert "alertPriorityLabel(alert.priority)" in parts_source
    assert "alert.automation_decision?.run_ai ? 'AI 分析' : '只记录'" in parts_source
    assert "alertClassLabel" in display_source
    assert "alertNoiseActionLabel" in display_source
    assert "cooldown_forward" in display_source


def test_alert_center_can_filter_by_source_family_and_ai_policy():
    center_source = Path("frontend/src/components/views/AlertCenter.tsx").read_text(
        encoding="utf-8"
    )
    parts_source = Path("frontend/src/components/views/AlertCenterParts.tsx").read_text(
        encoding="utf-8"
    )

    assert "sourceFamily" in center_source
    assert "automationMode" in center_source
    assert "source_family: sourceFamily" in center_source
    assert "automation_mode: automationMode" in center_source
    assert "全部平台" in parts_source
    assert "全部流程" in parts_source
    assert "会走 AI" in parts_source
    assert "只记录" in parts_source


def test_alert_policy_drawer_updates_existing_rules_and_exposes_delete():
    drawer_source = Path("frontend/src/components/views/AlertPolicyDrawer.tsx").read_text(
        encoding="utf-8"
    )

    assert "ruleMatchKey" in drawer_source
    assert "已有规则已更新" in drawer_source
    assert "deleteRuleAndSave" in drawer_source
    assert "已有规则" in drawer_source
    assert "删除规则" in drawer_source
