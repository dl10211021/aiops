import { request } from './http'
import type { ExecTraceItem, MemoryReference, SessionMemoryActivity } from '@/types'

interface SessionHistoryApiMessage {
  role: string
  content: string
  _memory_id?: number
  feedback?: {
    rating: 'up' | 'down'
    note?: string
    created_at?: string
    memory_policy?: string
    memory_path?: string
  }
  exec_trace?: ExecTraceItem[]
  execTrace?: ExecTraceItem[]
  memory_refs?: MemoryReference[]
  memoryRefs?: MemoryReference[]
  timestamp?: number | string
  created_at?: string
  attachments?: Array<{
    filename: string
    ext?: string
    size: number
    kind?: string
    rows?: number
    pages?: number
    sheets?: string[]
    truncated?: boolean
  }>
}

export async function getSessionHistory(sessionId: string, limit?: number, options?: RequestInit) {
  const query = limit && limit > 0 ? `?limit=${encodeURIComponent(String(limit))}` : ''
  return request<{ messages: SessionHistoryApiMessage[] }>(
    `/session/${sessionId}/history${query}`,
    options,
  )
}

export async function updateSessionHistoryMessage(sessionId: string, messageId: number, content: string) {
  return request<{ message: { role: string; content: string; _memory_id?: number; feedback?: SessionHistoryApiMessage['feedback'] } }>(
    `/session/${sessionId}/history/${messageId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    },
  )
}

export async function feedbackSessionHistoryMessage(
  sessionId: string,
  messageId: number,
  rating: 'up' | 'down',
  note?: string,
) {
  return request<{ message: { role: string; content: string; _memory_id?: number; feedback?: SessionHistoryApiMessage['feedback'] } }>(
    `/session/${sessionId}/history/${messageId}/feedback`,
    {
      method: 'POST',
      body: JSON.stringify({ rating, note: note || null }),
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

export async function getSessionMemoryActivity(sessionId: string, options?: RequestInit) {
  return request<{ activity: SessionMemoryActivity }>(
    `/session/${sessionId}/memory/activity`,
    options,
  )
}
