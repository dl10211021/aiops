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
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
  onPaste: (event: ClipboardEvent<HTMLTextAreaElement>) => void
  onSend: () => void
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
  onKeyDown,
  onPaste,
  onSend,
  onStop,
}: ChatComposerInputProps) {
  return (
    <div className="flex items-end gap-2">
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploadingAttachment || isStreaming}
        className="h-14 shrink-0 rounded-lg border border-ops-surface1 bg-ops-dark px-3 text-sm text-ops-subtext transition-colors hover:border-ops-accent/70 hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-50"
        title="上传附件"
      >
        {uploadingAttachment ? '解析中' : '附件'}
      </button>

      <textarea
        ref={textareaRef}
        value={input}
        onChange={(event) => {
          onInputChange(event.target.value)
          onHistoryReset()
        }}
        onKeyDown={onKeyDown}
        onPaste={onPaste}
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        rows={1}
        className="min-h-14 flex-1 resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-4 py-4 text-sm leading-5 text-ops-text outline-none transition-colors focus:border-ops-accent"
        style={{ height: '56px', maxHeight: '260px', overflowY: 'auto' }}
      />

      {isStreaming ? (
        <button
          onClick={onStop}
          className="h-14 shrink-0 rounded-lg bg-ops-alert px-5 text-sm font-medium text-white transition-colors hover:bg-ops-alert/80"
        >
          停止
        </button>
      ) : (
        <button
          onClick={onSend}
          disabled={!hasSendableContent}
          className="h-14 shrink-0 rounded-lg bg-ops-accent px-5 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/80 disabled:cursor-not-allowed disabled:opacity-40"
        >
          发送
        </button>
      )}
    </div>
  )
}
