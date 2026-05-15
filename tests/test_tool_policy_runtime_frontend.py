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
    assert "门禁：{gateLabel}" in source
    assert "证据：{evidenceLabel(evidenceFamily)}" in source
    assert "operationToneClass(operationMode)" in source
    assert "sessionModePolicyToneClass(operationMode, approvalPolicy, sessionMode)" in source
    assert "evidenceToneClass(evidenceFamily)" in source
    assert "模式：{operation}" in thinking_panel
    assert "门禁：{approvalText}" in thinking_panel
    assert "证据：{evidence}" in thinking_panel
    assert "sessionModePolicyToneClass(operationMode, approval, sessionMode)" in thinking_panel
    assert "read_write: '可读写'" in presentation
    assert "guarded_write: '写入需审批'" in presentation
    assert "guarded_write: 'border-amber-400/40" in presentation


def test_tool_policy_chips_are_session_mode_aware():
    chat_window = Path("frontend/src/components/chat/ChatWindow.tsx").read_text(encoding="utf-8")
    message_list = Path("frontend/src/components/chat/ChatMessageList.tsx").read_text(encoding="utf-8")
    message_bubble = Path("frontend/src/features/sessions/MessageBubble.tsx").read_text(encoding="utf-8")
    presentation = Path(
        "frontend/src/features/sessions/toolPolicyPresentation.ts"
    ).read_text(encoding="utf-8")

    assert "session?.isReadWriteMode ? 'readwrite' : 'readonly'" in chat_window
    assert "sessionMode={sessionMode}" in chat_window
    assert "sessionMode?: 'readonly' | 'readwrite'" in message_list
    assert "sessionMode?: 'readonly' | 'readwrite'" in message_bubble
    assert "sessionMode === 'readonly' && writeCapable" in presentation
    assert "return '只读限制'" in presentation
    assert "return '读写受控'" in presentation
    assert "border-ops-alert/45 bg-ops-alert/10 text-ops-alert" in presentation
