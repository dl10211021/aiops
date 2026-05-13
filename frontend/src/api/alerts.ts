import type { AlertEvent } from '@/types'
import { request } from './http'

export async function getAlertEvents(params: {
  status?: string
  severity?: string
  host?: string
  source_family?: string
  automation_mode?: string
  limit?: number
} = {}) {
  const search = new URLSearchParams()
  if (params.status && params.status !== 'all') search.set('status', params.status)
  if (params.severity && params.severity !== 'all') search.set('severity', params.severity)
  if (params.host) search.set('host', params.host)
  if (params.source_family && params.source_family !== 'all') search.set('source_family', params.source_family)
  if (params.automation_mode && params.automation_mode !== 'all') search.set('automation_mode', params.automation_mode)
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

export async function sendAlertWebhook(payload: Record<string, unknown>) {
  return request<{ alert: AlertEvent | null; alerts?: AlertEvent[]; injected_count: number }>('/webhook/alert', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
