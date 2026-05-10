import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { ClipboardEvent, KeyboardEvent, RefObject } from 'react'

interface ChatComposerInputProps {
  fileInputRef: RefObject<HTMLInputElement | null>
  textareaRef: RefObject<HTMLTextAreaElement | null>
  input: string
  uploadingAttachment: boolean
  isStreaming: boolean
  hasSendableContent: boolean
  onInputChange: (value: string) => void
  onHistoryReset: () => void
  onShowAttachmentFormats: () => void
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
  onPaste: (event: ClipboardEvent<HTMLTextAreaElement>) => void
  onSend: (value?: string) => void
  onStop: () => void
}

export default function ChatComposerInput({
  fileInputRef,
  textareaRef,
  input,
  uploadingAttachment,
  isStreaming,
  hasSendableContent,
  onInputChange,
  onHistoryReset,
  onShowAttachmentFormats,
  onKeyDown,
  onPaste,
  onSend,
  onStop,
}: ChatComposerInputProps) {
  const [localInput, setLocalInput] = useState(input)
  const syncTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
  const lastSyncedInputRef = useRef(input)

  useEffect(() => {
    if (input === lastSyncedInputRef.current) return
    lastSyncedInputRef.current = input
    setLocalInput(input)
  }, [input])

  useEffect(() => () => {
    if (syncTimerRef.current) window.clearTimeout(syncTimerRef.current)
  }, [])

  const syncInput = (value: string) => {
    if (syncTimerRef.current) window.clearTimeout(syncTimerRef.current)
    lastSyncedInputRef.current = value
    onInputChange(value)
  }

  const scheduleInputSync = (value: string) => {
    if (syncTimerRef.current) window.clearTimeout(syncTimerRef.current)
    syncTimerRef.current = window.setTimeout(() => syncInput(value), 120)
  }

  const canSend = Boolean(localInput.trim()) || hasSendableContent

  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 48), 160)}px`
  }, [localInput, textareaRef])

  return (
    <div className="ops-chat-composer-input flex items-end gap-2 rounded-xl border border-ops-surface1/70 bg-ops-dark/35 p-1.5">
      <button
        type="button"
        onClick={() => {
          onShowAttachmentFormats()
          fileInputRef.current?.click()
        }}
        disabled={uploadingAttachment || isStreaming}
        className="ops-chat-attachment-button h-12 shrink-0 rounded-lg border border-ops-surface1/80 bg-ops-panel/80 px-3 text-sm font-semibold text-ops-subtext transition-colors hover:border-ops-accent/70 hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-50"
        title="上传附件"
      >
        {uploadingAttachment ? '解析中' : '附件'}
      </button>

      <textarea
        ref={textareaRef}
        value={localInput}
        onChange={(event) => {
          const nextInput = event.target.value
          setLocalInput(nextInput)
          scheduleInputSync(nextInput)
          onHistoryReset()
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            syncInput(event.currentTarget.value)
          }
          onKeyDown(event)
        }}
        onPaste={onPaste}
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        rows={1}
        className="min-h-12 flex-1 resize-none rounded-lg border border-ops-surface1/80 bg-ops-panel/82 px-3 py-3 text-sm leading-6 text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent focus:shadow-[0_0_0_3px_rgba(40,208,168,0.08)]"
        style={{ maxHeight: '160px', overflowY: 'auto' }}
      />

      {isStreaming ? (
        <button
          onClick={onStop}
          className="ops-chat-send-button h-12 shrink-0 rounded-lg bg-ops-alert px-5 text-sm font-black text-white transition-colors hover:bg-ops-alert/80"
        >
          停止
        </button>
      ) : (
        <button
          onClick={() => {
            syncInput(localInput)
            onSend(localInput)
          }}
          disabled={!canSend}
          className="ops-chat-send-button h-12 shrink-0 rounded-lg bg-ops-accent px-5 text-sm font-black text-ops-dark shadow-[0_12px_34px_rgba(40,208,168,0.18)] transition-colors hover:bg-ops-accent/80 disabled:cursor-not-allowed disabled:opacity-40"
        >
          发送
        </button>
      )}
    </div>
  )
}
