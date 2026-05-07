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
  onShowAttachmentFormats,
  onKeyDown,
  onPaste,
  onSend,
  onStop,
}: ChatComposerInputProps) {
  return (
    <div className="flex items-end gap-2 rounded-[18px] border border-ops-surface1/70 bg-ops-dark/35 p-2">
      <button
        type="button"
        onClick={() => {
          onShowAttachmentFormats()
          fileInputRef.current?.click()
        }}
        disabled={uploadingAttachment || isStreaming}
        className="h-[50px] shrink-0 rounded-xl border border-ops-surface1/80 bg-ops-panel/80 px-3 text-sm font-semibold text-ops-subtext transition-colors hover:border-ops-accent/70 hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-50"
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
        className="min-h-[90px] flex-1 resize-y rounded-[14px] border border-ops-surface1/80 bg-ops-panel/82 px-4 py-3 text-sm leading-6 text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent focus:shadow-[0_0_0_3px_rgba(40,208,168,0.08)]"
        style={{ height: '90px', maxHeight: '240px', overflowY: 'auto' }}
      />

      {isStreaming ? (
        <button
          onClick={onStop}
          className="h-[50px] shrink-0 rounded-xl bg-ops-alert px-5 text-sm font-black text-white transition-colors hover:bg-ops-alert/80"
        >
          停止
        </button>
      ) : (
        <button
          onClick={onSend}
          disabled={!hasSendableContent}
          className="h-[50px] shrink-0 rounded-xl bg-ops-accent px-5 text-sm font-black text-ops-dark shadow-[0_12px_34px_rgba(40,208,168,0.18)] transition-colors hover:bg-ops-accent/80 disabled:cursor-not-allowed disabled:opacity-40"
        >
          发送
        </button>
      )}
    </div>
  )
}
