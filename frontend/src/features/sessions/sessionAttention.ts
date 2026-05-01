import type { Session } from '@/types'

export type SessionAttention = {
  type: 'approval' | 'input' | 'none'
  label: string
}

export function sessionAttention(session: Session): SessionAttention {
  for (let index = session.messages.length - 1; index >= 0; index -= 1) {
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
