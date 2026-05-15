from pathlib import Path


def test_auto_approve_confirmation_uses_explicit_all_approval_phrase():
    confirmation = Path(
        "frontend/src/features/sessions/approvalConfirmation.ts"
    ).read_text(encoding="utf-8")
    modal = Path(
        "frontend/src/features/sessions/ChatApprovalDecisionModal.tsx"
    ).read_text(encoding="utf-8")
    hook = Path(
        "frontend/src/features/sessions/useToolApprovalDecision.ts"
    ).read_text(encoding="utf-8")
    parts = Path(
        "frontend/src/features/sessions/ChatApprovalDecisionModalParts.tsx"
    ).read_text(encoding="utf-8")
    approval_card_parts = Path(
        "frontend/src/features/sessions/ToolApprovalCardParts.tsx"
    ).read_text(encoding="utf-8")

    assert "AUTO_APPROVE_CONFIRMATION_TEXT = '全部批准'" in confirmation
    assert "value.trim() === AUTO_APPROVE_CONFIRMATION_TEXT" in confirmation
    assert "!isAutoApproveConfirmationValid(decision.confirmation)" in modal
    assert "approvalDecisionDisabledReason(decision)" in modal
    assert "!isAutoApproveConfirmationValid(confirmation)" in hook
    assert "确认全部批准" in parts
    assert "请输入“{AUTO_APPROVE_CONFIRMATION_TEXT}”" in parts
    assert "{disabledReason}" in parts
    assert "本会话全部批准" in approval_card_parts
    assert "已全部批准，本会话后续审批将自动放行" in approval_card_parts
    assert "批准本次，并让本会话后续需要审批的工具调用自动放行" in approval_card_parts


def test_approval_argument_rows_surface_http_and_asset_context():
    rows = Path("frontend/src/features/sessions/approvalRows.ts").read_text(encoding="utf-8")

    assert "const url = parsed.url" in rows
    assert "const endpoint = parsed.endpoint" in rows
    assert "const body = parsed.body" in rows
    assert "const params = parsed.params" in rows
    assert "const headers = parsed.headers" in rows
    assert "formatApprovalArgValue(value: unknown)" in rows
    assert "asset_name: '资产'" in rows
    assert "channel: '通知渠道'" in rows
    assert "return rows.slice(0, 12)" in rows
