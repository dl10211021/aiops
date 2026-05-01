import type { ChatMessage } from '@/types'

export function hasMeaningfulAssistantPayload(msg: ChatMessage): boolean {
  if (msg.role !== 'assistant') return true
  if (msg.content.trim().length > 0) return true
  if (msg.toolApproval || msg.userInteraction) return true
  return (msg.execTrace || []).some((trace) => {
    if (trace.status || trace.startedAt || trace.completedAt) return true
    if ((trace.args || '').trim().length > 0) return true
    if ((trace.result || '').trim().length > 0) return true
    if (trace.resultMeta && Object.keys(trace.resultMeta).length > 0) return true
    return false
  })
}
