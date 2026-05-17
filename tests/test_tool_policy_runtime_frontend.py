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


def test_tool_trace_shows_multi_agent_child_session_modes():
    source = Path(
        "frontend/src/features/sessions/ToolTraceList.tsx"
    ).read_text(encoding="utf-8")

    assert "协同子任务" in source
    assert "dispatchResultItems(parsedResult)" in source
    assert "recordValue(result, 'status') !== 'BATCH_COMPLETE'" in source
    assert "parseSessionMode(item.session_mode ?? item.allow_modifications)" in source
    assert "模式：{dispatchResultModeLabel(child)}" in source
    assert "dispatchPermissionBoundaryLabel(child)" in source
    assert "dispatchPermissionBoundaryTitle(child)" in source
    assert "function dispatchPermissionBoundary(item: Record<string, unknown>)" in source
    assert "objectRecord(item.permission_boundary)" in source
    assert "return `${scope}降权`" in source
    assert "范围：${dispatchScopeLabel(recordValue(boundary, 'scope'))}" in source
    assert "dispatchItems.slice(0, 8).map" in source


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
    assert "statusesOrOptions?: LearningCandidateStatus[] | RequestInit" in knowledge_api
    assert "search.set('statuses', statusesOrOptions.join(','))" in knowledge_api
    assert "/knowledge/memory/learning-candidates?" in knowledge_api
    assert "/status" in knowledge_api
    assert "/quality-checklist" in knowledge_api
    assert "待确认候选" in knowledge_parts
    assert "Runbook 候选" in knowledge_parts
    assert "Skill 候选" in knowledge_parts
    assert "发布候选池" in knowledge_parts
    assert "filteredLearningCandidates" in knowledge_parts
    assert "visibleLearningCandidates = filteredLearningCandidates.slice(0, 20)" in knowledge_parts
    assert "LearningCandidateStatusFilter" in knowledge_parts
    assert "LearningCandidateTargetFilter" in knowledge_parts
    assert "candidateSearch" in knowledge_parts
    assert "memoryCandidateSearchText" in knowledge_parts
    assert "learningCandidateSearchText" in knowledge_parts
    assert "搜索候选 ID、摘要、会话、证据、状态" in knowledge_parts
    assert "学习候选 {filteredMemoryCandidates.length}/{items.length}" in knowledge_parts
    assert "发布候选 {filteredLearningCandidates.length}/{learningCandidates.length}" in knowledge_parts
    assert "setLearningStatusFilter" in knowledge_parts
    assert "setLearningTargetFilter" in knowledge_parts
    assert "learningCandidateStatusLabel" in knowledge_parts
    assert "learningCandidateNeedsCompletion" in knowledge_parts
    assert "当前筛选条件下暂无发布候选" in knowledge_parts
    assert "显示 {visibleLearningCandidates.length}/{filteredLearningCandidates.length}" in knowledge_parts
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
    assert "review?: {" in Path("frontend/src/types/index.ts").read_text(encoding="utf-8")
    assert "LearningCandidateReviewCard" in knowledge_parts
    assert "辅助审核" in knowledge_parts
    assert "review.missing_items" in knowledge_parts
    assert "review.suggestions" in knowledge_parts
    assert "查看详情" in knowledge_parts
    assert "item.review_status === 'runbook_candidate'" in knowledge_parts
    assert "item.review_status === 'skill_candidate'" in knowledge_parts
    assert "const actionable = (item.review_status || 'pending') === 'pending'" in knowledge_parts
    assert "import { EvidenceReferenceChip } from './EvidenceReferenceChip'" in knowledge_parts
    assert "value={`${ref.id || ref.tool || ref.type || '-'}" in knowledge_parts


def test_memory_quality_panel_summarizes_learning_publish_quality():
    knowledge = Path("frontend/src/components/views/KnowledgeBase.tsx").read_text(encoding="utf-8")
    knowledge_parts = Path("frontend/src/components/views/KnowledgeBaseParts.tsx").read_text(encoding="utf-8")

    assert "learningCandidates={learningCandidates}" in knowledge
    assert "learningCandidates: LearningCandidate[]" in knowledge_parts
    assert "learningCandidateStats" in knowledge_parts
    assert "学习发布质量" in knowledge_parts
    assert "Runbook/Skill 发布候选" in knowledge_parts
    assert "发布候选" in knowledge_parts
    assert "需补齐" in knowledge_parts
    assert "可推进" in knowledge_parts
    assert "已发布" in knowledge_parts
    assert "质量清单或辅助审核未通过" in knowledge_parts
    assert "不会自动批准或发布" in knowledge_parts
    assert "查看候选" in knowledge_parts


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


def test_run_trace_events_show_evidence_and_approval_refs():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "function runTraceEvidenceId(event: RunTraceEvent)" in source
    assert "function runTraceApprovalRef(event: RunTraceEvent)" in source
    assert "import { EvidenceReferenceChip } from '@/components/views/EvidenceReferenceChip'" in source
    assert "<EvidenceReferenceChip" in source
    assert 'kind="evidence"' in source
    assert 'kind="approval"' in source
    assert "value={runTraceEvidenceId(event)}" in source
    assert "value={runTraceApprovalRef(event)}" in source
    assert "查看本次工具执行归档的完整证据详情" in source


def test_run_trace_evidence_refs_open_tool_trace_detail():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "import ToolTraceList from './ToolTraceList'" in source
    assert "getSessionHistoryEvidenceTrace(sessionId, { evidenceId, limit: 200 })" in source
    assert "onOpenEvidence={(event) => void openRunTraceEvidence(event)}" in source
    assert "function RunTraceEvidenceDialog(" in source
    assert "Run Trace 工具证据" in source
    assert "查看本次工具执行归档的完整证据详情" in source
    assert "ToolTraceList items={[trace]} sessionMode={sessionMode}" in source
    assert "EvidenceReferenceChipProps" in Path("frontend/src/components/views/EvidenceReferenceChip.tsx").read_text(encoding="utf-8")


def test_run_trace_approval_refs_open_readonly_approval_detail():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")
    approvals_api = Path("frontend/src/api/approvals.ts").read_text(encoding="utf-8")

    assert "export async function getApproval(approvalId: string)" in approvals_api
    assert "import { getApproval } from '@/api/approvals'" in source
    assert "onOpenApproval={(event) => void openRunTraceApproval(event)}" in source
    assert "function RunTraceApprovalDialog(" in source
    assert "Run Trace 审批详情" in source
    assert "查看本次工具执行关联的审批详情" in source
    assert "ApprovalStatusBadge status={approval.status}" in source
    assert "ApprovalSourceSummary" in source
    assert "暂未找到该审批记录，当前 Run Trace 仅保留审批引用 ID。" in source


def test_run_trace_learning_preview_is_exposed_as_readonly_ui():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")
    session_api = Path("frontend/src/api/sessionHistory.ts").read_text(encoding="utf-8")
    types = Path("frontend/src/types/index.ts").read_text(encoding="utf-8")

    assert "export interface SessionRunLearningPreview" in types
    assert "deduped?: boolean" in types
    assert "getSessionRunLearningPreview" in session_api
    assert "createSessionRunLearningCandidate" in session_api
    assert "/history/run-trace/learning-preview?" in session_api
    assert "/history/run-trace/learning-candidate" in session_api
    assert "onOpenLearningPreview={(runId) => void openRunTraceLearningPreview(runId)}" in source
    assert "Run Trace 学习预览" in source
    assert "只读预览，不会自动写入记忆或发布 Skill。" in source
    assert "学习预览" in source
    assert "提交候选池" in source
    assert "submittedDeduped: Boolean(response.data.deduped)" in source
    assert "已存在候选" in source
    assert "提交后进入学习候选池，仍需人工审核质量清单。" in source
    assert "可进入候选池" in source
    assert "证据引用" in source


def test_run_trace_context_sources_are_visible_without_prompt_text():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "function runTraceContextSources(group: RunTraceGroup)" in source
    assert "context_sources" in source
    assert "上下文来源" in source
    assert "系统提示词" in source
    assert "长期记忆" in source
    assert "知识库" in source
    assert "资产画像" in source
    assert "命中 ${source.referenceCount}" in source
    assert "读取失败" in source
    assert "未命中" in source
    assert "contextSourceTone(source)" in source


def test_run_trace_prompt_modules_are_visible_without_prompt_text():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "function runTracePromptManifest(group: RunTraceGroup)" in source
    assert "prompt_modules" in source
    assert "Prompt 模块" in source
    assert "证据契约" in source
    assert "上下文优先级" in source
    assert "Skill 指令" in source
    assert "知识库上下文" in source
    assert "长期记忆上下文" in source
    assert "只分析模式" in source
    assert "委派任务" in source
    assert "工具目录" in source
    assert "本地 Skill 路径" in source
    assert "promptModuleTone(module)" in source
    assert "已启用" in source
    assert "未启用" in source
    assert "promptManifest.modules.slice(0, 10).map" in source


def test_run_trace_context_prompt_audit_summary_is_visible():
    source = Path(
        "frontend/src/features/sessions/AiThinkingChainPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "function runTraceAuditSummary(groups: RunTraceGroup[])" in source
    assert "const auditSummary = runTraceAuditSummary(recentRuns)" in source
    assert "Context/Prompt 审计" in source
    assert "上下文源 {auditSummary.contextSources}" in source
    assert "命中 {auditSummary.contextHits}" in source
    assert "失败 {auditSummary.contextErrors}" in source
    assert "Prompt 模块 {auditSummary.promptModules}" in source
    assert "contextSources.filter((source) => source.enabled && source.hit).length" in source
    assert "promptManifest?.modules.filter((module) => module.enabled).length" in source


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


def test_approval_center_exposes_risk_filters_and_search():
    center = Path("frontend/src/components/views/ApprovalCenter.tsx").read_text(encoding="utf-8")
    parts = Path("frontend/src/components/views/ApprovalCenterParts.tsx").read_text(encoding="utf-8")
    data = Path("frontend/src/components/views/useApprovalCenterData.ts").read_text(encoding="utf-8")
    display = Path("frontend/src/components/views/approvalDisplay.ts").read_text(encoding="utf-8")

    assert "ApprovalQueueFilters" in center
    assert "riskFilter={riskFilter}" in center
    assert "search={approvalSearch}" in center
    assert "onRiskFilterChange={setRiskFilter}" in center
    assert "onSearchChange={setApprovalSearch}" in center
    assert "totalCount={approvalTotal}" in center
    assert "export type ApprovalRiskFilter" in display
    assert "approvalRiskFilterLabel" in display
    assert "破坏性" in display
    assert "外发/通知" in display
    assert "写入变更" in display
    assert "技能变更" in display
    assert "const RISK_OPTIONS: ApprovalRiskFilter[]" in parts
    assert "搜索审批 ID、工具、会话、资产" in parts
    assert "当前 {approvals.length}/{totalCount} 条" in parts
    assert "const [riskFilter, setRiskFilter] = useState<ApprovalRiskFilter>('all')" in data
    assert "const [approvalSearch, setApprovalSearch] = useState('')" in data
    assert "approvalMatchesRiskFilter(item, riskFilter)" in data
    assert "approvalSearchText(item).includes(query)" in data
    assert "approvalTotal: approvals.length" in data
    assert "function approvalMatchesRiskFilter" in data
    assert "function approvalSearchText" in data
