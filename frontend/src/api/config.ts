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

export async function getAssistantModelConfig() {
  return request<{ config: AssistantModelConfig }>('/config/assistant-model')
}

export async function updateAssistantModelConfig(config: AssistantModelConfig) {
  return request<{ config: AssistantModelConfig }>('/config/assistant-model', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}
