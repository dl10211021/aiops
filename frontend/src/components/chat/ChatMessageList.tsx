import { useEffect, useState } from 'react'
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
  showInlineTrace?: boolean
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
  showInlineTrace = true,
}: ChatMessageListProps) {
  const [highlightedMessageId, setHighlightedMessageId] = useState<string | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const onScrollToMessage = (event: Event) => {
      const messageId = (event as CustomEvent<{ messageId?: string }>).detail?.messageId
      if (!messageId) return
      const target = Array.from(container.querySelectorAll<HTMLElement>('[data-message-id]'))
        .find((item) => item.dataset.messageId === messageId)
      if (!target) return
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setHighlightedMessageId(messageId)
      window.setTimeout(() => setHighlightedMessageId((current) => current === messageId ? null : current), 1600)
    }
    window.addEventListener('opscore:scroll-chat-message', onScrollToMessage)
    return () => window.removeEventListener('opscore:scroll-chat-message', onScrollToMessage)
  }, [containerRef])

  return (
    <div
      ref={containerRef}
      className="min-h-0 flex-1 space-y-5 overflow-y-auto bg-[linear-gradient(to_bottom,color-mix(in_oklab,var(--color-ops-surface0)_62%,transparent),transparent_190px)] px-5 py-5 lg:px-7 lg:py-6"
    >
      {messages.map((msg, index) => (
        <div
          key={msg.id}
          data-message-id={msg.id}
          data-message-role={msg.role}
          data-message-time={msg.timestamp}
          className={`rounded-xl transition-[box-shadow,background-color] duration-300 ${
            highlightedMessageId === msg.id
              ? 'bg-ops-accent/10 shadow-[0_0_0_1px_rgba(45,212,191,0.55),0_0_32px_rgba(45,212,191,0.18)]'
              : ''
          }`}
        >
          <MessageBubble
            message={msg}
            isPending={isStreaming && index === messages.length - 1 && msg.role === 'assistant'}
            onApproval={onApproval}
            onInteraction={onInteraction}
            onTraceActionRule={onTraceActionRule}
            policyRuleBusy={policyRuleBusy}
            onEdit={onEdit}
            onDelete={onDelete}
            showInlineTrace={showInlineTrace}
          />
        </div>
      ))}
    </div>
  )
}
