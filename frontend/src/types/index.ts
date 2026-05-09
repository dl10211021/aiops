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
  // For tool execution traces
  execTrace?: ExecTraceItem[]
  // For tool approval requests
  toolApproval?: ToolApproval
  // For model-initiated user input or option selection
  userInteraction?: UserInteractionRequest
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
  tool: string
  args?: string
  result?: string
  resultMeta?: Record<string, unknown>
  status?: 'running' | 'done' | 'error'
  startedAt?: number
  completedAt?: number
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
  reason?: string
  actions?: SafetyPolicyAction[]
  primaryAction?: SafetyPolicyAction | null
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
  layer_counts: Record<string, number>
}

export interface ObservabilityProfile {
  system: ObservabilityBusinessSystem
  components: ObservabilityComponent[]
  relationships: ObservabilityRelationship[]
  observable_sources: ObservabilitySource[]
  unknowns: ObservabilityComponent[]
}

export type ViewId = 'dashboard' | 'bigscreen' | 'chat' | 'observability' | 'assets' | 'canvas' | 'cron' | 'alerts' | 'approvals' | 'skills' | 'knowledge' | 'config'

export interface ApprovalRequest {
  id: string
  tool_call_id: string
  session_id: string
  tool_name: string
  args: Record<string, unknown>
  metadata?: {
    policy?: {
      actions?: SafetyPolicyAction[]
      primary_action?: SafetyPolicyAction | null
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
