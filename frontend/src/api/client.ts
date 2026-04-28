// API service layer for all OpsCore backend endpoints
import type {
  AlertTrendPoint,
  ApiResponse,
  ApprovalRequest,
  AlertEvent,
  Asset,
  AssetVerificationRun,
  AssetCleanupPlan,
  CronJob,
  DashboardOverview,
  InspectionReport,
  InspectionRun,
  InspectionTrendPoint,
  InspectionTemplate,
  KnowledgeFile,
  ProtocolVerificationOverview,
  RiskRankingItem,
  SafetyPolicy,
  SessionToolCatalog,
  SkillInfo,
  SkillValidationResult,
} from '@/types'

const BASE = '/api/v1'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('OPSCORE_API_TOKEN')
  return token ? { 'X-API-Key': token } : {}
}

async function request<T = Record<string, unknown>>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || res.statusText)
  }
  return res.json()
}

// ---- Sessions ----
export async function connectSession(params: {
  host: string; port: number; username: string; password?: string;
  private_key_path?: string; allow_modifications: boolean;
  active_skills: string[]; agent_profile: string; remark?: string;
  asset_type: string; protocol?: string; extra_args: Record<string, unknown>; group_name?: string;
  tags?: string[]; target_scope?: string; scope_value?: string;
}) {
  return request<{ session_id: string }>('/connect', {
    method: 'POST', body: JSON.stringify(params),
  })
}

export async function testConnection(params: {
  host: string; port: number; username: string; password?: string;
  asset_type: string; protocol?: string; extra_args?: Record<string, unknown>;
  active_skills?: string[];
  target_scope?: string; scope_value?: string;
}) {
  return request('/connect/test', {
    method: 'POST', body: JSON.stringify(params),
  })
}

export async function inspectConnection(params: {
  host: string; port: number; username: string; password?: string;
  asset_type: string; protocol?: string; extra_args?: Record<string, unknown>;
  active_skills?: string[]; agent_profile?: string; remark?: string;
  tags?: string[]; target_scope?: string; scope_value?: string;
  keep_session?: boolean;
}) {
  return request<{ inspection: {
    status: string; supported: boolean; summary?: string; message?: string;
    checks: Array<{ title: string; status: string; output: string }>;
  } }>('/connect/inspect', {
    method: 'POST', body: JSON.stringify(params),
  })
}

export async function disconnectSession(sessionId: string) {
  return request(`/disconnect/${sessionId}`, { method: 'DELETE' })
}

export async function getActiveSessions() {
  return request<{ sessions: Record<string, {
    id: string; host: string; remark: string; isReadWriteMode: boolean;
    skills: string[]; agentProfile: string; user: string;
    asset_type: string; protocol: string; extra_args: Record<string, unknown>;
    heartbeatEnabled: boolean; tags: string[];
    target_scope?: string; scope_value?: string | null;
  }> }>('/sessions/active')
}

export async function pollAllSessions() {
  return request<{ updates: Record<string, Array<{ role: string; content: string }>> }>(
    '/sessions/poll_all'
  )
}

// ---- Chat (SSE) ----
export function streamChat(
  sessionId: string, message: string, modelName: string,
  thinkingMode: string = 'off',
  signal?: AbortSignal
) {
  return fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ session_id: sessionId, message, model_name: modelName, thinking_mode: thinkingMode }),
    signal,
  })
}

export async function stopChat(sessionId: string) {
  return request(`/session/${sessionId}/stop`, { method: 'POST' })
}

export async function approveToolCall(sessionId: string, toolCallId: string, approved: boolean, autoApproveAll = false) {
  return request(`/session/${sessionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ tool_call_id: toolCallId, approved, auto_approve_all: autoApproveAll }),
  })
}

// ---- Session Settings ----
export async function updatePermission(sessionId: string, allowModifications: boolean) {
  return request(`/session/${sessionId}/permission`, {
    method: 'PUT', body: JSON.stringify({ allow_modifications: allowModifications }),
  })
}

export async function updateHeartbeat(sessionId: string, enabled: boolean, masterInterval?: number) {
  return request(`/session/${sessionId}/heartbeat`, {
    method: 'PUT', body: JSON.stringify({ heartbeat_enabled: enabled, master_interval: masterInterval }),
  })
}

export async function updateSessionSkills(sessionId: string, skills: string[]) {
  return request(`/session/${sessionId}/skills`, {
    method: 'PUT', body: JSON.stringify({ active_skills: skills }),
  })
}

export async function getSessionHistory(sessionId: string) {
  return request<{ messages: Array<{ role: string; content: string }> }>(
    `/session/${sessionId}/history`
  )
}

export async function clearSessionHistory(sessionId: string) {
  return request(`/session/${sessionId}/history`, { method: 'DELETE' })
}

export async function exportSessionHistory(sessionId: string) {
  return request<{ markdown: string }>(`/session/${sessionId}/export`)
}

export async function getSessionTools(sessionId: string) {
  return request<SessionToolCatalog>(`/session/${sessionId}/tools`)
}

// ---- Skills ----
export async function getSkillRegistry() {
  return request<{ registry: SkillInfo[] }>('/skills/registry')
}

export async function getSkillDetail(skillId: string) {
  return request<{ instructions: string; source_path: string }>(
    `/skills/registry/${skillId}`
  )
}

export async function scanSkills() {
  return request('/skills/scan', { method: 'POST' })
}

export async function migrateSkill(sourcePath: string, targetDirName: string) {
  return request('/skills/migrate', {
    method: 'POST',
    body: JSON.stringify({ source_path: sourcePath, target_dir_name: targetDirName }),
  })
}

export async function createSkill(params: {
  skill_id: string; description: string; instructions: string;
  script_name?: string; script_content?: string; overwrite_existing?: boolean;
}) {
  return request('/skills/create', { method: 'POST', body: JSON.stringify(params) })
}

export async function validateSkill(params: {
  skill_id: string; file_name?: string; content: string;
}) {
  return request<SkillValidationResult>('/skills/validate', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

// ---- Assets ----
export async function getSavedAssets() {
  return request<{ assets: Asset[] }>('/assets/saved')
}

export async function deleteAsset(assetId: number) {
  return request(`/assets/${assetId}`, { method: 'DELETE' })
}

export async function createAsset(asset: Partial<Asset>) {
  return request('/assets', {
    method: 'POST', body: JSON.stringify(asset),
  })
}

export async function getAsset(assetId: number) {
  return request<{ asset: Asset }>(`/assets/${assetId}`)
}

export async function getAssetVerificationMatrix(assetId: number) {
  return request<{ matrix: ProtocolVerificationOverview['matrix'][number] }>(`/assets/${assetId}/verification`)
}

export async function verifyAsset(assetId: number) {
  return request<{ run: AssetVerificationRun }>(`/assets/${assetId}/verify`, { method: 'POST' })
}

export async function getAssetVerificationRuns(assetId: number, limit = 20) {
  return request<{ runs: AssetVerificationRun[] }>(`/assets/${assetId}/verification/runs?limit=${limit}`)
}

export async function getProtocolVerificationOverview() {
  return request<ProtocolVerificationOverview>('/verification/protocols')
}

export async function updateAsset(assetId: number, asset: Partial<Asset>) {
  return request<{ asset: Asset }>(`/assets/${assetId}`, {
    method: 'PUT', body: JSON.stringify(asset),
  })
}

export async function batchImportAssets(items: Partial<Asset>[]) {
  return request('/assets/batch_import', {
    method: 'POST', body: JSON.stringify(items),
  })
}

export async function previewAssetNormalization() {
  return request<AssetCleanupPlan>('/assets/normalize/preview')
}

export async function applyAssetNormalization() {
  return request<{
    backup_path: string
    removed_ids: number[]
    merged_groups: Array<{ keep_id: number; remove_ids: number[]; host: string; port: number }>
    summary: Record<string, unknown>
  }>('/assets/normalize/apply', { method: 'POST' })
}

// ---- Knowledge Base ----
export async function listKnowledgeDocuments() {
  return request<{ files: KnowledgeFile[] }>('/knowledge/list')
}

export async function uploadKnowledgeDocument(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${BASE}/knowledge/upload`, { method: 'POST', body: fd, headers: authHeaders() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json() as Promise<ApiResponse>
}

export async function deleteKnowledgeDocument(filename: string) {
  return request(`/knowledge/${encodeURIComponent(filename)}`, { method: 'DELETE' })
}

// ---- Cron ----
export async function getCronJobs() {
  return request<{ jobs: CronJob[] }>('/cron/list')
}

export async function addCronJob(params: {
  cron_expr: string; message: string; host: string;
  username: string; agent_profile?: string; password?: string;
  asset_id?: number | null; target_scope?: string; scope_value?: string;
  template_id?: string; notification_channel?: string; retry_count?: number;
  active_skills?: string[];
}) {
  return request('/cron/add', { method: 'POST', body: JSON.stringify(params) })
}

export async function updateCronJob(jobId: string, params: {
  cron_expr: string; message: string; host: string;
  username: string; agent_profile?: string; password?: string;
  asset_id?: number | null; target_scope?: string; scope_value?: string;
  template_id?: string; notification_channel?: string; retry_count?: number;
  active_skills?: string[];
}) {
  return request<{ job: CronJob }>(`/cron/${jobId}`, { method: 'PUT', body: JSON.stringify(params) })
}

export async function pauseCronJob(jobId: string) {
  return request<{ job: CronJob }>(`/cron/${jobId}/pause`, { method: 'POST' })
}

export async function resumeCronJob(jobId: string) {
  return request<{ job: CronJob }>(`/cron/${jobId}/resume`, { method: 'POST' })
}

export async function runCronJobNow(jobId: string) {
  return request<{ result: { status: string; job_id: string; run_id: string; target_count: number } }>(`/cron/${jobId}/run`, { method: 'POST' })
}

export async function deleteCronJob(jobId: string) {
  return request(`/cron/${jobId}`, { method: 'DELETE' })
}

export async function getCronJobRuns(jobId: string, limit = 5) {
  return request<{ runs: InspectionRun[] }>(`/cron/${jobId}/runs?limit=${limit}`)
}

export async function getCronJobRun(runId: string) {
  return request<{ run: InspectionRun }>(`/cron/runs/${runId}`)
}

export async function listInspectionRuns(params: { jobId?: string; assetId?: number; limit?: number } = {}) {
  const search = new URLSearchParams()
  if (params.jobId) search.set('job_id', params.jobId)
  if (params.assetId) search.set('asset_id', String(params.assetId))
  if (params.limit) search.set('limit', String(params.limit))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return request<{ runs: InspectionRun[] }>(`/inspection-runs${suffix}`)
}

export async function getInspectionRunReport(runId: string) {
  return request<{ report: InspectionReport }>(`/inspection-runs/${runId}/report`)
}

export async function exportInspectionRunReport(runId: string, format: 'markdown' | 'json' = 'markdown') {
  return request<{ format: string; content_type: string; content: string }>(
    `/inspection-runs/${runId}/export?format=${format}`
  )
}

export async function getDashboardInspectionRunTrend() {
  return request<{ points: InspectionTrendPoint[] }>('/dashboard/inspection-runs/trend')
}

// ---- Inspection Templates ----
export async function getInspectionTemplates() {
  return request<{ templates: InspectionTemplate[] }>('/inspection-templates')
}

export async function createInspectionTemplate(template: InspectionTemplate) {
  return request<{ template: InspectionTemplate }>('/inspection-templates', {
    method: 'POST',
    body: JSON.stringify(template),
  })
}

export async function updateInspectionTemplate(templateId: string, template: InspectionTemplate) {
  return request<{ template: InspectionTemplate }>(`/inspection-templates/${templateId}`, {
    method: 'PUT',
    body: JSON.stringify(template),
  })
}

export async function deleteInspectionTemplate(templateId: string) {
  return request(`/inspection-templates/${templateId}`, { method: 'DELETE' })
}

// ---- Config ----

export interface ProviderConfig {
  id: string;
  name: string;
  protocol: string;
  base_url: string;
  api_key: string;
  models: string;
}

export interface ModelGroup {
  provider_id: string;
  provider_name: string;
  models: { id: string; name: string }[];
}

export interface AssetTypeDefinition {
  id: string;
  label: string;
  category: string;
  protocol: string;
  default_port: number;
  inspection_profile?: string;
}

export interface AssetCategoryDefinition {
  id: string;
  label: string;
}

export async function getProviders() {
  return request<{ providers: ProviderConfig[] }>('/config/providers')
}

export async function updateProviders(providers: ProviderConfig[]) {
  return request('/config/providers', {
    method: 'POST', body: JSON.stringify(providers),
  })
}

export async function getAvailableModels(providerId?: string, refresh = false) {
  const params = new URLSearchParams()
  if (providerId) params.set('provider_id', providerId)
  if (refresh) params.set('refresh', 'true')
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return request<{ models: ModelGroup[] }>(`/models${suffix}`)
}

export async function getAssetTypes() {
  return request<{ types: AssetTypeDefinition[]; categories: AssetCategoryDefinition[] }>('/assets/types')
}

export async function getToolCatalog() {
  return request<SessionToolCatalog>('/tools/catalog')
}

export async function getSessionCommands(sessionId: string) {
  return request<{ commands: Array<{ id: string; label: string; description: string; prompt: string; category: string }> }>(
    `/session/${sessionId}/commands`
  )
}

export async function getDashboardOverview() {
  return request<DashboardOverview>('/dashboard/overview')
}

export async function getDashboardAlertTrend() {
  return request<{ points: AlertTrendPoint[] }>('/dashboard/alerts/trend')
}

export async function getDashboardRiskRanking() {
  return request<{ ranking: RiskRankingItem[] }>('/dashboard/risk-ranking')
}

export async function getDashboardToolsets() {
  return request<SessionToolCatalog>('/dashboard/toolsets')
}

// ---- Alert Center ----
export async function getAlertEvents(params: {
  status?: string
  severity?: string
  host?: string
  limit?: number
} = {}) {
  const search = new URLSearchParams()
  if (params.status && params.status !== 'all') search.set('status', params.status)
  if (params.severity && params.severity !== 'all') search.set('severity', params.severity)
  if (params.host) search.set('host', params.host)
  search.set('limit', String(params.limit || 200))
  return request<{ alerts: AlertEvent[] }>(`/alerts?${search.toString()}`)
}

export async function getAlertEvent(alertId: string) {
  return request<{ alert: AlertEvent }>(`/alerts/${alertId}`)
}

export async function updateAlertEvent(
  alertId: string,
  params: { status?: string; assignee?: string; note?: string }
) {
  return request<{ alert: AlertEvent }>(`/alerts/${alertId}`, {
    method: 'PATCH',
    body: JSON.stringify(params),
  })
}


export async function getNotificationConfig() {
  return request<Record<string, unknown>>('/config/notifications')
}

export async function updateNotificationConfig(config: Record<string, unknown>) {
  return request('/config/notifications', {
    method: 'POST', body: JSON.stringify(config),
  })
}

export async function testNotificationChannel(channel: string) {
  return request('/config/notifications/test', {
    method: 'POST', body: JSON.stringify({ channel }),
  })
}

export async function getSafetyPolicy() {
  return request<{ policy: SafetyPolicy }>('/config/safety-policy')
}

export async function updateSafetyPolicy(policy: SafetyPolicy) {
  return request<{ policy: SafetyPolicy }>('/config/safety-policy', {
    method: 'POST', body: JSON.stringify({ policy }),
  })
}

// ---- Approval Center ----
export async function getApprovals(status?: string, limit = 100) {
  const params = new URLSearchParams()
  if (status && status !== 'all') params.set('status', status)
  params.set('limit', String(limit))
  return request<{ approvals: ApprovalRequest[] }>(`/approvals?${params.toString()}`)
}

export async function decideApproval(
  approvalId: string,
  approved: boolean,
  operator = 'ops-admin',
  note = ''
) {
  return request<{ approval: ApprovalRequest }>(`/approvals/${approvalId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ approved, operator, note }),
  })
}

export async function executeApproval(approvalId: string) {
  return request<{ approval: ApprovalRequest; result: Record<string, unknown> }>(
    `/approvals/${approvalId}/execute`,
    { method: 'POST' }
  )
}

// ---- Hydrate ----
export async function getHydrateStatus() {
  return request<{ total: number; done: number; success: number; running: boolean }>(
    '/hydrate/status'
  )
}
