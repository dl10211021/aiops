import type { AssetProfile } from '@/types'
import { request } from './http'

export async function getSessionProfile(sessionId: string, options?: RequestInit) {
  return request<{ profile: AssetProfile | null }>(`/session/${sessionId}/profile`, options)
}

export async function generateSessionProfile(sessionId: string, modelName?: string, includeInspection = true) {
  return request<{ profile: AssetProfile }>(`/session/${sessionId}/profile/generate`, {
    method: 'POST',
    body: JSON.stringify({ model_name: modelName || undefined, include_inspection: includeInspection }),
  })
}
