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
      className="min-h-0 flex-1 space-y-5 overflow-y-auto bg-[linear-gradient(to_bottom,color-mix(in_oklab,var(--color-ops-surface0)_62%,transparent),transparent_190px)] px-5 py-5 lg:px-7 lg:py-6"
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
