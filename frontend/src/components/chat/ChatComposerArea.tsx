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
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
  onApplySlashCommand: (prompt: string) => void
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
  onPaste: (event: ClipboardEvent<HTMLTextAreaElement>) => void
  onRemoveAttachment: (id: string) => void
  onSend: () => void
  onStop: () => void
  onTraceActionRule: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
}

export default function ChatComposerArea({
  attachments,
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
  onApproval,
  onApplySlashCommand,
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
  onPaste,
  onRemoveAttachment,
  onSend,
  onStop,
  onTraceActionRule,
}: ChatComposerAreaProps) {
  return (
    <div
      className="relative border-t border-ops-surface0 bg-ops-panel px-5 py-4 lg:px-8"
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
      {quickCommands.length > 0 && (
        <QuickCommandDock
          commands={quickCommands}
          onSelect={onApplySlashCommand}
          onManage={onManageCommands}
        />
      )}
      {visibleSlashCommands.length > 0 && (
        <SlashCommandMenu
          commands={visibleSlashCommands}
          onSelect={onApplySlashCommand}
        />
      )}
      {attachments.length > 0 && (
        <AttachmentPreviewStrip
          attachments={attachments}
          onRemove={onRemoveAttachment}
        />
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
        fileInputRef={fileInputRef}
        textareaRef={textareaRef}
        input={input}
        uploadingAttachment={uploadingAttachment}
        isStreaming={isStreaming}
        hasSendableContent={Boolean(input.trim() || attachments.length > 0)}
        onInputChange={onInputChange}
        onHistoryReset={onHistoryReset}
        onKeyDown={onKeyDown}
        onPaste={onPaste}
        onSend={onSend}
        onStop={onStop}
      />
    </div>
  )
}
