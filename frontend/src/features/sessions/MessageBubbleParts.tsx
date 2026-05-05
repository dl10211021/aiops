import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { useStore } from '@/store'
import type { ChatMessage, ChatMessageAttachment, MemoryReference } from '@/types'
import { formatBytes } from './format'
import { renderMarkdown } from './markdown'

function formatMessageTime(timestamp: number) {
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

export function UserMessageBubble({
  message,
  onEdit,
  onDelete,
}: {
  message: ChatMessage
  onEdit?: (message: ChatMessage) => void
  onDelete?: (message: ChatMessage) => void
}) {
  const userTime = formatMessageTime(message.timestamp)
  return (
    <div className="group flex justify-end">
      <div className="max-w-[86%] rounded-lg rounded-br-sm bg-ops-accent/15 px-4 py-2.5 text-sm text-ops-text">
        <div className="mb-1 flex items-center justify-end gap-2">
          <span className="font-mono text-[11px] text-ops-overlay">{userTime}</span>
          <button onClick={() => onEdit?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-subtext opacity-0 transition-opacity hover:bg-ops-dark/50 hover:text-ops-text group-hover:opacity-100">编辑</button>
          <button onClick={() => onDelete?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-alert opacity-0 transition-opacity hover:bg-ops-alert/10 group-hover:opacity-100">删除</button>
        </div>
        <div className="whitespace-pre-wrap">{message.content}</div>
        {message.attachments && message.attachments.length > 0 && (
          <UserAttachmentList attachments={message.attachments} />
        )}
      </div>
    </div>
  )
}

export function SystemMessageBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-center">
      <div className="text-xs text-ops-subtext bg-ops-surface0 rounded-full px-3 py-1">
        {content}
      </div>
    </div>
  )
}

export function AssistantReportBubble({
  message,
  onEdit,
  onDelete,
  onFeedback,
}: {
  message: ChatMessage
  onEdit?: (message: ChatMessage) => void
  onDelete?: (message: ChatMessage) => void
  onFeedback?: (message: ChatMessage, rating: 'up' | 'down', note?: string) => void
}) {
  const setView = useStore((state) => state.setView)
  const bubbleRef = useRef<HTMLElement | null>(null)
  const [focusedByAudit, setFocusedByAudit] = useState(false)
  const assistantTime = formatMessageTime(message.timestamp)
  const feedbackRating = message.feedback?.rating
  const ownMessageId = String(message.memoryId || message._memory_id || message.id || '')
  const feedbackNote = message.feedback?.note?.trim()
  const recordFeedback = (rating: 'up' | 'down') => {
    const defaultNote = rating === 'up'
      ? '这条回答好在哪里？可不填，例如：巡检结论准确、建议可执行。'
      : '这条回答哪里不对？可不填，例如：误判风险、建议不适合当前环境。'
    const note = window.prompt(defaultNote, feedbackNote || '')?.trim()
    if (note === undefined) return
    onFeedback?.(message, rating, note)
  }
  const openMemoryActivity = () => {
    setView('knowledge')
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('opscore:knowledge-target', {
        detail: { tab: 'memory', step: 'govern', messageId: ownMessageId },
      }))
    }, 60)
  }

  useEffect(() => {
    const handleChatFocusMessage = (event: Event) => {
      const detail = (event as CustomEvent<{ messageId?: string | number }>).detail
      const targetMessageId = String(detail?.messageId || '')
      if (!targetMessageId || targetMessageId !== ownMessageId) return
      bubbleRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setFocusedByAudit(true)
      window.setTimeout(() => setFocusedByAudit(false), 2400)
    }
    window.addEventListener('opscore:chat-focus-message', handleChatFocusMessage)
    return () => {
      window.removeEventListener('opscore:chat-focus-message', handleChatFocusMessage)
    }
  }, [ownMessageId])
  const handleCodeCopy = async (event: MouseEvent<HTMLDivElement>) => {
    const target = event.target
    if (!(target instanceof HTMLButtonElement) || !target.dataset.copyCode) return
    const text = target.dataset.copyCode
    const originalText = target.textContent || '复制'
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.setAttribute('readonly', 'true')
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      target.textContent = '已复制'
      target.classList.add('is-copied')
      window.setTimeout(() => {
        target.textContent = originalText
        target.classList.remove('is-copied')
      }, 1200)
    } catch {
      target.textContent = '复制失败'
      window.setTimeout(() => {
        target.textContent = originalText
      }, 1200)
    }
  }

  return (
    <article
      ref={bubbleRef}
      className={`w-full overflow-hidden rounded-lg border bg-ops-panel/85 shadow-[0_10px_28px_rgba(0,0,0,0.16)] transition-all ${
        focusedByAudit
          ? 'border-ops-accent shadow-[0_0_0_1px_rgba(45,212,191,0.35),0_16px_36px_rgba(45,212,191,0.12)]'
          : 'border-ops-surface1/55'
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-ops-surface0/80 bg-ops-surface0/35 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-ops-success shadow-[0_0_14px_rgba(79,209,177,0.55)]" />
          <span className="text-xs font-semibold text-ops-text">AI 输出报告</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => recordFeedback('up')}
            title="回答很好，写入会话成功经验记忆"
            className={`rounded-full border px-2 py-0.5 text-[12px] transition-colors ${
              feedbackRating === 'up'
                ? 'border-ops-success/70 bg-ops-success/15 text-ops-success'
                : 'border-ops-surface1 text-ops-subtext hover:border-ops-success/55 hover:text-ops-success'
            }`}
          >
            👍
          </button>
          <button
            onClick={() => recordFeedback('down')}
            title="回答较差，只做纠错审计，不作为成功经验"
            className={`rounded-full border px-2 py-0.5 text-[12px] transition-colors ${
              feedbackRating === 'down'
                ? 'border-ops-alert/70 bg-ops-alert/15 text-ops-alert'
                : 'border-ops-surface1 text-ops-subtext hover:border-ops-alert/55 hover:text-ops-alert'
            }`}
          >
            👎
          </button>
          <button onClick={() => onEdit?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-subtext opacity-0 transition-opacity hover:bg-ops-dark/50 hover:text-ops-text group-hover:opacity-100">编辑</button>
          <button onClick={() => onDelete?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-alert opacity-0 transition-opacity hover:bg-ops-alert/10 group-hover:opacity-100">删除</button>
          <span className="font-mono text-[11px] text-ops-overlay">{assistantTime}</span>
        </div>
      </div>
      {feedbackRating && (
        <div className={`flex flex-wrap items-center justify-between gap-2 border-b border-ops-surface0/70 px-4 py-1.5 text-[11px] ${
          feedbackRating === 'up' ? 'text-ops-success' : 'text-ops-alert'
        }`}>
          <span>
            {feedbackRating === 'up'
              ? '已记录好评：进入会话记忆，后续可复用但必须实时验证'
              : '已记录差评：只用于纠错审计，不作为成功经验沉淀'}
            {feedbackNote ? `；备注：${feedbackNote}` : ''}
          </span>
          <button
            type="button"
            onClick={openMemoryActivity}
            className="rounded-full border border-current/35 px-2 py-0.5 text-[11px] hover:bg-current/10"
          >
            查看记忆活动
          </button>
        </div>
      )}
      <MemoryReferenceStrip message={message} />
      <div
        className="markdown-body ai-report-body w-full px-5 py-4"
        onClick={handleCodeCopy}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
      />
    </article>
  )
}

function referenceSourceType(ref: MemoryReference) {
  const sourceType = String(ref.source_type || '').toLowerCase()
  const kind = String(ref.kind || '').toLowerCase()
  const kindLabel = String(ref.kind_label || '')
  if (sourceType === 'rag' || kindLabel.includes('RAG') || ['articles', 'candidates', 'sources', 'raw'].includes(kind)) {
    return 'rag'
  }
  return 'memory'
}

function referenceBadge(ref: MemoryReference) {
  if (referenceSourceType(ref) === 'rag') {
    return ref.kind_label || 'RAG 资料'
  }
  return '长期记忆'
}

function referenceTitle(ref: MemoryReference) {
  return ref.title || ref.scope_label || ref.path || ref.scope_id || '未命名引用'
}

function referenceMeta(ref: MemoryReference) {
  return [
    ref.source_session_id ? `会话 ${ref.source_session_id}` : '',
    ref.path || ref.scope_id || '',
    ref.updated_at || ref.timestamp || '',
    ref.score !== undefined ? `命中分 ${ref.score}` : '',
  ].filter(Boolean).join(' · ')
}

function referenceReason(ref: MemoryReference) {
  if (referenceSourceType(ref) === 'rag') {
    return '来自 RAG 检索命中的资料证据，已做敏感字段脱敏；用于辅助回答引用，不替代当前会话的实时巡检结果。'
  }
  return '来自长期记忆或会话经验，回答时需要结合当前证据复核，不能直接当作事实替代实时巡检结果。'
}

function referenceSearchQuery(ref: MemoryReference) {
  return (ref.title || ref.summary_preview || ref.path || ref.scope_id || '').trim()
}

function MemoryReferenceStrip({ message }: { message: ChatMessage }) {
  const setView = useStore((state) => state.setView)
  const refs = message.memoryRefs || message.memory_refs || []
  if (!refs.length) return null
  const ragCount = refs.filter((ref) => referenceSourceType(ref) === 'rag').length
  const memoryCount = refs.length - ragCount
  const openReference = (ref: MemoryReference) => {
    if (referenceSourceType(ref) === 'rag') {
      const query = referenceSearchQuery(ref)
      setView('knowledge')
      window.setTimeout(() => {
        window.dispatchEvent(new CustomEvent('opscore:knowledge-target', {
          detail: { tab: 'documents', step: 'discover', query, scope: ref.kind || 'all' },
        }))
      }, 60)
      return
    }
    setView('knowledge')
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('opscore:knowledge-target', {
        detail: { tab: 'memory', step: 'govern' },
      }))
    }, 60)
  }
  return (
    <details open className="border-b border-ops-accent/25 bg-[linear-gradient(135deg,rgba(45,212,191,0.13),rgba(37,99,235,0.08))] px-4 py-2 text-[11px] text-ops-subtext">
      <summary className="cursor-pointer select-none font-semibold text-ops-accent">
        本轮引用来源：{refs.length} 条
        {ragCount > 0 ? ` · RAG 资料 ${ragCount}` : ''}
        {memoryCount > 0 ? ` · 长期记忆 ${memoryCount}` : ''}
      </summary>
      <p className="mt-1 leading-5 text-ops-overlay">
        这里展示本轮回答使用过的资料和记忆。RAG 资料来自知识库检索，长期记忆来自会话经验；两者都只做辅助依据，最终仍以当前资产实时证据为准。
      </p>
      <div className="mt-2 grid gap-1.5">
        {refs.map((ref, index) => (
          <div
            key={`${ref.path || ref.scope_id || ref.title || ref.source_session_id || 'ref'}-${index}`}
            className={`rounded-md border px-2.5 py-1.5 ${
              referenceSourceType(ref) === 'rag'
                ? 'border-ops-accent/35 bg-ops-accent/10'
                : 'border-ops-surface1/60 bg-ops-panel/60'
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2 py-0.5 ${
                referenceSourceType(ref) === 'rag'
                  ? 'border-ops-accent/45 text-ops-accent'
                  : 'border-ops-surface1 text-ops-subtext'
              }`}>
                {referenceBadge(ref)}
              </span>
              <span className="font-semibold text-ops-text">{referenceTitle(ref)}</span>
              {referenceMeta(ref) && <span className="truncate font-mono text-ops-overlay">{referenceMeta(ref)}</span>}
            </div>
            <div className="mt-1 line-clamp-2 text-ops-subtext">
              {ref.summary_preview || '无摘要'}
            </div>
            <div className="mt-1 rounded border border-ops-surface0/80 bg-ops-dark/30 px-2 py-1 text-[10px] leading-4 text-ops-overlay">
              引用说明：{referenceReason(ref)}
            </div>
            <button
              type="button"
              onClick={() => openReference(ref)}
              className="mt-1.5 rounded-full border border-ops-accent/35 px-2 py-0.5 text-[10px] font-semibold text-ops-accent hover:bg-ops-accent/10"
            >
              {referenceSourceType(ref) === 'rag' ? '查看资料证据' : '查看记忆管理'}
            </button>
          </div>
        ))}
      </div>
    </details>
  )
}

export function TypingIndicatorBubble() {
  return (
    <div className="w-full rounded-lg border border-ops-surface1/55 bg-ops-panel/85 px-5 py-4 text-base">
      <span className="inline-flex gap-1">
        <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
        <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
        <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
      </span>
    </div>
  )
}

function UserAttachmentList({ attachments }: { attachments: ChatMessageAttachment[] }) {
  return (
    <div className="mt-2 space-y-1.5">
      {attachments.map((file, index) => (
        <div
          key={`${file.filename}-${index}`}
          className="flex items-center justify-between gap-3 rounded-md border border-ops-accent/25 bg-ops-dark/35 px-2.5 py-1.5 text-[11px]"
        >
          <div className="min-w-0">
            <div className="truncate font-semibold text-ops-text">{file.filename}</div>
            <div className="mt-0.5 text-ops-overlay">
              {file.ext || file.kind || '附件'} · {formatBytes(file.size)}
              {file.rows !== undefined ? ` · ${file.rows} 行` : ''}
              {file.pages !== undefined ? ` · ${file.pages} 页` : ''}
              {file.truncated ? ' · 已截断' : ''}
            </div>
          </div>
          <span className="shrink-0 rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-subtext">
            已随消息发送
          </span>
        </div>
      ))}
    </div>
  )
}
