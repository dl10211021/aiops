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
  onFeedback: (message: ChatMessage, rating: 'up' | 'down') => void
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
  onFeedback,
  onInteraction,
  onTraceActionRule,
  policyRuleBusy,
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
      className="ops-chat-message-list min-h-0 flex-1 overflow-y-auto px-4 py-4 lg:px-6 lg:py-5"
    >
      <div className="mx-auto w-full max-w-[1060px] space-y-3">
        <div className="mb-1 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ops-surface0/70 bg-ops-panel/38 px-3 py-2 text-[11px] text-ops-overlay">
          <span>会话输出区 · AI 报告优先保证阅读宽度，引用、画像、记忆默认折叠但不隐藏。</span>
          <span className="rounded-full border border-ops-surface1/55 px-2 py-0.5">消息 {messages.length}</span>
        </div>
        {messages.map((msg, index) => (
          <div
            key={msg.id}
            data-message-id={msg.id}
            data-message-role={msg.role}
            data-message-time={msg.timestamp}
            className={`rounded-2xl transition-[box-shadow,background-color] duration-300 ${
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
              onFeedback={onFeedback}
              showInlineTrace={false}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
