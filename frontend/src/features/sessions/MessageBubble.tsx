import { useState } from 'react'
import type { ChatMessage, SafetyPolicyAction, SafetyPolicyDecision, ToolApproval } from '@/types'
import { approvalArgumentRows } from './approvalRows'
import {
  AssistantReportBubble,
  SystemMessageBubble,
  TypingIndicatorBubble,
  UserMessageBubble,
} from './MessageBubbleParts'
import ToolApprovalCard from './ToolApprovalCard'
import ToolTraceList from './ToolTraceList'
import UserInteractionCard from './UserInteractionCard'

interface MessageBubbleProps {
  message: ChatMessage
  isPending?: boolean
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
  onInteraction: (requestId: string, value: string, label?: string) => void
  onTraceActionRule?: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
  onEdit?: (message: ChatMessage) => void
  onDelete?: (message: ChatMessage) => void
  showInlineTrace?: boolean
}

export default function MessageBubble({
  message,
  isPending = false,
  onApproval,
  onInteraction,
  onTraceActionRule,
  policyRuleBusy,
  onEdit,
  onDelete,
  showInlineTrace = true,
}: MessageBubbleProps) {
  const [traceOpen, setTraceOpen] = useState(false)

  if (message.role === 'user') {
    return (
      <UserMessageBubble message={message} onEdit={onEdit} onDelete={onDelete} />
    )
  }

  if (message.role === 'system') {
    return <SystemMessageBubble content={message.content} />
  }

  const hasTrace = message.execTrace && message.execTrace.length > 0
  const approval = message.toolApproval
  const approvalRows = approval ? approvalArgumentRows(approval) : []
  const approvalActions = approval?.actions || []
  const interaction = message.userInteraction
  const hasContent = message.content.trim().length > 0
  const shouldShowEmptyBubble = isPending && !hasContent && !hasTrace && !approval && !interaction
  if (!hasContent && !hasTrace && !approval && !interaction && !isPending) {
    return null
  }

  return (
    <div className="group flex w-full justify-start">
      <div className="w-full space-y-2">
        {hasTrace && showInlineTrace && (
          <div className="text-xs">
            <button
              onClick={() => setTraceOpen(!traceOpen)}
              className="text-ops-overlay hover:text-ops-subtext flex items-center gap-1"
            >
              <span>{traceOpen ? '▼' : '▶'}</span>
              <span>执行轨迹 ({message.execTrace!.length})</span>
            </button>
            {traceOpen && (
              <ToolTraceList
                items={message.execTrace!}
                onTraceActionRule={onTraceActionRule}
                policyRuleBusy={policyRuleBusy}
              />
            )}
          </div>
        )}

        {approval && (
          <ToolApprovalCard
            approval={approval}
            approvalRows={approvalRows}
            approvalActions={approvalActions}
            onApproval={onApproval}
          />
        )}

        {interaction && (
          <UserInteractionCard interaction={interaction} onSubmit={onInteraction} />
        )}

        {hasContent ? (
          <AssistantReportBubble message={message} onEdit={onEdit} onDelete={onDelete} />
        ) : shouldShowEmptyBubble ? (
          <TypingIndicatorBubble />
        ) : null}
      </div>
    </div>
  )
}
