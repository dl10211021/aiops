import type { SessionToolCatalog } from '@/types'
import { request } from './http'

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

export async function disconnectSession(sessionId: string) {
  return request(`/disconnect/${sessionId}`, { method: 'DELETE' })
}

export async function getActiveSessions() {
  return request<{ sessions: Record<string, {
    id: string; host: string; remark: string; isReadWriteMode: boolean;
    skills: string[]; agentProfile: string; user: string;
    asset_type: string; protocol: string; extra_args: Record<string, unknown>;
    heartbeatEnabled: boolean; tags: string[];
    group_name?: string;
    target_scope?: string; scope_value?: string | null;
    isStreaming?: boolean;
  }> }>('/sessions/active')
}

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

export async function updateSessionGroup(sessionId: string, groupName: string) {
  return request<{ session_id: string; tags: string[]; group_name: string }>(
    `/session/${sessionId}/group`,
    {
      method: 'PUT',
      body: JSON.stringify({ group_name: groupName }),
    },
  )
}

export async function updateSessionMetadata(
  sessionId: string,
  payload: { remark: string; group_name: string; tags: string[] },
) {
  return request<{ session_id: string; remark: string; tags: string[]; group_name: string }>(
    `/session/${sessionId}/metadata`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
  )
}

export async function getSessionTools(sessionId: string, options?: RequestInit) {
  return request<SessionToolCatalog>(`/session/${sessionId}/tools`, options)
}
