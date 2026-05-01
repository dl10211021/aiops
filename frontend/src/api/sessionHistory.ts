import { request } from './http'

export async function getSessionHistory(sessionId: string) {
  return request<{ messages: Array<{ role: string; content: string; _memory_id?: number; attachments?: Array<{
    filename: string
    ext?: string
    size: number
    kind?: string
    rows?: number
    pages?: number
    sheets?: string[]
    truncated?: boolean
  }> }> }>(
    `/session/${sessionId}/history`
  )
}

export async function updateSessionHistoryMessage(sessionId: string, messageId: number, content: string) {
  return request<{ message: { role: string; content: string; _memory_id?: number } }>(
    `/session/${sessionId}/history/${messageId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    },
  )
}

export async function deleteSessionHistoryMessage(sessionId: string, messageId: number) {
  return request(`/session/${sessionId}/history/${messageId}`, { method: 'DELETE' })
}

export async function clearSessionHistory(sessionId: string) {
  return request(`/session/${sessionId}/history`, { method: 'DELETE' })
}

export async function exportSessionHistory(sessionId: string) {
  return request<{ markdown: string }>(`/session/${sessionId}/export`)
}
