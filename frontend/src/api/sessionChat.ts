import type { ApiResponse } from '@/types'
import { apiUrl, authHeaders, isRecord, request, responseErrorMessage } from './http'

export async function pollAllSessions() {
  return request<{ updates: Record<string, Array<{ role: string; content: string }>> }>(
    '/sessions/poll_all'
  )
}

export function streamChat(
  sessionId: string,
  message: string,
  modelName: string,
  thinkingMode: string = 'off',
  orchestrationMode: 'single' | 'split' | 'fast' = 'single',
  displayMessage?: string,
  attachments: Array<{
    filename: string
    ext: string
    size: number
    content_type?: string
    kind?: string
    rows?: number
    pages?: number
    sheets?: string[]
    truncated?: boolean
    data_url?: string | null
  }> = [],
  signal?: AbortSignal,
  analysisOnly = false,
) {
  return fetch(apiUrl('/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ session_id: sessionId, message, display_message: displayMessage || message, model_name: modelName, thinking_mode: thinkingMode, orchestration_mode: orchestrationMode, attachments, analysis_only: analysisOnly }),
    signal,
  })
}

export function resumeChatStream(sessionId: string, signal?: AbortSignal, fromIndex = 0) {
  const params = new URLSearchParams()
  if (fromIndex > 0) params.set('from_index', String(fromIndex))
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return fetch(apiUrl(`/session/${encodeURIComponent(sessionId)}/chat/stream${suffix}`), {
    method: 'GET',
    headers: authHeaders(),
    signal,
  })
}

export async function stopChat(sessionId: string) {
  return request(`/session/${sessionId}/stop`, { method: 'POST' })
}

export async function approveToolCall(
  sessionId: string,
  toolCallId: string,
  approved: boolean,
  autoApproveAll = false,
  operator = 'user',
  note = '',
) {
  return request(`/session/${sessionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({
      tool_call_id: toolCallId,
      approved,
      auto_approve_all: autoApproveAll,
      operator,
      note,
    }),
  })
}

export async function previewChatAttachment(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(apiUrl('/chat/attachments/preview'), {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(responseErrorMessage(payload, res.statusText))
  }
  if (isRecord(payload) && payload.status === 'error') {
    throw new Error(responseErrorMessage(payload, '附件解析失败'))
  }
  return payload as ApiResponse<{
    attachment: {
      filename: string
      ext: string
      size: number
      content_type: string
      text: string
      truncated: boolean
      rows?: number
      sheets?: string[]
      pages?: number
      kind?: string
      data_url?: string | null
    }
  }>
}

export async function respondUserInteraction(
  sessionId: string,
  requestId: string,
  value: string,
  label = '',
) {
  return request(`/session/${sessionId}/interaction`, {
    method: 'POST',
    body: JSON.stringify({
      request_id: requestId,
      value,
      label,
    }),
  })
}
