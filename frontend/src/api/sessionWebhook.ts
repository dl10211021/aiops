import { request } from './http'

export type SessionWebhookPayloadType = 'profile' | 'summary' | 'markdown'
export type SessionWebhookChannel = 'generic' | 'wechat' | 'dingtalk'

export type SessionWebhookParams = {
  webhook_url: string
  payload_type: SessionWebhookPayloadType
  channel: SessionWebhookChannel
  title?: string
  model_name?: string
  allow_private_targets?: boolean
}

export async function sendSessionWebhook(sessionId: string, params: SessionWebhookParams) {
  return request<{ http_status: number; response_preview: string }>(`/session/${sessionId}/webhook/send`, {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function previewSessionWebhook(sessionId: string, params: SessionWebhookParams) {
  return request<{
    target: { host: string; port: number; resolved_ips: string[]; private_target: boolean }
    payload_type: string
    channel: string
    title: string
    payload: { bytes: number; preview: string; truncated: boolean }
  }>(`/session/${sessionId}/webhook/preview`, {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function getSessionWebhookHistory(sessionId: string, limit = 10) {
  return request<{ deliveries: Array<{
    id: number
    session_id: string
    webhook_host: string
    channel: string
    payload_type: string
    title: string
    status: string
    http_status?: number | null
    response_preview?: string
    error?: string
    created_at: string
  }> }>(`/session/${sessionId}/webhook/history?limit=${encodeURIComponent(String(limit))}`)
}
