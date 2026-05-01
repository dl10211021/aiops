import type { ToolApproval } from '@/types'

export interface ChatApprovalDecision {
  sessionId: string
  toolCallId: string
  messageId?: string
  approval: ToolApproval
  approved: boolean
  autoAll: boolean
  operator: string
  note: string
  confirmation: string
  busy: boolean
}
