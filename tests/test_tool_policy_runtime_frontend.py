from pathlib import Path


def test_tool_policy_runtime_summary_exposes_operational_context():
    source = Path(
        "frontend/src/features/sessions/ToolPolicyRuntimeSummary.tsx"
    ).read_text(encoding="utf-8")

    assert "强审批" in source
    assert "受控执行" in source
    assert "只读安全" in source
    assert "只读限制" in source
    assert "读写已开启" in source
    assert "requiresWriteGate(operation, approval)" in source
    assert "调度边界" in source
    assert "超时与重试" in source
    assert "不会被自动并发放大风险" in source
    assert "模式：{operation}" in source
    assert "门禁：{approval}" in source
    assert "证据：{evidence}" in source
    assert "operationToneClass(operationMode)" in source
    assert "sessionModePolicyToneClass(" in source
    assert "sessionModeSource" in source
    assert "evidenceToneClass(evidenceFamily)" in source


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
    assert "sessionModePolicyToneClass(" in source
    assert "sessionModeSource" in source
    assert "sqlActionFromTrace(item)" in source
    assert "本次 SQL 的实际动作类型" in source
    assert "evidenceToneClass(evidenceFamily)" in source
    assert "模式：{operation}" in thinking_panel
    assert "门禁：{approvalText}" in thinking_panel
    assert "证据：{evidence}" in thinking_panel
    assert "operationMode ? operationLabel(operationMode) : ''" in thinking_panel
    assert "evidenceFamily ? evidenceLabel(evidenceFamily) : ''" in thinking_panel
    assert "approval ? sessionModePolicyLabel(operationMode, approval, sessionMode) : ''" in thinking_panel
    assert "sessionModePolicyToneClass(" in thinking_panel
    assert "traceSource" in thinking_panel
    assert "sqlActionFromTrace(trace)" in thinking_panel
    assert "sqlActionFromTrace(trace)?.searchText" in thinking_panel
    assert "read_write: '可读写'" in presentation
    assert "guarded_write: '写入需审批'" in presentation
    assert "guarded_write: 'border-amber-400/40" in presentation
    assert "SQL：只读查询" in presentation
    assert "SQL：写入/DDL" in presentation
    assert "const parsedSqlAction = recordValue(parsed, 'sql_action')" in presentation
    assert "trace.tool !== 'db_execute_query'" in presentation


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
    assert "requiresWriteGate" in presentation
    assert "sessionMode === 'readonly' && requiresWriteGate" in presentation
    assert "return '只读限制'" in presentation
    assert "return '读写通过'" in presentation
    assert "border-ops-alert/45 bg-ops-alert/10 text-ops-alert" in presentation


def test_memory_candidate_source_navigation_can_focus_history_messages():
    knowledge = Path("frontend/src/components/views/KnowledgeBase.tsx").read_text(encoding="utf-8")
    knowledge_parts = Path("frontend/src/components/views/KnowledgeBaseParts.tsx").read_text(encoding="utf-8")
    message_list = Path("frontend/src/components/chat/ChatMessageList.tsx").read_text(encoding="utf-8")

    assert "handleFocusCandidateMessage" in knowledge
    assert "setCurrentSession(item.source_session_id)" in knowledge
    assert "opscore:scroll-chat-message" in knowledge
    assert "定位消息" in knowledge_parts
    assert "onFocusMessage(item)" in knowledge_parts
    assert "function messageMatchesFocus" in message_list
    assert "data-message-ids={messageDomIds(msg).join('|')}" in message_list
    assert "`mem-${message.memoryId}`" in message_list


def test_memory_candidate_evidence_dialog_reuses_session_exec_trace():
    knowledge = Path("frontend/src/components/views/KnowledgeBase.tsx").read_text(encoding="utf-8")
    knowledge_parts = Path("frontend/src/components/views/KnowledgeBaseParts.tsx").read_text(encoding="utf-8")
    session_api = Path("frontend/src/api/sessionHistory.ts").read_text(encoding="utf-8")

    assert "MemoryCandidateEvidenceDialog" in knowledge
    assert "handleOpenCandidateEvidence" in knowledge
    assert "findCandidateEvidenceTrace" in knowledge
    assert "getSessionHistoryEvidenceTrace(sourceSessionId, candidateEvidenceQuery(ref))" in knowledge
    assert "getSessionHistory(sourceSessionId, 200)" in knowledge
    assert "normalizeHistoryMessages(sourceSessionId" in knowledge
    assert "setSessionMessages(sourceSessionId, messages)" in knowledge
    assert "/history/evidence?" in session_api
    assert "onOpenEvidence={(item, ref) => void handleOpenCandidateEvidence(item, ref)}" in knowledge
    assert "onOpenEvidence(item, ref)" in knowledge_parts
    assert "ToolTraceList items={[trace]}" in knowledge_parts
    assert "工具证据详情" in knowledge_parts


def test_memory_candidate_evidence_refs_show_actual_actions():
    knowledge_parts = Path("frontend/src/components/views/KnowledgeBaseParts.tsx").read_text(encoding="utf-8")
    types = Path("frontend/src/types/index.ts").read_text(encoding="utf-8")

    assert "sql_action?: string" in types
    assert "http_action?: string" in types
    assert "command_action?: string" in types
    assert "action_label?: string" in types
    assert "function candidateEvidenceActionText(ref: MemoryCandidateRef)" in knowledge_parts
    assert "ref.command_action || ref.sql_action || ref.http_action || ref.action_label" in knowledge_parts
    assert "candidateEvidenceActionText(ref) ? ` · ${candidateEvidenceActionText(ref)}` : ''" in knowledge_parts
    assert '<CandidateEvidenceInfoLine label="实际动作" value={candidateEvidenceActionText(detail.ref) || \'-\'} />' in knowledge_parts
    assert '<CandidateEvidenceInfoLine label="证据类型" value={detail.ref.evidence_family || \'-\'} />' in knowledge_parts


def test_memory_candidates_panel_splits_runbook_and_skill_candidates():
    knowledge_data = Path("frontend/src/components/views/useKnowledgeBaseData.ts").read_text(encoding="utf-8")
    knowledge_api = Path("frontend/src/api/knowledge.ts").read_text(encoding="utf-8")
    knowledge_parts = Path("frontend/src/components/views/KnowledgeBaseParts.tsx").read_text(encoding="utf-8")

    assert "listMemoryCandidates(80, ['pending', 'runbook_candidate', 'skill_candidate']" in knowledge_data
    assert "listMemoryLearningCandidates(80, '', { signal })" in knowledge_data
    assert "updateMemoryLearningCandidateStatus(item.id, status, reason)" in knowledge_data
    assert "updateMemoryLearningCandidateQualityChecklist(item.id, checklist, reason)" in knowledge_data
    assert "statuses.join(',')" in knowledge_api
    assert "/knowledge/memory/learning-candidates?" in knowledge_api
    assert "/status" in knowledge_api
    assert "/quality-checklist" in knowledge_api
    assert "待确认候选" in knowledge_parts
    assert "Runbook 候选" in knowledge_parts
    assert "Skill 候选" in knowledge_parts
    assert "发布候选池" in knowledge_parts
    assert "learningCandidates.slice(0, 8).map" in knowledge_parts
    assert "learningCandidateStatusActions" in knowledge_parts
    assert "learningCandidateQualityReady" in knowledge_parts
    assert "learningCandidateActionBlocked" in knowledge_parts
    assert "需先补齐并保存发布前质量清单" in knowledge_parts
    assert "需补齐清单" in knowledge_parts
    assert "最近状态" in knowledge_parts
    assert "onUpdateLearningStatus(item, action.status, action.reason)" in knowledge_parts
    assert "LearningCandidateDetailDrawer" in knowledge_parts
    assert "发布候选详情" in knowledge_parts
    assert "发布前质量清单" in knowledge_parts
    assert "learningCandidateChecklist" in knowledge_parts
    assert "保存质量清单" in knowledge_parts
    assert "onUpdateLearningQuality" in knowledge_parts
    assert "quality_events" in Path("frontend/src/types/index.ts").read_text(encoding="utf-8")
    assert "查看详情" in knowledge_parts
    assert "item.review_status === 'runbook_candidate'" in knowledge_parts
    assert "item.review_status === 'skill_candidate'" in knowledge_parts
    assert "const actionable = (item.review_status || 'pending') === 'pending'" in knowledge_parts


def test_empty_tool_policy_is_not_rendered_as_unknown_chips():
    presentation = Path(
        "frontend/src/features/sessions/toolPolicyPresentation.ts"
    ).read_text(encoding="utf-8")

    assert "meaningfulToolPolicy(objectRecord(result?.tool_policy))" in presentation
    assert "meaningfulToolPolicy(metaPolicy)" in presentation
    assert "meaningfulToolPolicy(evidencePolicy)" in presentation
    assert "['operation_mode', 'approval_policy', 'evidence_family']" in presentation


def test_runtime_execution_labels_show_actual_timeout_and_failure_state():
    presentation = Path(
        "frontend/src/features/sessions/toolPolicyPresentation.ts"
    ).read_text(encoding="utf-8")

    assert "function runtimeExecutionFromTrace(trace: ExecTraceItem)" in presentation
    assert "kind: 'runtime_execution'" in presentation
    assert "kind: 'runtime_policy'" in presentation
    assert "const evidenceMeta = objectRecord(trace.evidence?.result_meta)" in presentation
    assert "objectRecord(evidenceMeta?.runtime_execution)" in presentation
    assert "const finalStatus = recordValue(execution, 'final_status')" in presentation
    assert "const errorType = recordValue(execution, 'error_type')" in presentation
    assert "实际超时 ${secondsText(timeoutSeconds)}" in presentation
    assert "实际执行失败" in presentation
    assert "if (kind === 'runtime_execution' && !retried) return labels" in presentation
    assert "labels.push(`实际重试 ${Math.round(attempts)}${totalText} 次`)" in presentation


def test_thinking_chain_search_includes_runtime_execution_labels():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "...runtimeExecutionLabels(trace)" in source
    assert "toolPolicySearchText(toolPolicyFromTrace(trace))" in source


def test_frontend_shows_actual_http_action_separately_from_tool_policy():
    presentation = Path(
        "frontend/src/features/sessions/toolPolicyPresentation.ts"
    ).read_text(encoding="utf-8")
    trace_list = Path("frontend/src/features/sessions/ToolTraceList.tsx").read_text(
        encoding="utf-8"
    )
    thinking_panel = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "export function httpActionFromTrace(trace: ExecTraceItem)" in presentation
    assert "HTTP/API：只读请求" in presentation
    assert "HTTP/API：写入/变更" in presentation
    assert "const parsedHttpAction = recordValue(parsed, 'http_action')" in presentation
    assert "http readonly read" in presentation
    assert "http write change" in presentation
    assert "const httpAction = httpActionFromTrace(item)" in trace_list
    assert "{httpAction && (" in trace_list
    assert "const httpAction = httpActionFromTrace(trace)" in thinking_panel
    assert "httpAction?.searchText" in thinking_panel


def test_frontend_shows_actual_command_action_separately_from_tool_policy():
    presentation = Path(
        "frontend/src/features/sessions/toolPolicyPresentation.ts"
    ).read_text(encoding="utf-8")
    trace_list = Path("frontend/src/features/sessions/ToolTraceList.tsx").read_text(
        encoding="utf-8"
    )
    thinking_panel = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "export function commandActionFromTrace(trace: ExecTraceItem)" in presentation
    assert "label: `命令：${label} (${actionId})`" in presentation
    assert "'linux.service.change': '变更服务状态'" in presentation
    assert "command write change ${actionId}" in presentation
    assert "command read readonly ${actionId}" in presentation
    assert "const commandAction = commandActionFromTrace(item)" in trace_list
    assert "{commandAction && (" in trace_list
    assert "const commandAction = commandActionFromTrace(trace)" in thinking_panel
    assert "commandAction?.searchText" in thinking_panel


def test_approval_row_shows_requested_action_separately_from_policy():
    approval_row = Path("frontend/src/components/views/ApprovalRow.tsx").read_text(encoding="utf-8")
    types = Path("frontend/src/types/index.ts").read_text(encoding="utf-8")

    assert "requested_action?:" in types
    assert "const requestedAction = approval.metadata?.requested_action" in approval_row
    assert "实际动作：{requestedAction.label}" in approval_row
    assert "title={requestedAction.kind || 'requested_action'}" in approval_row
