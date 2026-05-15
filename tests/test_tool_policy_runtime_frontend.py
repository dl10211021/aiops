from pathlib import Path


def test_tool_policy_runtime_summary_exposes_operational_context():
    source = Path(
        "frontend/src/features/sessions/ToolPolicyRuntimeSummary.tsx"
    ).read_text(encoding="utf-8")

    assert "强审批" in source
    assert "受控执行" in source
    assert "只读安全" in source
    assert "调度边界" in source
    assert "超时与重试" in source
    assert "不会被自动并发放大风险" in source


def test_tool_trace_policy_chips_separate_mode_gate_and_evidence():
    source = Path(
        "frontend/src/features/sessions/ToolTraceList.tsx"
    ).read_text(encoding="utf-8")
    thinking_panel = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")
    presentation = Path(
        "frontend/src/features/sessions/toolPolicyPresentation.ts"
    ).read_text(encoding="utf-8")

    assert "模式：{operationLabel(operationMode)}" in source
    assert "门禁：{approvalLabel(approvalPolicy)}" in source
    assert "证据：{evidenceLabel(evidenceFamily)}" in source
    assert "operationToneClass(operationMode)" in source
    assert "approvalToneClass(approvalPolicy)" in source
    assert "evidenceToneClass(evidenceFamily)" in source
    assert "模式：{operation}" in thinking_panel
    assert "门禁：{approvalText}" in thinking_panel
    assert "证据：{evidence}" in thinking_panel
    assert "approvalToneClass(approval)" in thinking_panel
    assert "read_write: '可读写'" in presentation
    assert "guarded_write: '写入需审批'" in presentation
    assert "guarded_write: 'border-amber-400/40" in presentation
