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
    assert "AlertIntegrationPanel" in center_source
    assert "http://127.0.0.1" not in center_source
    assert "window.location.origin" in center_source
    assert "handleCopyWebhookUrl" in center_source
    assert "handleSendTestAlert" in center_source
    assert "OpsCore Webhook Test" in center_source
    assert "外部告警接入" in parts_source
    assert "复制地址" in parts_source
    assert "发送测试告警" in parts_source
    assert "Alertmanager / Grafana" in parts_source
    assert "ManageEngine / 卓豪" in parts_source
    assert "分类降噪策略" in parts_source
    assert "zabbix、prometheus、grafana" in parts_source


def test_alert_center_uses_source_type_for_display_labels():
    parts_source = Path("frontend/src/components/views/AlertCenterParts.tsx").read_text(
        encoding="utf-8"
    )
    detail_source = Path("frontend/src/components/views/AlertDetail.tsx").read_text(
        encoding="utf-8"
    )

    assert "alertSourceLabel(alert.source_family || alert.source_type || alert.source)" in parts_source
    assert "alertSourceLabel(alert.source_type || alert.source)" in detail_source


def test_alert_detail_shows_policy_and_ai_automation_fields():
    detail_source = Path("frontend/src/components/views/AlertDetail.tsx").read_text(
        encoding="utf-8"
    )
    types_source = Path("frontend/src/types/index.ts").read_text(encoding="utf-8")

    assert "平台分类" in detail_source
    assert "告警类型" in detail_source
    assert "AI 自动化策略" in detail_source
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

    assert "alertClassLabel(alert.alert_class)" in parts_source
    assert "alertNoiseActionLabel(alert.noise_action)" in parts_source
    assert "alertPriorityLabel(alert.priority)" in parts_source
    assert "alert.automation_decision?.run_ai ? '会触发 AI' : '仅入库'" in parts_source
    assert "alertClassLabel" in display_source
    assert "alertNoiseActionLabel" in display_source


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
    assert "全部策略" in parts_source
    assert "会触发 AI" in parts_source
    assert "仅入库" in parts_source
