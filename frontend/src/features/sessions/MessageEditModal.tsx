import type { ChatMessage } from '@/types'

interface MessageEditModalProps {
  message: ChatMessage
  content: string
  busy: boolean
  onContentChange: (content: string) => void
  onClose: () => void
  onSave: () => void
}

export default function MessageEditModal({
  message,
  content,
  busy,
  onContentChange,
  onClose,
  onSave,
}: MessageEditModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="w-full max-w-3xl overflow-hidden rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className="text-xs font-semibold text-ops-accent">编辑会话内容</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">
            {message.role === 'user' ? '修改用户消息' : '修改 AI 输出'}
          </h2>
          <p className="mt-1 text-sm text-ops-subtext">修改会同步写入历史记录，刷新后仍会保留。</p>
        </div>
        <div className="p-5">
          <textarea
            value={content}
            onChange={(event) => onContentChange(event.target.value)}
            className="h-72 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm leading-6 text-ops-text outline-none focus:border-ops-accent"
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button
            onClick={onClose}
            disabled={busy}
            className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onSave}
            disabled={busy}
            className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark disabled:opacity-50"
          >
            {busy ? '保存中...' : '保存修改'}
          </button>
        </div>
      </section>
    </div>
  )
}
