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

function formatMessageTimeline(timestamp: number) {
  return new Date(timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function roleTimelineLabel(role: ChatMessage['role']) {
  if (role === 'user') return '用户输入'
  if (role === 'assistant') return 'AI 输出'
  return '系统事件'
}

function roleTimelineClass(role: ChatMessage['role']) {
  if (role === 'user') return 'border-ops-accent/65 bg-ops-accent text-ops-dark shadow-[0_0_18px_rgba(40,208,168,0.26)]'
  if (role === 'assistant') return 'border-sky-300/60 bg-sky-300 text-ops-dark shadow-[0_0_18px_rgba(125,211,252,0.2)]'
  return 'border-ops-overlay/60 bg-ops-overlay text-ops-dark'
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
      className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-[radial-gradient(circle_at_18%_8%,rgba(40,208,168,0.08),transparent_24rem),linear-gradient(180deg,rgba(9,19,34,0.74),rgba(8,17,30,0.94))] px-4 py-4 lg:px-6 lg:py-5"
    >
      {messages.map((msg, index) => (
        <div key={msg.id} className="relative pl-7">
          <span className="absolute left-[9px] top-7 bottom-[-18px] w-px bg-gradient-to-b from-ops-accent/32 via-ops-surface1/55 to-transparent" />
          <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
            <span className={`relative z-[1] h-3 w-3 rounded-full border-2 ${roleTimelineClass(msg.role)}`} />
            <span className="rounded-full border border-ops-surface1/70 bg-ops-dark/55 px-2.5 py-1 font-mono text-ops-subtext">
              {formatMessageTimeline(msg.timestamp)}
            </span>
            <span className="rounded-full border border-ops-surface1/60 bg-ops-panel/55 px-2.5 py-1 font-bold text-ops-overlay">
              {roleTimelineLabel(msg.role)}
            </span>
            {msg.execTrace?.length ? (
              <span className="rounded-full border border-ops-accent/35 bg-ops-accent/10 px-2.5 py-1 font-bold text-ops-accent">
                工具链路 {msg.execTrace.length} 步
              </span>
            ) : null}
          </div>
          <div
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
              showInlineTrace={showInlineTrace}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
