import type { Session } from '@/types'

const SESSION_ATTENTION_SCAN_LIMIT = 120

export type SessionAttention = {
  type: 'approval' | 'input' | 'none'
  label: string
}

export function sessionAttention(session: Session): SessionAttention {
  const minIndex = Math.max(0, session.messages.length - SESSION_ATTENTION_SCAN_LIMIT)
  for (let index = session.messages.length - 1; index >= minIndex; index -= 1) {
    const message = session.messages[index]
    if (message.toolApproval && !message.toolApproval.resolved) {
      return { type: 'approval', label: '待审批' }
    }
    if (message.userInteraction && !message.userInteraction.resolved) {
      return { type: 'input', label: '待输入' }
    }
  }
  return { type: 'none', label: '' }
}
