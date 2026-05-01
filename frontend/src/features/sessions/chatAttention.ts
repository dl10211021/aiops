import type { ChatMessage } from '@/types'
import { parseJsonRecord } from './jsonRecords'
import {
  extractPrimaryAction,
  isPolicyBlockedResult,
  resultReason,
} from './traceUtils'

export function findApprovalMessageId(messages: ChatMessage[], uniqueId: string) {
  return messages.find((msg) => msg.toolApproval?.uniqueId === uniqueId)?.id
}

export function findInteractionMessageId(messages: ChatMessage[], requestId: string) {
  return messages.find((msg) => msg.userInteraction?.requestId === requestId)?.id
}

export function findPendingAttention(messages: ChatMessage[]) {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message.toolApproval && !message.toolApproval.resolved) {
      return { type: 'approval' as const, messageId: message.id, approval: message.toolApproval }
    }
    if (message.userInteraction && !message.userInteraction.resolved) {
      return { type: 'interaction' as const, messageId: message.id, interaction: message.userInteraction }
    }
  }
  return null
}

export function findLatestPolicyBlock(messages: ChatMessage[]) {
  let lastUserIndex = -1
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') {
      lastUserIndex = i
      break
    }
  }

  for (let i = messages.length - 1; i > lastUserIndex; i--) {
    const message = messages[i]
    const traces = message.execTrace || []
    for (let j = traces.length - 1; j >= 0; j--) {
      const trace = traces[j]
      const result = trace.resultMeta || parseJsonRecord(trace.result || '')
      if (!isPolicyBlockedResult(result)) continue
      const action = extractPrimaryAction(result)
      if (!action) continue
      return {
        messageId: message.id,
        traceIndex: j,
        trace,
        result,
        action,
      }
    }
  }
  return null
}

export type LatestPolicyBlock = NonNullable<ReturnType<typeof findLatestPolicyBlock>>
export type PendingAttention = NonNullable<ReturnType<typeof findPendingAttention>>

export function policyBlockKey(item: LatestPolicyBlock) {
  return [
    item.messageId,
    item.traceIndex,
    item.trace.tool || 'unknown',
    item.action.id,
    String(item.result?.policy_decision || ''),
    resultReason(item.result),
  ].join('|')
}

export function resolveApprovalFromToolEnd(message: ChatMessage, data: Record<string, unknown>): ChatMessage {
  const approval = message.toolApproval
  if (!approval || approval.resolved || approval.toolCallId !== String(data.id || '')) return message
  const resultMeta = data.result_meta && typeof data.result_meta === 'object' && !Array.isArray(data.result_meta)
    ? data.result_meta as Record<string, unknown>
    : parseJsonRecord(String(data.result || ''))
  const errorType = String(resultMeta?.error_type || '')
  if (errorType !== 'approval_timeout' && errorType !== 'approval_rejected') return message
  const timedOut = errorType === 'approval_timeout'
  return {
    ...message,
    toolApproval: {
      ...approval,
      resolved: true,
      decision: timedOut ? 'timeout' : 'rejected',
      operator: timedOut ? 'system' : approval.operator,
      note: timedOut ? '审批超时，系统已取消本次工具调用。' : (approval.note || '工具调用已被拒绝。'),
      decidedAt: Date.now(),
    },
  }
}
