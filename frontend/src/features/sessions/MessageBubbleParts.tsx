import type { MouseEvent } from 'react'
import type { ChatMessage, ChatMessageAttachment } from '@/types'
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
  onFeedback?: (message: ChatMessage, rating: 'up' | 'down') => void
}) {
  const assistantTime = formatMessageTime(message.timestamp)
  const feedbackRating = message.feedback?.rating
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
    <article className="w-full overflow-hidden rounded-lg border border-ops-surface1/55 bg-ops-panel/85 shadow-[0_10px_28px_rgba(0,0,0,0.16)]">
      <div className="flex items-center justify-between gap-3 border-b border-ops-surface0/80 bg-ops-surface0/35 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-ops-success shadow-[0_0_14px_rgba(79,209,177,0.55)]" />
          <span className="text-xs font-semibold text-ops-text">AI 输出报告</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onFeedback?.(message, 'up')}
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
            onClick={() => onFeedback?.(message, 'down')}
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
        <div className={`border-b border-ops-surface0/70 px-4 py-1.5 text-[11px] ${
          feedbackRating === 'up' ? 'text-ops-success' : 'text-ops-alert'
        }`}>
          {feedbackRating === 'up'
            ? '已记录好评：进入会话记忆，后续可复用但必须实时验证'
            : '已记录差评：只用于纠错审计，不作为成功经验沉淀'}
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

function MemoryReferenceStrip({ message }: { message: ChatMessage }) {
  const refs = message.memoryRefs || message.memory_refs || []
  if (!refs.length) return null
  return (
    <details className="border-b border-ops-surface0/70 bg-ops-dark/25 px-4 py-2 text-[11px] text-ops-subtext">
      <summary className="cursor-pointer select-none font-semibold text-ops-accent">
        本次引用记忆 {refs.length} 条
      </summary>
      <div className="mt-2 grid gap-1.5">
        {refs.map((ref, index) => (
          <div
            key={`${ref.scope_id}-${ref.timestamp || index}-${index}`}
            className="rounded-md border border-ops-surface1/60 bg-ops-panel/60 px-2.5 py-1.5"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-ops-accent">
                {ref.scope_label || ref.scope_id}
              </span>
              <span className="font-mono text-ops-overlay">{ref.timestamp || '未知时间'}</span>
              {ref.path && <span className="truncate font-mono text-ops-overlay">{ref.path}</span>}
            </div>
            <div className="mt-1 line-clamp-2 text-ops-subtext">
              {ref.summary_preview || '无摘要'}
            </div>
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
