// Types for the OpsCore AIOps platform

export interface Session {
  id: string
  host: string
  remark: string
  isReadWriteMode: boolean
  skills: string[]
  agentProfile: string
  user: string
  asset_type: string
  protocol: string
  extra_args: Record<string, unknown>
  heartbeatEnabled: boolean
  tags: string[]
  target_scope?: string
  scope_value?: string | null
  backendStreaming?: boolean
  // Frontend-only state
  messages: ChatMessage[]
  isStreaming: boolean
  historyLoaded?: boolean
}

export interface AssetProfileEvidence {
  label: string
  value: string
  source?: string
}

export interface AssetProfileFocusArea {
  title: string
  reason: string
  priority: string
}

export interface AssetProfileRelation {
  direction: 'inbound' | 'outbound' | 'bidirectional' | 'unknown' | string
  peer: string
  peer_role?: string
  endpoint?: string
  protocol?: string
  evidence?: string
  confidence?: number
}

export interface AssetProfileRelationStrategy {
  direction: 'inbound' | 'outbound' | 'bidirectional' | 'unknown' | string
  title: string
  method?: string
  evidence?: string
  tool_hint?: string
}

export interface AssetProfile {
  version: number
  session_id: string
  asset_key?: string
  host?: string
  port?: number
  remark?: string
  asset_type?: string
  protocol?: string
  role_label: string
  role_category: string
  purpose: string
  confidence: number
  risk_level: 'normal' | 'watch' | 'high' | string
  evidence: AssetProfileEvidence[]
  focus_areas: AssetProfileFocusArea[]
  relations?: AssetProfileRelation[]
  relation_strategies?: AssetProfileRelationStrategy[]
  services: string[]
  tags: string[]
  source?: string
  source_summary?: string
  profile_prompt?: string
  updated_at?: string
}

export interface RealtimeMetricPoint {
  time: string
  status: 'ok' | 'error' | string
  cpu?: number
  memory?: number
  disk?: number
  load?: number
  top_process?: Array<{ pid: string; name: string; cpu: number; memory: number }>
  error?: string
  command?: string
}

export interface RealtimeCanvasItem {
  id: string
  title: string
  kind?: 'metrics' | 'topology' | 'fault_story' | 'custom_html' | string
  mode?: 'realtime' | 'window' | 'static' | string
  session_id: string
  session?: {
    session_id: string
    host: string
    port?: string | number
    username?: string
    asset_type?: string
    protocol?: string
    remark?: string
  }
  status: 'running' | 'paused' | 'expired' | 'stopped' | string
  metrics: string[]
  metric_labels?: Record<string, string>
  interval_seconds: number
  duration_seconds: number
  remaining_seconds: number
  started_at: string
  created_at: string
  generated_at?: string
  expires_at: string
  last_collect_at?: string
  last_error?: string
  stop_reason?: string
  stop_existing?: boolean
  scripts?: Record<string, string>
  script_mode?: string
  collector_language?: string
  collector_code?: string
  canvas_spec?: Record<string, unknown>
  data_schema?: Record<string, unknown>
  html?: string
  ai_prompt_template?: string
  cleanup_note?: string
  command_audit?: Array<{ time: string; command: string; status?: string }>
  points: RealtimeMetricPoint[]
  latest?: RealtimeMetricPoint | null
}

export interface SlashCommand {
  id: string
  label: string
  description: string
  prompt: string
  prompt_template?: string
  category: string
  scope_type?: 'global' | 'asset_type' | 'protocol' | 'asset' | string
  asset_type?: string
  protocol?: string
  host?: string
  readonly?: boolean
  pinned?: boolean
  enabled?: boolean
  sort_order?: number
  source?: 'builtin' | 'custom' | string
  is_override?: boolean
  builtin_id?: string
  asset_types?: string[]
  protocols?: string[]
}

export interface ChatMessage {
  id: string
  memoryId?: number
  _memory_id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  attachments?: ChatMessageAttachment[]
  feedback?: {
    rating: 'up' | 'down'
    note?: string
    created_at?: string
    memory_policy?: string
    memory_path?: string
  }
  memoryRefs?: MemoryReference[]
  memory_refs?: MemoryReference[]
  runtimeEvents?: ChatRuntimeEvent[]
  // For tool execution traces
  execTrace?: ExecTraceItem[]
  // For tool approval requests
  toolApproval?: ToolApproval
  // For model-initiated user input or option selection
  userInteraction?: UserInteractionRequest
}

export interface ChatRuntimeEvent {
  type: 'status'
  content: string
  timestamp: number
}

export interface MemoryReference {
  scope_id?: string
  scope_label?: string
  source_type?: 'memory' | 'rag' | string
  kind?: string
  kind_label?: string
  title?: string
  source_session_id?: string
  score?: number | string
  updated_at?: string
  timestamp?: string
  summary_preview?: string
  path?: string
}

export interface SessionMemoryActivity {
  session_id: string
  summary: {
    referenced_count: number
    referenced_messages: number
    promoted_count: number
    pending_candidate_count?: number
    rejected_count: number
    pending_conflict_count: number
  }
  referenced: Array<{
    message_id?: number | string
    created_at?: string | number
    message_preview: string
    refs: MemoryReference[]
  }>
  feedback: Array<{
    message_id?: number | string
    created_at?: string | number
    rating: 'up' | 'down' | string
    note?: string
    memory_policy?: string
    message_preview: string
  }>
  pending_conflicts: MemoryPendingConflict[]
}

export interface ChatMessageAttachment {
  filename: string
  ext?: string
  size: number
  kind?: string
  rows?: number
  pages?: number
  sheets?: string[]
  truncated?: boolean
}

export interface ExecTraceItem {
  type: 'tool_start' | 'tool_end'
  toolCallId?: string
  tool: string
  args?: string
  result?: string
  resultMeta?: Record<string, unknown>
  evidenceId?: string
  evidence?: ToolEvidence
  status?: 'running' | 'done' | 'error'
  startedAt?: number
  completedAt?: number
}

export interface RunTraceEvent {
  id?: string | number
  created_at?: string | number
  run_id?: string
  event_type: string
  event_ts?: number
  payload: Record<string, unknown>
  summary: string
}

export interface RunTraceRun {
  run_id: string
  started_at?: string | number | null
  ended_at?: string | number | null
  duration_ms?: number | null
  status: string
  reason?: string
  event_count: number
  tool_count: number
  step_count: number
  latest_event_type?: string
  latest_summary?: string
}

export interface RunTraceAuditSummary {
  run_count: number
  event_count: number
  audited_run_count: number
  unaudited_run_count: number
  context_sources: number
  context_hits: number
  context_errors: number
  prompt_modules: number
  source_counts?: Record<string, { total: number; hit: number; error: number; disabled: number }>
  module_counts?: Record<string, { total: number; enabled: number; disabled: number }>
}

export interface SessionRunLearningPreview {
  session_id: string
  run_id?: string
  source: string
  candidate_type: 'runbook' | 'skill' | string
  eligible: boolean
  title: string
  summary: string
  event_count: number
  run_count: number
  tool_count: number
  status_counts: Record<string, number>
  evidence_refs: MemoryCandidateRef[]
  draft?: {
    title?: string
    outline?: string[]
  }
  next_action?: string
}

export interface SessionRunLearningCandidateResult {
  candidate?: MemoryCandidate
  learning_candidate?: LearningCandidate
  preview?: SessionRunLearningPreview
  deduped?: boolean
}

export interface ToolEvidence {
  evidence_id: string
  session_id: string
  asset_ref?: {
    asset_id?: string | number | null
    target_scope?: string
    asset_type?: string | null
    protocol?: string | null
    host?: string | null
    port?: number | string | null
  }
  tool_name: string
  tool_family: string
  input_summary?: string
  redacted_input?: string
  output_preview?: string
  result_status?: 'done' | 'error' | string
  result_meta?: Record<string, unknown>
  approval_ref?: string
  started_at?: number
  finished_at?: number
}

export interface SafetyPolicyAction {
  id: string
  label: string
  description?: string
  severity?: 'low' | 'medium' | 'high' | 'critical' | string
}

export interface ToolApproval {
  toolCallId: string
  toolName: string
  args: string
  sessionMode?: 'readonly' | 'readwrite'
  sessionModeSource?: 'context' | 'session_snapshot' | 'inferred_unknown'
  allowModifications?: boolean
  executionMode?: string
  reason?: string
  approvalSources?: Array<Record<string, unknown> | null>
  actions?: SafetyPolicyAction[]
  primaryAction?: SafetyPolicyAction | null
  approvalSource?: Record<string, unknown> | null
  toolPolicy?: Record<string, unknown> | null
  uniqueId: string
  resolved: boolean
  decision?: 'approved' | 'rejected' | 'timeout'
  operator?: string
  note?: string
  autoAll?: boolean
  decidedAt?: number
}

export interface UserInteractionOption {
  label: string
  value: string
  description?: string
}

export interface UserInteractionRequest {
  requestId: string
  prompt: string
  inputType: 'text' | 'password' | 'choice' | string
  options?: UserInteractionOption[]
  placeholder?: string
  required?: boolean
  timeoutSeconds?: number
  resolved: boolean
  status?: 'submitted' | 'timeout' | string
  value?: string
  label?: string
}

export interface ToolDefinition {
  name: string
  label?: string
  toolset: string
  scope: string
  description: string
  safety_category: string
  protocols: string[]
  asset_types: string[]
  requires_virtual: boolean
  operation_mode?: 'read' | 'write' | 'read_write' | 'destructive' | 'external_effect' | 'interactive' | string
  destructive?: boolean
  concurrency_safe?: boolean
  approval_policy?: 'none' | 'guarded_write' | 'always_required' | string
  evidence_family?: string
  ui_renderer?: string
  result_store_policy?: 'evidence' | 'audit_only' | 'audit_and_evidence' | string
  timeout_policy?: {
    default_seconds: number
    max_seconds: number
    user_driven?: boolean
  }
  retry_policy?: {
    max_attempts: number
    retry_on: string[]
    delay_seconds?: number
  }
  metadata_version?: number
  runtime_scope?: string
  enabled?: boolean
}

export interface ToolDisplayDetail {
  name: string
  label?: string
  description?: string
  toolset?: string
  scope?: string
  safety_category?: string
  protocols?: string[]
  asset_types?: string[]
  enabled?: boolean
}

export interface ToolsetInfo {
  id: string
  label?: string
  enabled: boolean
  tools: ToolDefinition[]
}

export interface SessionToolCatalog {
  toolsets: ToolsetInfo[]
  active_tools?: string[]
  active_tool_details?: ToolDisplayDetail[]
  context?: {
    target_scope: string
    asset_type: string
    protocol: string
    host?: string
    port?: number
  }
}

export type ToolCenterStatus = 'available' | 'controlled' | 'not_wired' | string

export interface ToolCenterTool extends ToolDefinition {
  status: ToolCenterStatus
  status_label: string
  model_exposed: boolean
  execution_enabled: boolean
  source: 'opscore' | 'builtin' | string
  control_reason?: string
}

export interface ToolCenterToolset {
  id: string
  label?: string
  tools: ToolCenterTool[]
  counts: Record<string, number>
}

export interface ToolCenterCatalog {
  summary: Record<string, number>
  status_labels: Record<string, string>
  toolsets: ToolCenterToolset[]
}

export interface SkillInfo {
  id: string
  name: string
  description: string
  category: string
  is_market?: boolean
  source_path?: string
}

export interface SkillValidationIssue {
  code: string
  message: string
}

export interface SkillValidationResult {
  valid: boolean
  issues: SkillValidationIssue[]
  warnings: SkillValidationIssue[]
  skill_id: string
  file_name: string
}

export interface Asset {
  id: number
  remark: string
  host: string
  port: number
  username: string
  password?: string
  asset_type: string
  protocol?: string
  agent_profile: string
  extra_args: Record<string, unknown>
  skills: string[]
  tags: string[]
}

export interface AssetParamDefinition {
  field: string
  label: string
  type: string
  required?: boolean
  defaultValue?: string | number | boolean
  placeholder?: string
  range?: string
  limit?: number
  group?: string
  options?: Array<{ label: string; value: string | number | boolean }>
  depend?: Record<string, Array<string | number | boolean>>
  hide?: boolean
}

export interface AssetAccessProtocol {
  protocol: string
  label: string
  purpose?: 'operation' | 'monitoring' | 'probe' | string
  purpose_label?: string
  role?: string
  role_label?: string
  source: string
  default_port?: number
  security?: string
  description?: string
  is_default?: boolean
  is_current?: boolean
  supported?: boolean
}

export interface AssetTypeDefinition {
  id: string
  label: string
  category: string
  protocol: string
  default_port: number
  inspection_profile?: string
  source?: string
  hertzbeat_category?: string
  hertzbeat_protocols?: string[]
  access_protocols?: AssetAccessProtocol[]
  params?: AssetParamDefinition[]
  category_meta?: AssetCategoryDefinition
  capability?: {
    family: string
    connector: string
    operation_model: string
    tools: string[]
    tool_details?: ToolDisplayDetail[]
    credential_fields: string[]
    connector_group?: AssetCategoryDefinition & { tools?: string[] }
    driver_key?: string
    maturity: 'native' | 'generic' | 'needs_adapter' | string
    setup?: Record<string, unknown>
    parameter_template?: AssetParamDefinition[]
    risk_model: {
      read_only_default: boolean
      approval_required_for_write: boolean
      hard_block_supported: boolean
      safety_category: string
    }
    standard_version: string
  }
}

export interface AssetCategoryDefinition {
  id: string
  label: string
  group?: string
  order?: number
  description?: string
}

export interface CronJob {
  id: string
  cron_expr: string
  message: string
  inspection_cycle?: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'custom' | string
  inspection_depth?: 'quick' | 'standard' | 'deep' | string
  host: string
  target_host?: string
  username: string
  agent_profile: string
  next_run?: string
  next_run_time?: string
  status?: 'scheduled' | 'paused' | string
  asset_id?: number | null
  target_scope?: string
  scope_value?: string | null
  template_id?: string | null
  notification_channel?: string
  retry_count?: number
  active_skills?: string[]
  run_state?: CronRunState
}

export interface CronRunState {
  schedule_status: 'scheduled' | 'paused' | string
  running: boolean
  running_run_id?: string | null
  started_at?: string | null
  task_status?: 'running' | 'cancelling' | 'completed' | 'failed' | 'cancelled' | string | null
  current_stage?: string | null
  current_target?: {
    asset_id?: number | null
    host?: string | null
    asset_type?: string | null
    protocol?: string | null
  } | null
  progress_current?: number
  progress_total?: number
  progress_percent?: number
  elapsed_ms?: number
  cancel_requested_at?: string | null
  runtime_message?: string | null
  effective_status?: 'running' | 'completed' | 'failed' | 'partial' | 'empty' | 'cancelled' | 'orphaned' | string | null
  latest_run_id?: string | null
  latest_status?: 'running' | 'completed' | 'failed' | 'partial' | 'empty' | 'cancelled' | string | null
  latest_message?: string | null
  latest_started_at?: string | null
  latest_completed_at?: string | null
  latest_duration_ms?: number
  target_count: number
  success_count: number
  error_count: number
  notification_status?: string | null
  notification_message?: string | null
}

export interface DashboardOverview {
  summary: Record<string, number>
  by_category: Record<string, number>
  by_protocol: Record<string, number>
  by_type: Record<string, number>
  active_by_protocol: Record<string, number>
  run_trace_audit?: DashboardRunTraceAuditOverview
  alerts?: {
    total: number
    by_status: Record<string, number>
    by_severity: Record<string, number>
    top_hosts: Array<{ host: string; count: number }>
  }
  jobs?: {
    total: number
    scheduled: number
    paused: number
  }
  inspection_runs?: {
    total_runs: number
    completed: number
    failed: number
    partial: number
    empty: number
    success_rate: number
    targets_total: number
    targets_success: number
    targets_error: number
    recent_failures: InspectionRun[]
  }
}

export interface DashboardRunTraceAuditOverview {
  session_count: number
  sessions_with_trace: number
  sessions_with_audit: number
  sessions_with_gaps: number
  session_errors: number
  run_count: number
  event_count: number
  audited_run_count: number
  unaudited_run_count: number
  context_sources: number
  context_hits: number
  context_errors: number
  prompt_modules: number
  runtime_tool_count: number
  runtime_success_count: number
  runtime_error_count: number
  runtime_timeout_count: number
  runtime_retry_count: number
  runtime_concurrent_count: number
  runtime_untracked_count: number
  source_counts?: Record<string, { total: number; hit: number; error: number; disabled: number }>
  module_counts?: Record<string, { total: number; enabled: number; disabled: number }>
  runtime_error_types?: Record<string, number>
  sessions: Array<{
    session_id: string
    label: string
    host: string
    protocol: string
    group_name: string
    run_count: number
    audited_run_count: number
    unaudited_run_count: number
    context_errors: number
    runtime_tool_count?: number
    runtime_error_count?: number
    runtime_timeout_count?: number
    runtime_retry_count?: number
  }>
}

export interface AlertTrendPoint {
  date: string
  total: number
  [severity: string]: string | number
}

export type AlertEventStatus = 'open' | 'acknowledged' | 'closed' | 'suppressed'

export interface AlertEventNote {
  time: string
  content: string
}

export interface AlertEvent {
  id: string
  created_at: string
  updated_at: string
  closed_at?: string | null
  status: AlertEventStatus | string
  assignee: string
  host: string
  alert_name: string
  severity: string
  description: string
  source: string
  source_type?: string
  source_family?: string
  alert_class?: string
  priority?: string
  noise_action?: string
  automation_decision?: {
    run_ai?: boolean
    notify?: boolean
    reason?: string
    rule_id?: string
    rule_name?: string
    remediation_mode?: string
    allowed_remediation_actions?: string[]
    cooldown_minutes?: number
    ai_cooldown?: {
      suppressed?: boolean
      window_minutes?: number
      last_triggered_at?: string
      next_allowed_at?: string
    }
  }
  notification_plan?: {
    channel?: string
    when?: string
    targets?: string[]
  }
  external_id?: string
  fingerprint?: string
  starts_at?: string
  ends_at?: string
  repeat_count?: number
  labels?: Record<string, unknown>
  annotations?: Record<string, unknown>
  payload: Record<string, unknown>
  notes: AlertEventNote[]
}

export interface AlertAutomationRuleConditions {
  source_families?: string[]
  severities?: string[]
  alert_classes?: string[]
  priorities?: string[]
  host_contains?: string[]
  name_contains?: string[]
  label_contains?: string[]
  min_repeat_count?: number
  recovery?: boolean
}

export type AlertAutomationAction = 'record_only' | 'analyze' | 'dedupe_escalate' | 'suppress' | 'close'

export interface AlertAutomationRule {
  id: string
  name: string
  enabled: boolean
  conditions: AlertAutomationRuleConditions
  action: AlertAutomationAction
  notify: boolean
  channels: string[]
  remediation_mode?: string
  allowed_remediation_actions?: string[]
  cooldown_minutes?: number
  reason: string
}

export interface AlertAutomationPolicy {
  version: number
  rules: AlertAutomationRule[]
}

export interface AlertAutomationPolicyTestResult {
  alert: Record<string, unknown>
  policy: {
    source_family?: string
    alert_class?: string
    priority?: string
    noise_action?: string
    automation_decision?: AlertEvent['automation_decision']
    notification_plan?: AlertEvent['notification_plan']
  }
}

export interface AlertWorkflowStep {
  id: string
  title: string
  status: string
  summary?: string
  details?: Record<string, unknown>
}

export interface AlertWorkflowMessage {
  role: string
  time: string
  content: string
}

export interface AlertWorkflowSessionLink {
  session_id: string
  host: string
  remark?: string
  asset_type?: string
  protocol?: string
  allow_modifications?: boolean
  active_skills?: string[]
  tags?: string[]
}

export interface AlertWorkflowAssetCandidate {
  asset_id?: number | string
  host: string
  remark?: string
  asset_type?: string
  protocol?: string
  tags?: string[]
  can_create_session?: boolean
}

export interface AlertWorkflow {
  id: string
  alert_id: string
  created_at: string
  updated_at: string
  status: string
  alert_name?: string
  host?: string
  source_family?: string
  linked_sessions?: AlertWorkflowSessionLink[]
  asset_candidates?: AlertWorkflowAssetCandidate[]
  steps: AlertWorkflowStep[]
  messages: AlertWorkflowMessage[]
}

export interface RiskRankingItem {
  host: string
  count: number
  score: number
}

export interface InspectionTemplateStep {
  title: string
  tool: string
  command?: string
  command_candidates?: string[]
  query?: string
  args?: Record<string, unknown>
}

export interface InspectionTemplate {
  id: string
  name: string
  description?: string
  asset_types: string[]
  protocols: string[]
  steps: InspectionTemplateStep[]
  enabled?: boolean
  updated_at?: string
}

export interface InspectionRunTarget {
  asset_id?: number | null
  host: string
  port?: number
  username?: string
  asset_type?: string | null
  protocol?: string | null
  status: 'success' | 'error' | string
  attempts?: number
  started_at?: string
  completed_at?: string
  duration_ms?: number
  result?: string
  error?: string
}

export interface InspectionRunEvent {
  time: string
  type: string
  message: string
  status?: string
  target?: {
    asset_id?: number | null
    host?: string | null
    asset_type?: string | null
    protocol?: string | null
  }
}

export interface InspectionRunTranscriptEvent {
  id: string
  run_id: string
  time: string
  type: string
  source: string
  message: string
  status?: string
  payload?: Record<string, unknown>
}

export interface InspectionNotificationResult {
  status?: string
  message?: string
}

export interface InspectionRunTracePhase {
  id: string
  label: string
  status: string
  started_at?: string | null
  completed_at?: string | null
  detail?: string
}

export interface InspectionRunTrace {
  trace_id: string
  kind: 'inspection_run' | string
  status: string
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number
  counters: {
    events: number
    targets: number
    success: number
    error: number
    cancelled: number
  }
  phases: InspectionRunTracePhase[]
}

export interface InspectionScoreDimension {
  id: string
  label: string
  score: number
  weight?: number
}

export interface InspectionScoreDeduction {
  dimension: string
  label: string
  points: number
  reason: string
  host?: string
}

export interface InspectionTargetScore {
  target: {
    asset_id?: number | null
    host?: string | null
    asset_type?: string | null
    protocol?: string | null
  }
  status?: string
  profile: string
  profile_label: string
  score: number
  grade: string
  grade_label: string
  dimensions: InspectionScoreDimension[]
  deductions: InspectionScoreDeduction[]
}

export interface InspectionScore {
  score: number
  grade: string
  grade_label: string
  profile: string
  profile_label: string
  dimensions: InspectionScoreDimension[]
  target_scores: InspectionTargetScore[]
  deductions: InspectionScoreDeduction[]
  run_status?: string
}

export interface InspectionRun {
  id: string
  job_id: string
  status: 'running' | 'completed' | 'failed' | 'partial' | 'empty' | 'cancelled' | string
  target_scope: string
  scope_value?: string | null
  message: string
  target_count: number
  targets: InspectionRunTarget[]
  events?: InspectionRunEvent[]
  notification?: InspectionNotificationResult | null
  started_at: string
  completed_at?: string | null
  duration_ms?: number
}

export interface InspectionTrendPoint {
  date: string
  total_runs: number
  completed: number
  failed: number
  partial: number
  empty: number
  target_success: number
  target_error: number
  success_rate: number
  avg_duration_ms: number
}

export interface InspectionReport {
  run_id: string
  job_id: string
  status: string
  target_scope: string
  scope_value?: string | null
  message: string
  started_at?: string
  completed_at?: string
  summary: {
    target_count: number
    success_count: number
    error_count: number
    success_rate: number
  }
  notification?: InspectionNotificationResult | null
  events?: InspectionRunEvent[]
  transcript?: {
    event_count: number
    events: InspectionRunTranscriptEvent[]
  }
  trace?: InspectionRunTrace
  score?: InspectionScore
  targets: InspectionRunTarget[]
}

export interface VerificationStep {
  id: string
  label: string
  status: 'supported' | 'gap' | string
  description: string
}

export interface AssetVerificationMatrix {
  asset: {
    id: number
    remark: string
    host: string
    port: number
    username: string
    asset_type: string
    protocol: string
    category: string
    agent_profile: string
    tags: string[]
    extra_args: Record<string, unknown>
  }
  active_tools: string[]
  active_tool_details?: ToolDisplayDetail[]
  supported_protocols?: AssetAccessProtocol[]
  steps: VerificationStep[]
  coverage: {
    total: number
    supported: number
    gaps: number
  }
  status: 'ready' | 'needs_attention' | string
}

export interface ProtocolVerificationOverview {
  summary: {
    asset_total: number
    protocols: Record<string, number>
    categories: Record<string, number>
    steps_total: number
    gaps_total: number
    ready_assets: number
    needs_attention: number
  }
  matrix: AssetVerificationMatrix[]
}

export interface ProtocolVerificationStatusOverview {
  summary: ProtocolVerificationOverview['summary']
  matrix: Array<{
    asset: Pick<AssetVerificationMatrix['asset'], 'id'>
    coverage: AssetVerificationMatrix['coverage']
    status: AssetVerificationMatrix['status']
  }>
}

export interface AssetVerificationRun {
  id: string
  asset: AssetVerificationMatrix['asset']
  status: 'success' | 'failed' | 'partial' | string
  steps: Array<{
    id: string
    label: string
    status: 'success' | 'error' | 'skipped' | string
    message: string
    details: Record<string, unknown>
    completed_at: string
  }>
  matrix_status: string
  started_at: string
  completed_at: string
}

export interface KnowledgeFile {
  filename: string
  original_filename?: string
  size?: number
  chunks?: number
  extension?: string
  source_path?: string
  note_path?: string
  vault_path?: string
  status?: string
  compile_status?: string
  vector_status?: string
  vector_error?: string
  obsidian_compatible?: boolean
  created_at?: string
  updated_at?: string
  tags?: string[]
}

export interface KnowledgeDocumentContent extends KnowledgeFile {
  content: string
  content_sha256?: string
  content_type?: 'text' | 'source_note' | 'metadata' | string
  preview_available?: boolean
  truncated?: boolean
  preview_limit?: number
}

export interface KnowledgeListSummary {
  total: number
  filtered: number
  total_size: number
  vector_counts: Record<string, number>
  compile_counts: Record<string, number>
  extension_counts: Record<string, number>
  searchable_count: number
  indexed_ratio: number
  latest_updated_at?: string
  query?: string
  active_vector_status?: string
  active_extension?: string
}

export interface KnowledgeListPagination {
  page: number
  per_page: number
  total: number
  page_count: number
  has_prev: boolean
  has_next: boolean
}

export interface KnowledgeVectorStoreStatus {
  status: string
  status_label?: string
  health?: string
  message: string
  embedding_model?: string
  embedding_dim?: number
  model_configured?: boolean
  database?: string
  db_path?: string
  table?: string
  table_exists?: boolean
  db_path_exists?: boolean
  table_names?: string[]
  chunk_count?: number
  source_count?: number
  indexed_count?: number
  skipped_count?: number
  failed_count?: number
  pending_count?: number
  reindex_timeout_seconds?: number
  action_label?: string
  recommended_action?: string
  diagnostics?: string[]
  error?: string
}

export interface KnowledgeReindexResult extends KnowledgeDocumentContent {
  message?: string
}

export interface KnowledgeCompileQueueItem extends KnowledgeFile {
  id: string
  source_session_id?: string
  compile_stage?: string
  status_label?: string
  candidate_path?: string
  wiki_path?: string
  compiled_at?: string
  approved_at?: string
  compile_model_status?: string
  compile_error?: string
  review_status?: string
  candidate_exists?: boolean
  candidate_size?: number
  article_exists?: boolean
  article_size?: number
  content?: string
  content_sha256?: string
}

export interface KnowledgeVaultSearchResult {
  id?: string
  source_session_id?: string
  title: string
  kind: 'articles' | 'candidates' | 'sources' | 'raw' | string
  kind_label: string
  path: string
  compile_status?: string
  compile_stage?: string
  snippet: string
  score: number
  updated_at?: string
}

export interface KnowledgeVaultGraphNode {
  id: string
  title: string
  kind: 'article' | 'candidate' | string
  kind_label?: string
  path: string
  source_session_id?: string
  compile_stage?: string
  review_status?: string
  updated_at?: string
  degree?: number
  links_in?: number
  links_out?: number
  x?: number
  y?: number
  size?: number
}

export interface KnowledgeVaultGraphEdge {
  source: string
  target: string
  kind: 'wikilink' | 'mention' | string
  label: string
}

export interface KnowledgeVaultGraph {
  nodes: KnowledgeVaultGraphNode[]
  edges: KnowledgeVaultGraphEdge[]
  summary: {
    node_count: number
    edge_count: number
    article_count: number
    candidate_count: number
    linked_node_count?: number
    isolated_node_count?: number
    relation_counts?: Record<string, number>
    generated_at?: string
  }
}

export interface MemoryItem {
  path: string
  scope_id: string
  store_id?: string
  store_name?: string
  access?: 'read_only' | 'read_write' | string
  lifecycle?: string
  memory_model?: string
  retrieval_enabled?: boolean
  retrieval_entries?: number
  audit_entries?: number
  entry_kinds?: Record<string, number>
  usage_policy?: string
  archived?: boolean
  legacy?: boolean
  size: number
  entries: number
  updated_at: string
  preview: string
}

export interface MemoryDetail extends MemoryItem {
  content: string
  content_sha256: string
}

export interface MemoryVersion {
  version_id?: string
  timestamp: string
  operation: 'created' | 'modified' | 'deleted' | 'restored' | string
  path: string
  scope_id: string
  source_session_id?: string
  content_sha256?: string
  summary_sha256?: string
  metadata?: Record<string, unknown>
  redacted?: boolean
}

export interface MemoryPendingConflict {
  version_id: string
  timestamp: string
  path: string
  scope_id: string
  reason: string
  existing_preview?: string
  new_preview?: string
  source_session_id?: string
}

export interface MemoryCandidate {
  candidate_id: string
  path: string
  scope_id: string
  timestamp: string
  source_session_id?: string
  summary: string
  summary_preview?: string
  memory_kind?: string
  memory_kind_label?: string
  candidate_type?: string
  review_status?: string
  retrieval_enabled?: boolean
  feedback_target_message_id?: number | string
  source_refs?: MemoryCandidateRef[]
  evidence_refs?: MemoryCandidateRef[]
  recommended_action?: string
}

export interface MemoryCandidateRef {
  type?: string
  label?: string
  id?: string
  path?: string
  tool?: string
  status?: string
  evidence_family?: string
  sql_action?: string
  http_action?: string
  command_action?: string
  action_id?: string
  action_label?: string
}

export interface LearningCandidatePublishedArtifact {
  artifact_id: string
  target_type: 'runbook' | 'skill' | string
  file_path: string
  status: string
  generated_by: string
  generated_reason: string
  generated_at: string
  content_preview?: string
  artifact_sha256?: string
  content_sha256?: string
  artifact_size?: number | string
}

export interface LearningCandidatePublishedArtifactDetail extends LearningCandidatePublishedArtifact {
  candidate_id: string
  content: string
}

export interface LearningCandidate {
  id: string
  target_type: 'runbook' | 'skill' | string
  status: string
  created_at: string
  updated_at?: string
  actor?: string
  source_candidate_id: string
  source_path: string
  source_session_id?: string
  feedback_target_message_id?: number | string
  summary: string
  summary_preview?: string
  memory_kind?: string
  source_refs?: MemoryCandidateRef[]
  evidence_refs?: MemoryCandidateRef[]
  next_action?: string
  quality_checklist?: Array<{
    key: string
    label: string
    ok: boolean
    note?: string
  }>
  quality_events?: Array<{
    actor: string
    reason: string
    timestamp: string
    passed?: number
    total?: number
  }>
  status_events?: Array<{
    from?: string
    to: string
    actor: string
    reason: string
    timestamp: string
  }>
  review?: {
    reviewer?: string
    decision?: 'accept' | 'needs_human_review' | 'reject' | string
    risk_level?: 'low' | 'medium' | 'high' | string
    missing_items?: string[]
    suggestions?: string[]
    reviewed_at?: string
  }
  model_reviews?: Array<{
    reviewer?: string
    reviewer_role?: 'primary' | 'assistant' | string
    model_id?: string
    target_type?: string
    trigger?: string
    decision?: 'accept' | 'needs_human_review' | 'reject' | string
    risk_level?: 'low' | 'medium' | 'high' | string
    missing_items?: string[]
    suggestions?: string[]
    reviewed_at?: string
  }>
  review_events?: Array<{
    trigger: string
    actor: string
    reason?: string
    timestamp: string
    reviewer?: string
    reviewer_role?: 'primary' | 'assistant' | string
    model_id?: string
    decision?: 'accept' | 'needs_human_review' | 'reject' | string
    risk_level?: 'low' | 'medium' | 'high' | string
    missing_items?: string[]
  }>
  published_artifact?: LearningCandidatePublishedArtifact
}

export interface MemoryReviewItem extends MemoryItem {
  age_days: number
  stale_days: number
  reason: string
  recommended_action: string
}

export interface MemoryQualityCompressionCandidate {
  path: string
  scope_id: string
  store_id?: string
  store_name?: string
  entries: number
  size: number
  updated_at: string
  priority: 'high' | 'medium' | 'low' | string
  score: number
  reason: string
  recommended_action: string
}

export interface MemoryQualityReport {
  summary: {
    memory_count: number
    entry_count: number
    store_count: number
    pending_conflict_count: number
    stale_review_count: number
    compression_candidate_count: number
    duplicate_entry_count: number
    recent_version_count: number
    health_score: number
  }
  stores: Array<{
    store_id: string
    store_name: string
    memories: number
    entries: number
    size: number
  }>
  compression_candidates: MemoryQualityCompressionCandidate[]
  policy: {
    mode: string
    stale_days: number
    auto_apply: boolean
    rule: string
  }
}

export interface MemorySearchResult {
  session_id?: string
  _memory_scope_id?: string
  timestamp?: string
  summary?: string
  memory_model?: string
  memory_kind?: string
  memory_kind_label?: string
  retention_tier?: string
  usage_role?: string
  retrieval_enabled?: boolean
  _distance?: number
  path?: string
}

export interface MemoryStoreInfo {
  id: string
  name: string
  description: string
  path_prefix: string
  access: 'read_only' | 'read_write' | string
  lifecycle: string
  memory_model?: string
  instructions?: string
}

export interface ApiResponse<T = Record<string, unknown>> {
  status: 'success' | 'error'
  data: T
  message: string
}

export interface ObservabilityOverview {
  system_count: number
  source_count: number
  profile_pack_count: number
  unknown_count: number
  pending_review_count: number
  discovery_candidate_count?: number
  investigation_count?: number
}

export interface ObservabilityBusinessSystem {
  id: string
  name: string
  environment: string
  description: string
  criticality: string
  owner: string
  aliases: string[]
  tags: string[]
  status: string
  profile_completeness: number
  created_at: string
  updated_at: string
}

export interface ObservabilityComponent {
  id: string
  system_id: string
  name: string
  component_type: string
  layer: string
  workload_family: string
  profile_pack_id?: string | null
  environment: string
  status: string
  confidence: string
  source: string
  metadata: Record<string, unknown>
}

export interface ObservabilityRelationship {
  id: string
  system_id: string
  from_component_id: string
  to_component_id: string
  relationship_type: string
  confidence: string
  source: string
  evidence_ids: string[]
  metadata: Record<string, unknown>
}

export interface ObservabilitySource {
  id: string
  name: string
  source_type: string
  source_origin: string
  status: string
  capabilities: string[]
  bound_system_ids: string[]
  bound_component_ids: string[]
  session_id?: string | null
  metadata: Record<string, unknown>
}

export interface ObservabilityProfilePack {
  id: string
  name: string
  workload_family: string
  layer: string
  component_types: string[]
  source_types: string[]
  capabilities: string[]
  signals: string[]
  read_only: boolean
}

export interface ObservabilitySystemSummary {
  system: ObservabilityBusinessSystem
  component_count: number
  unknown_count: number
  relationship_count: number
  source_count: number
  bound_asset_count?: number
  bound_session_count?: number
  layer_counts: Record<string, number>
}

export interface ObservabilityProfile {
  system: ObservabilityBusinessSystem
  components: ObservabilityComponent[]
  relationships: ObservabilityRelationship[]
  observable_sources: ObservabilitySource[]
  unknowns: ObservabilityComponent[]
}

export interface ObservabilityDiscoveryCandidate {
  id: string
  system_id: string
  candidate_type: 'component' | 'relationship' | 'source' | string
  title: string
  summary: string
  status: 'pending_review' | 'confirmed' | 'rejected' | 'postponed' | string
  confidence: string
  proposed_component?: ObservabilityComponent | null
  proposed_relationship?: ObservabilityRelationship | null
  evidence_ids: string[]
  evidence_summary: string[]
  suggested_actions: string[]
  created_at: string
}

export interface ObservabilityInvestigation {
  id: string
  system_id: string
  title: string
  symptom: string
  time_window: string
  status: 'draft' | 'running' | 'waiting_review' | 'closed' | string
  severity: 'unknown' | 'info' | 'warning' | 'critical' | string
  agent_plan: string[]
  evidence_count: number
  root_cause_candidates: string[]
  tasks: ObservabilityInvestigationTask[]
  evidence: ObservabilityEvidence[]
  root_causes: ObservabilityRootCause[]
  created_at: string
  updated_at: string
}

export interface ObservabilityInvestigationTask {
  id: string
  investigation_id: string
  agent_role: string
  target_component_id?: string | null
  source_id?: string | null
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | string
  input_json: Record<string, unknown>
  output_summary: string
  started_at: string
  finished_at: string
  error_message: string
}

export interface ObservabilityEvidence {
  id: string
  investigation_id: string
  task_id?: string | null
  component_id?: string | null
  source_id?: string | null
  evidence_type: string
  title: string
  summary: string
  raw_ref: string
  raw_excerpt: string
  tool_evidence: Record<string, unknown>
  confidence: string
  timestamp: string
  created_at: string
}

export interface ObservabilityRootCause {
  id: string
  investigation_id: string
  title: string
  description: string
  likelihood: string
  impact: string
  confidence: string
  supporting_evidence_ids: string[]
  contradicting_evidence_ids: string[]
  recommended_next_steps: string[]
  status: 'open' | 'confirmed' | 'rejected' | 'watching' | string
  created_at: string
  updated_at: string
}

export type ViewId = 'dashboard' | 'bigscreen' | 'chat' | 'observability' | 'assets' | 'canvas' | 'cron' | 'alerts' | 'approvals' | 'skills' | 'tools' | 'knowledge' | 'config'

export interface ApprovalRequest {
  id: string
  tool_call_id: string
  session_id: string
  tool_name: string
  args: Record<string, unknown>
  metadata?: {
    tool_policy?: {
      name?: string
      label?: string
      toolset?: string
      safety_category?: string
      operation_mode?: 'read' | 'write' | 'read_write' | 'destructive' | 'external_effect' | 'interactive' | string
      destructive?: boolean
      concurrency_safe?: boolean
      approval_policy?: 'none' | 'guarded_write' | 'always_required' | string
      evidence_family?: string
      ui_renderer?: string
      result_store_policy?: 'evidence' | 'audit_only' | 'audit_and_evidence' | string
      timeout_policy?: {
        default_seconds?: number
        max_seconds?: number
        user_driven?: boolean
      }
      retry_policy?: {
        max_attempts?: number
        retry_on?: string[]
        delay_seconds?: number
      }
      runtime_scope?: string
      metadata_version?: number
    }
    policy?: {
      actions?: SafetyPolicyAction[]
      primary_action?: SafetyPolicyAction | null
    }
    requested_action?: {
      kind?: 'sql' | 'http' | 'command' | string
      label?: string
    }
    approval_sources?: Array<{
      layer?: string
      label?: string
      detail?: string
      reason?: string
    }>
    approval_source?: {
      layer?: string
      label?: string
      detail?: string
      reason?: string
    }
    skill_change?: {
      type: string
      skill_id: string
      file_name: string
      content_chars: number
      content_lines: number
      content_sha256: string
      content_preview: string
      validation?: SkillValidationResult
    }
    skill_rollback?: {
      type: string
      skill_id: string
      file_name: string
      version_id: string
      target_file?: string
      version_file?: string
    }
  }
  execution?: {
    status: 'success' | 'error' | string
    result_chars: number
    result_preview: string
    artifacts?: {
      skill_id?: string
      file_name?: string
      file_path?: string
      backup_path?: string | null
      version_id?: string
      restored_version_path?: string
    }
    metadata?: {
      type?: string
      statement_type?: string
      has_result_set?: boolean
      committed?: boolean
      affected_rows?: number
      count?: number
      message?: string
    }
    completed_at?: string
    completed_at_ts?: number
  }
  reason: string
  context: {
    host?: string
    port?: number
    username?: string
    asset_type?: string
    protocol?: string
    remark?: string
    allow_modifications?: boolean
    target_scope?: string
    scope_value?: string
    tags?: string[]
  }
  status: 'pending' | 'approved' | 'rejected' | 'timeout'
  decision?: string | null
  operator?: string | null
  note?: string
  requested_at: string
  expires_at?: string
  resolved_at?: string | null
}

export interface ApprovalAuditSummary {
  total: number
  limit: number
  by_status: Record<string, number>
  by_tool: Record<string, number>
  by_layer: Record<string, number>
  by_risk: Record<string, number>
  recent: Array<{
    id?: string
    status?: string
    tool_name?: string
    session_id?: string
    reason?: string
    requested_at?: string
    resolved_at?: string | null
  }>
}

export interface LLMPreset {
  name: string
  base_url: string
  api_key_placeholder: string
}

export interface SafetyPolicyCategory {
  always_approval?: boolean
  approval_reason?: string
  approval_patterns?: string[]
  readonly_block_patterns?: string[]
  readonly_safe_roots?: string[]
  readonly_unknown_requires_approval?: boolean
  approval_commands?: string[]
  readonly_block_commands?: string[]
  approval_methods?: string[]
  readonly_block_methods?: string[]
  hard_block_substrings?: string[]
}

export interface SafetyPolicyRule {
  id: string
  name: string
  domain?: string
  platform?: string
  category?: string
  resource?: string
  action?: string
  decision: 'allow' | 'approval' | 'deny'
  description?: string
  enabled?: boolean
  scope?: {
    type: 'all' | 'tag' | 'asset_type' | 'asset_group' | 'environment' | 'asset' | string
    value?: string
  }
  sources?: string[]
  matchers: Array<{
    type: string
    value: string
  }>
}

export type SafetyPolicyDecision = 'allow' | 'approval' | 'deny'

export interface SafetyPolicyNetworkBoundary {
  enabled: boolean
  active_cidrs: string[]
  readonly_cidrs: string[]
  blocked_cidrs: string[]
  allowed_hosts: string[]
  blocked_hosts: string[]
  block_unknown_targets: boolean
}

export interface SafetyPolicy {
  version: number
  approval_timeout_seconds: number
  readwrite_chat_warning_enabled: boolean
  rules?: SafetyPolicyRule[]
  action_rules?: Record<string, Record<string, SafetyPolicyDecision>>
  network_boundary?: SafetyPolicyNetworkBoundary
  categories: Record<string, SafetyPolicyCategory>
}

export interface SafetyPolicyTestInput {
  tool_name: string
  command?: string
  sql?: string
  method?: string
  path?: string
  oid?: string
  body?: Record<string, unknown>
  allow_modifications?: boolean
  asset_type?: string
  protocol?: string
  trigger_source?: string
  host?: string
  tags?: string[]
}

export interface SafetyPolicyTestResult {
  decision: 'allow' | 'approval' | 'deny' | 'readonly_block' | string
  label: string
  mode: 'readonly' | 'readwrite' | string
  reason: string
  actions?: SafetyPolicyAction[]
  primary_action?: SafetyPolicyAction | null
  resolution_layer?: string
  policy_layers?: Array<{
    id: string
    label: string
    matched: boolean
    reason?: string
    priority?: number
  }>
  checks: Array<{
    name: string
    matched: boolean
    reason?: string
  }>
}

export interface AssetCleanupPlan {
  summary: {
    assets_scanned: number
    rows_to_update: number
    duplicate_groups: number
    duplicates_to_remove: number
  }
  changes: Array<{
    id: number
    remark: string
    before: Record<string, unknown>
    after: Record<string, unknown>
  }>
  duplicates: Array<{
    keep_id: number
    remove_ids: number[]
    host: string
    port: number
    asset_type: string
    protocol: string
    merged_tags: string[]
  }>
}
