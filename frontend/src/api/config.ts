import { request } from './http'

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

export interface AgentRuntimeConfig {
  chat_max_steps: number
  headless_max_steps: number
  min_steps: number
  max_steps: number
  defaults: {
    chat_max_steps: number
    headless_max_steps: number
  }
  env_keys: {
    chat_max_steps: string
    headless_max_steps: string
  }
}

export interface SessionRetentionPreview {
  rows_scanned: number
  rows_compacted: number
  rows_deleted: number
  audit_rows_inserted?: number
  audit_rows_deleted?: number
  started_at?: string
  completed_at?: string
  duration_ms?: number
  status?: string
  dry_run?: boolean
  enabled?: boolean
  error?: string
}

export interface SessionRetentionStatus {
  last_run?: SessionRetentionPreview | null
  next_run_at?: string | null
  interval_seconds?: number | null
  error?: string
}

export interface SessionRetentionPolicyFields {
  enabled: boolean
  raw_result_days: number
  compressed_history_days: number
  audit_metadata_days: number
  max_result_chars: number
  preview_chars: number
}

export interface SessionRetentionConfig extends SessionRetentionPolicyFields {
  interval_seconds?: number
  defaults?: SessionRetentionPolicyFields
  env_keys?: Record<string, string>
  preview?: SessionRetentionPreview
  status?: SessionRetentionStatus
}

export interface AssistantModelConfig {
  main_model_id: string
  enabled: boolean
  model_id: string
  thinking_mode: 'off' | 'low' | 'medium' | 'high' | 'enabled' | string
  tasks: {
    memory_compression?: boolean
    trace_review?: boolean
    risk_advice?: boolean
    asset_profile_prompt?: boolean
    completion_check?: boolean
    [key: string]: boolean | undefined
  }
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

export async function getAgentRuntimeConfig() {
  return request<{ config: AgentRuntimeConfig }>('/config/agent-runtime')
}

export async function updateAgentRuntimeConfig(config: {
  chat_max_steps: number
  headless_max_steps: number
}) {
  return request<{ config: AgentRuntimeConfig }>('/config/agent-runtime', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export async function getSessionRetentionConfig(preview = true) {
  return request<{ config: SessionRetentionConfig }>(
    `/config/session-retention?preview=${preview ? 'true' : 'false'}`
  )
}

export async function updateSessionRetentionConfig(config: SessionRetentionConfig) {
  return request<{ config: SessionRetentionConfig }>('/config/session-retention', {
    method: 'POST',
    body: JSON.stringify({
      enabled: config.enabled,
      raw_result_days: config.raw_result_days,
      compressed_history_days: config.compressed_history_days,
      audit_metadata_days: config.audit_metadata_days,
      max_result_chars: config.max_result_chars,
      preview_chars: config.preview_chars,
    }),
  })
}

export async function runSessionRetentionNow() {
  return request<{ result: SessionRetentionPreview }>('/config/session-retention/run', {
    method: 'POST',
  })
}

export async function getAssistantModelConfig() {
  return request<{ config: AssistantModelConfig }>('/config/assistant-model')
}

export async function updateAssistantModelConfig(config: AssistantModelConfig) {
  return request<{ config: AssistantModelConfig }>('/config/assistant-model', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}
