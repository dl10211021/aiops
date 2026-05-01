import { request } from './http'

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
