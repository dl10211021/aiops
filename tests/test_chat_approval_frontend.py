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

    assert "AUTO_APPROVE_CONFIRMATION_TEXT = '全部批准'" in confirmation
    assert "value.trim() === AUTO_APPROVE_CONFIRMATION_TEXT" in confirmation
    assert "!isAutoApproveConfirmationValid(decision.confirmation)" in modal
    assert "!isAutoApproveConfirmationValid(confirmation)" in hook
    assert "确认全部批准" in parts
    assert "请输入“{AUTO_APPROVE_CONFIRMATION_TEXT}”" in parts
