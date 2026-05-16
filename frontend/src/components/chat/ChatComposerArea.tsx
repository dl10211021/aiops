import { useEffect, useState } from 'react'
import type { ClipboardEvent, DragEvent, KeyboardEvent, RefObject } from 'react'
import type {
  SafetyPolicyAction,
  SafetyPolicyDecision,
  SlashCommand,
  ToolApproval,
} from '@/types'
import AttachmentPreviewStrip from '@/features/sessions/AttachmentPreviewStrip'
import { PendingActionDock, PolicyBlockDock } from '@/features/sessions/AttentionDocks'
import ChatComposerInput from '@/features/sessions/ChatComposerInput'
import { QuickCommandDock, SlashCommandMenu } from '@/features/sessions/CommandShortcuts'
import type { LatestPolicyBlock, PendingAttention } from '@/features/sessions/chatAttention'
import type { ChatAttachmentPreview } from '@/features/sessions/chatTypes'

interface ChatComposerAreaProps {
  attachments: ChatAttachmentPreview[]
  draftKey: string
  fileInputRef: RefObject<HTMLInputElement | null>
  input: string
  isDragging: boolean
  isStreaming: boolean
  pendingAttention: PendingAttention | null
  policyRuleBusy: string | null
  quickCommands: SlashCommand[]
  textareaRef: RefObject<HTMLTextAreaElement | null>
  uploadingAttachment: boolean
  visiblePolicyBlock: LatestPolicyBlock | null
  visibleSlashCommands: SlashCommand[]
  selectedSlashCommandIndex: number
  sessionMode?: 'readonly' | 'readwrite'
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
  onApplySlashCommand: (prompt: string) => void
  onSlashCommandIndexChange: (index: number) => void
  onDismissPolicyBlock: () => void
  onDragLeave: (event: DragEvent<HTMLDivElement>) => void
  onDragOver: (event: DragEvent<HTMLDivElement>) => void
  onDrop: (event: DragEvent<HTMLDivElement>) => void
  onFiles: (files: FileList | File[] | null) => Promise<void>
  onHistoryReset: () => void
  onInputChange: (value: string) => void
  onInteraction: (requestId: string, value: string, label?: string) => void
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
  onManageCommands: () => void
  onOpenRealtimeCanvas?: () => void
  onPaste: (event: ClipboardEvent<HTMLTextAreaElement>) => void
  onRemoveAttachment: (id: string) => void
  onSend: (value?: string) => void
  onStop: () => void
  onTraceActionRule: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
}

export default function ChatComposerArea({
  attachments,
  draftKey,
  fileInputRef,
  input,
  isDragging,
  isStreaming,
  pendingAttention,
  policyRuleBusy,
  quickCommands,
  textareaRef,
  uploadingAttachment,
  visiblePolicyBlock,
  visibleSlashCommands,
  selectedSlashCommandIndex,
  sessionMode,
  onApproval,
  onApplySlashCommand,
  onSlashCommandIndexChange,
  onDismissPolicyBlock,
  onDragLeave,
  onDragOver,
  onDrop,
  onFiles,
  onHistoryReset,
  onInputChange,
  onInteraction,
  onKeyDown,
  onManageCommands,
  onOpenRealtimeCanvas,
  onPaste,
  onRemoveAttachment,
  onSend,
  onStop,
  onTraceActionRule,
}: ChatComposerAreaProps) {
  const [showAttachmentFormats, setShowAttachmentFormats] = useState(false)

  useEffect(() => {
    const onShowFormats = () => {
      setShowAttachmentFormats(true)
      window.setTimeout(() => setShowAttachmentFormats(false), 6500)
    }
    window.addEventListener('opscore:show-attachment-formats', onShowFormats)
    return () => window.removeEventListener('opscore:show-attachment-formats', onShowFormats)
  }, [])

  return (
    <div
      className="ops-chat-composer relative border-t border-ops-surface1/70 px-3 py-2 lg:px-4"
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {isDragging && (
        <div className="pointer-events-none absolute inset-2 z-10 grid place-items-center rounded-lg border border-dashed border-ops-accent bg-ops-dark/90 text-sm font-medium text-ops-accent">
          松开后解析附件
        </div>
      )}
      {pendingAttention && (
        <PendingActionDock
          item={pendingAttention}
          onApproval={onApproval}
          onInteraction={onInteraction}
          sessionMode={sessionMode}
        />
      )}
      {visiblePolicyBlock && (
        <PolicyBlockDock
          item={visiblePolicyBlock}
          onTraceActionRule={onTraceActionRule}
          onDismiss={onDismissPolicyBlock}
          policyRuleBusy={policyRuleBusy}
        />
      )}
      {(quickCommands.length > 0 || onOpenRealtimeCanvas) && (
        <QuickCommandDock
          commands={quickCommands}
          onSelect={onApplySlashCommand}
          onManage={onManageCommands}
          onOpenRealtimeCanvas={onOpenRealtimeCanvas}
        />
      )}
      {visibleSlashCommands.length > 0 && (
        <SlashCommandMenu
          commands={visibleSlashCommands}
          activeIndex={selectedSlashCommandIndex}
          onSelect={onApplySlashCommand}
          onActiveIndexChange={onSlashCommandIndexChange}
        />
      )}
      {attachments.length > 0 && (
        <AttachmentPreviewStrip
          attachments={attachments}
          onRemove={onRemoveAttachment}
        />
      )}
      {showAttachmentFormats && (
        <div className="mb-2 flex items-start justify-between gap-3 rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-xs leading-5 text-ops-subtext">
          <div>
            <span className="font-semibold text-ops-accent">支持附件：</span>
            文本、日志、Markdown、CSV/TSV、JSON、YAML、INI/CONF、SQL、XML、PDF、Word、Excel、PNG/JPG/GIF/WebP/BMP 图片。
          </div>
          <button
            type="button"
            onClick={() => setShowAttachmentFormats(false)}
            className="shrink-0 rounded px-1.5 py-0.5 text-[11px] text-ops-overlay hover:bg-ops-dark/40 hover:text-ops-text"
          >
            收起
          </button>
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".txt,.md,.log,.csv,.tsv,.json,.yaml,.yml,.ini,.conf,.sql,.xml,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.webp,.bmp,image/*"
        className="hidden"
        onChange={(event) => void onFiles(event.target.files)}
      />
      <ChatComposerInput
        draftKey={draftKey}
        fileInputRef={fileInputRef}
        textareaRef={textareaRef}
        input={input}
        uploadingAttachment={uploadingAttachment}
        isStreaming={isStreaming}
        hasSendableContent={Boolean(input.trim() || attachments.length > 0)}
        onInputChange={onInputChange}
        onHistoryReset={onHistoryReset}
        onShowAttachmentFormats={() => {
          const event = new CustomEvent('opscore:show-attachment-formats')
          window.dispatchEvent(event)
        }}
        onKeyDown={onKeyDown}
        onPaste={onPaste}
        onSend={onSend}
        onStop={onStop}
      />
    </div>
  )
}
