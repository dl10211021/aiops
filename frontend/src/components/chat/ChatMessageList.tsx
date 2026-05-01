import type { RefObject } from 'react'
import type { ChatMessage, SafetyPolicyAction, SafetyPolicyDecision, ToolApproval } from '@/types'
import MessageBubble from '@/features/sessions/MessageBubble'

interface ChatMessageListProps {
  containerRef: RefObject<HTMLDivElement | null>
  isStreaming: boolean
  messages: ChatMessage[]
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
  onDelete: (message: ChatMessage) => void
  onEdit: (message: ChatMessage) => void
  onInteraction: (requestId: string, value: string, label?: string) => void
  onTraceActionRule: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy: string | null
}

export default function ChatMessageList({
  containerRef,
  isStreaming,
  messages,
  onApproval,
  onDelete,
  onEdit,
  onInteraction,
  onTraceActionRule,
  policyRuleBusy,
}: ChatMessageListProps) {
  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-5 py-5 lg:px-8 lg:py-6 space-y-5"
    >
      {messages.map((msg, index) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          isPending={isStreaming && index === messages.length - 1 && msg.role === 'assistant'}
          onApproval={onApproval}
          onInteraction={onInteraction}
          onTraceActionRule={onTraceActionRule}
          policyRuleBusy={policyRuleBusy}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
