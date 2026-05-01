import type { AlertEvent } from '@/types'
import { request } from './http'

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
