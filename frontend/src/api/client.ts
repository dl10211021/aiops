// API service layer for all OpsCore backend endpoints
import type { ApiResponse, Asset, CronJob, KnowledgeFile, SkillInfo } from '@/types'

const BASE = '/api/v1'

async function request<T = Record<string, unknown>>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
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
  asset_type: string; extra_args: Record<string, unknown>; group_name?: string;
  tags?: string[]; target_scope?: string; scope_value?: string;
}) {
  return request<{ session_id: string }>('/connect', {
    method: 'POST', body: JSON.stringify(params),
  })
}

export async function testConnection(params: {
  host: string; port: number; username: string; password?: string;
  asset_type: string; extra_args?: Record<string, unknown>;
  active_skills?: string[];
  target_scope?: string; scope_value?: string;
}) {
  return request('/connect/test', {
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
    asset_type: string; extra_args: Record<string, unknown>;
    heartbeatEnabled: boolean; tags: string[];
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
    headers: { 'Content-Type': 'application/json' },
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
  script_name?: string; script_content?: string;
}) {
  return request('/skills/create', { method: 'POST', body: JSON.stringify(params) })
}

// ---- Assets ----
export async function getSavedAssets() {
  return request<{ assets: Asset[] }>('/assets/saved')
}

export async function deleteAsset(assetId: number) {
  return request(`/assets/${assetId}`, { method: 'DELETE' })
}

export async function batchImportAssets(items: Partial<Asset>[]) {
  return request('/assets/batch_import', {
    method: 'POST', body: JSON.stringify(items),
  })
}

// ---- Knowledge Base ----
export async function listKnowledgeDocuments() {
  return request<{ files: KnowledgeFile[] }>('/knowledge/list')
}

export async function uploadKnowledgeDocument(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${BASE}/knowledge/upload`, { method: 'POST', body: fd })
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
}) {
  return request('/cron/add', { method: 'POST', body: JSON.stringify(params) })
}

export async function deleteCronJob(jobId: string) {
  return request(`/cron/${jobId}`, { method: 'DELETE' })
}

// ---- Config ----
export async function getLLMConfig() {
  return request<{ base_url: string; api_key: string }>('/config/llm')
}

export async function updateLLMConfig(baseUrl: string, apiKey: string) {
  return request('/config/llm', {
    method: 'POST', body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
  })
}

export async function getAvailableModels() {
  return request<{ models: string[] }>('/models')
}

export async function getEmbeddingConfig() {
  return request<{ model: string; dim: number }>('/config/embedding')
}

export async function updateEmbeddingConfig(model: string, dim: number) {
  return request('/config/embedding', {
    method: 'POST', body: JSON.stringify({ model, dim }),
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

// ---- Hydrate ----
export async function getHydrateStatus() {
  return request<{ total: number; done: number; success: number; running: boolean }>(
    '/hydrate/status'
  )
}
