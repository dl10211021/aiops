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
  // Frontend-only state
  messages: ChatMessage[]
  isStreaming: boolean
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  // For tool execution traces
  execTrace?: ExecTraceItem[]
  // For tool approval requests
  toolApproval?: ToolApproval
}

export interface ExecTraceItem {
  type: 'tool_start' | 'tool_end'
  tool: string
  args?: string
  result?: string
  status?: 'running' | 'done' | 'error'
  startedAt?: number
  completedAt?: number
}

export interface ToolApproval {
  toolCallId: string
  toolName: string
  args: string
  reason?: string
  uniqueId: string
  resolved: boolean
}

export interface ToolDefinition {
  name: string
  toolset: string
  scope: string
  description: string
  safety_category: string
  protocols: string[]
  asset_types: string[]
  requires_virtual: boolean
  enabled?: boolean
}

export interface ToolsetInfo {
  id: string
  enabled: boolean
  tools: ToolDefinition[]
}

export interface SessionToolCatalog {
  toolsets: ToolsetInfo[]
  active_tools?: string[]
  context?: {
    target_scope: string
    asset_type: string
    protocol: string
    host?: string
    port?: number
  }
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

export interface CronJob {
  id: string
  cron_expr: string
  message: string
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
}

export interface DashboardOverview {
  summary: Record<string, number>
  by_category: Record<string, number>
  by_protocol: Record<string, number>
  by_type: Record<string, number>
  active_by_protocol: Record<string, number>
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
  payload: Record<string, unknown>
  notes: AlertEventNote[]
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

export interface InspectionRun {
  id: string
  job_id: string
  status: 'completed' | 'failed' | 'partial' | 'empty' | string
  target_scope: string
  scope_value?: string | null
  message: string
  target_count: number
  targets: InspectionRunTarget[]
  started_at: string
  completed_at: string
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
  size?: number
  chunks?: number
}

export interface ApiResponse<T = Record<string, unknown>> {
  status: 'success' | 'error'
  data: T
  message: string
}

export type ViewId = 'dashboard' | 'bigscreen' | 'chat' | 'assets' | 'cron' | 'alerts' | 'approvals' | 'skills' | 'knowledge'

export interface ApprovalRequest {
  id: string
  tool_call_id: string
  session_id: string
  tool_name: string
  args: Record<string, unknown>
  metadata?: {
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

export interface SafetyPolicy {
  version: number
  approval_timeout_seconds: number
  readwrite_chat_warning_enabled: boolean
  categories: Record<string, SafetyPolicyCategory>
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
