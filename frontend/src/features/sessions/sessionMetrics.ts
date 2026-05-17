import type { Session } from '@/types'
import { sessionAttention } from './sessionAttention'

export interface SessionMetrics {
  total: number
  readonly: number
  readwrite: number
  running: number
  pendingApproval: number
  pendingInput: number
  needsAttention: number
}

export function summarizeSessions(sessions: Session[]): SessionMetrics {
  const metrics: SessionMetrics = {
    total: sessions.length,
    readonly: 0,
    readwrite: 0,
    running: 0,
    pendingApproval: 0,
    pendingInput: 0,
    needsAttention: 0,
  }

  for (const session of sessions) {
    if (session.isReadWriteMode) metrics.readwrite += 1
    else metrics.readonly += 1
    if (isSessionRunning(session)) metrics.running += 1
    const attention = sessionAttention(session)
    if (attention.type === 'approval') metrics.pendingApproval += 1
    if (attention.type === 'input') metrics.pendingInput += 1
    if (attention.type !== 'none') metrics.needsAttention += 1
  }

  return metrics
}

export function isSessionRunning(session: Session): boolean {
  if (session.isStreaming || session.backendStreaming) return true
  return session.messages.slice(-3).some((message) =>
    (message.execTrace || []).some((trace) => trace.status === 'running'),
  )
}
