import type { ChatMessage, ChatMessageAttachment } from '@/types'
import { formatBytes } from './format'
import { renderMarkdown } from './markdown'

export function UserMessageBubble({
  message,
  onEdit,
  onDelete,
}: {
  message: ChatMessage
  onEdit?: (message: ChatMessage) => void
  onDelete?: (message: ChatMessage) => void
}) {
  return (
    <div className="group flex justify-end">
      <div className="max-w-[86%] rounded-lg rounded-br-sm bg-ops-accent/15 px-4 py-2.5 text-sm text-ops-text">
        <div className="mb-1 flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button onClick={() => onEdit?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-subtext hover:bg-ops-dark/50 hover:text-ops-text">编辑</button>
          <button onClick={() => onDelete?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-alert hover:bg-ops-alert/10">删除</button>
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
}: {
  message: ChatMessage
  onEdit?: (message: ChatMessage) => void
  onDelete?: (message: ChatMessage) => void
}) {
  const assistantTime = new Date(message.timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <article className="w-full overflow-hidden rounded-lg border border-ops-surface1/55 bg-ops-panel/85 shadow-[0_10px_28px_rgba(0,0,0,0.16)]">
      <div className="flex items-center justify-between gap-3 border-b border-ops-surface0/80 bg-ops-surface0/35 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-ops-success shadow-[0_0_14px_rgba(79,209,177,0.55)]" />
          <span className="text-xs font-semibold text-ops-text">AI 输出报告</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => onEdit?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-subtext opacity-0 transition-opacity hover:bg-ops-dark/50 hover:text-ops-text group-hover:opacity-100">编辑</button>
          <button onClick={() => onDelete?.(message)} className="rounded px-1.5 py-0.5 text-[11px] text-ops-alert opacity-0 transition-opacity hover:bg-ops-alert/10 group-hover:opacity-100">删除</button>
          <span className="font-mono text-[11px] text-ops-overlay">{assistantTime}</span>
        </div>
      </div>
      <div
        className="markdown-body ai-report-body w-full px-5 py-4"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
      />
    </article>
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
