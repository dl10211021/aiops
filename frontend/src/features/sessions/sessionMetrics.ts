import type { Session } from '@/types'
import { sessionAttention } from './sessionAttention'

export interface SessionMetrics {
  total: number
  running: number
  pendingApproval: number
  pendingInput: number
  needsAttention: number
}

export function summarizeSessions(sessions: Session[]): SessionMetrics {
  const metrics: SessionMetrics = {
    total: sessions.length,
    running: 0,
    pendingApproval: 0,
    pendingInput: 0,
    needsAttention: 0,
  }

  for (const session of sessions) {
    if (session.isStreaming) metrics.running += 1
    const attention = sessionAttention(session)
    if (attention.type === 'approval') metrics.pendingApproval += 1
    if (attention.type === 'input') metrics.pendingInput += 1
    if (attention.type !== 'none') metrics.needsAttention += 1
  }

  return metrics
}
