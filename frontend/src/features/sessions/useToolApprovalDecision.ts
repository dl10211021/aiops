import { useState } from 'react'
import { approveToolCall } from '@/api/client'
import { useStore } from '@/store'
import type { ChatMessage, ToolApproval } from '@/types'
import { isAutoApproveConfirmationValid } from './approvalConfirmation'
import type { ChatApprovalDecision } from './approvalTypes'
import { findApprovalMessageId } from './chatAttention'

export function useToolApprovalDecision(currentSessionId: string | null, messages: ChatMessage[]) {
  const updateMessage = useStore((state) => state.updateMessage)
  const updateLastAssistantMessage = useStore((state) => state.updateLastAssistantMessage)
  const addToast = useStore((state) => state.addToast)
  const [decision, setDecision] = useState<ChatApprovalDecision | null>(null)

  const openDecision = (approval: ToolApproval, approved: boolean, autoAll = false) => {
    if (!currentSessionId) return
    const messageId = findApprovalMessageId(messages, approval.uniqueId)
    setDecision({
      sessionId: currentSessionId,
      toolCallId: approval.toolCallId,
      messageId,
      approval,
      approved,
      autoAll,
      operator: localStorage.getItem('OPSCORE_OPERATOR') || 'user',
      note: autoAll ? '本会话后续同类工具调用由人工确认全部放行' : '',
      confirmation: '',
      busy: false,
    })
  }

  const closeDecision = () => {
    setDecision(null)
  }

  const submitDecision = async () => {
    if (!decision) return
    const { sessionId, toolCallId, approved, autoAll, operator, note, confirmation } = decision
    if (!operator.trim()) {
      addToast('操作人不能为空', 'error')
      return
    }
    if (autoAll && !isAutoApproveConfirmationValid(confirmation)) {
      addToast('请输入“全部批准”确认本会话自动放行', 'error')
      return
    }
    if (approved && !note.trim()) {
      addToast('批准敏感操作必须填写原因', 'error')
      return
    }
    setDecision((current) => current ? { ...current, busy: true } : current)
    localStorage.setItem('OPSCORE_OPERATOR', operator.trim())
    try {
      await approveToolCall(sessionId, toolCallId, approved, autoAll, operator.trim(), note.trim())
      const resolvedDecision: ToolApproval['decision'] = approved ? 'approved' : 'rejected'
      const updater = (message: ChatMessage) => ({
        ...message,
        toolApproval: message.toolApproval ? {
          ...message.toolApproval,
          resolved: true,
          decision: resolvedDecision,
          operator: operator.trim(),
          note: note.trim(),
          autoAll,
          decidedAt: Date.now(),
        } : undefined,
      })
      if (decision.messageId) updateMessage(sessionId, decision.messageId, updater)
      else updateLastAssistantMessage(sessionId, updater)
      setDecision(null)
    } catch {
      addToast('审批提交失败', 'error')
      setDecision((current) => current ? { ...current, busy: false } : current)
    }
  }

  return {
    closeDecision,
    decision,
    openDecision,
    setDecision,
    submitDecision,
  }
}
