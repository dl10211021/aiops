import { request } from './http'
import type {
  ExecTraceItem,
  MemoryReference,
  RunTraceAuditSummary,
  RunTraceEvent,
  RunTraceRun,
  SessionMemoryActivity,
  SessionRunLearningCandidateResult,
  SessionRunLearningPreview,
} from '@/types'

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

export async function getSessionHistoryEvidenceTrace(
  sessionId: string,
  params: {
    evidenceId?: string
    toolCallId?: string
    tool?: string
    limit?: number
  },
  options?: RequestInit,
) {
  const search = new URLSearchParams()
  if (params.evidenceId) search.set('evidence_id', params.evidenceId)
  if (params.toolCallId) search.set('tool_call_id', params.toolCallId)
  if (params.tool) search.set('tool', params.tool)
  search.set('limit', String(params.limit || 200))
  return request<{ trace: ExecTraceItem; message?: { id?: string | number; role?: string; created_at?: string | number; preview?: string } }>(
    `/session/${sessionId}/history/evidence?${search.toString()}`,
    options,
)
}

type SessionRunTraceRequestOptions = RequestInit & { runId?: string }

export async function getSessionRunTrace(sessionId: string, limit = 120, options?: SessionRunTraceRequestOptions) {
  const { runId, ...requestOptions } = options || {}
  const search = new URLSearchParams()
  search.set('limit', String(limit))
  if (runId) search.set('run_id', runId)
  return request<{ events: RunTraceEvent[]; runs?: RunTraceRun[] }>(
    `/session/${sessionId}/history/run-trace?${search.toString()}`,
    requestOptions,
  )
}

export async function getSessionRunTraceAuditSummary(sessionId: string, limit = 120, options?: SessionRunTraceRequestOptions) {
  const { runId, ...requestOptions } = options || {}
  const search = new URLSearchParams()
  search.set('limit', String(limit))
  if (runId) search.set('run_id', runId)
  return request<{ summary: RunTraceAuditSummary }>(
    `/session/${sessionId}/history/run-trace/audit-summary?${search.toString()}`,
    requestOptions,
  )
}

export async function getSessionRunLearningPreview(sessionId: string, limit = 200, options?: SessionRunTraceRequestOptions) {
  const { runId, ...requestOptions } = options || {}
  const search = new URLSearchParams()
  search.set('limit', String(limit))
  if (runId) search.set('run_id', runId)
  return request<{ preview: SessionRunLearningPreview }>(
    `/session/${sessionId}/history/run-trace/learning-preview?${search.toString()}`,
    requestOptions,
  )
}

export async function createSessionRunLearningCandidate(
  sessionId: string,
  params: { runId?: string; actor?: string; reason?: string },
) {
  return request<SessionRunLearningCandidateResult>(
    `/session/${sessionId}/history/run-trace/learning-candidate`,
    {
      method: 'POST',
      body: JSON.stringify({
        run_id: params.runId || null,
        actor: params.actor || 'user',
        reason: params.reason || '人工提交 Run Trace 学习候选',
      }),
    },
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
