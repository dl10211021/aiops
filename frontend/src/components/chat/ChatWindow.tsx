import { useRef, useEffect, useState } from 'react'
import { useStore } from '@/store'
import AssetProfilePanel from '@/features/sessions/AssetProfilePanel'
import SessionToolsetBar from '@/features/sessions/SessionToolsetBar'
import ChatComposerArea from './ChatComposerArea'
import ChatEmptyState from './ChatEmptyState'
import ChatMessageList from './ChatMessageList'
import { ChatWindowOverlays } from './ChatWindowOverlays'
import {
  findLatestPolicyBlock,
  findPendingAttention,
  policyBlockKey,
} from '@/features/sessions/chatAttention'
import { buildQuickCommands, visibleSlashCommandsForInput } from '@/features/sessions/chatCommandMenu'
import { useAssetProfile } from '@/features/sessions/useAssetProfile'
import { useChatAttachments } from '@/features/sessions/useChatAttachments'
import { useChatInputDrafts } from '@/features/sessions/useChatInputDrafts'
import { useChatRuntimePreferences } from '@/features/sessions/useChatRuntimePreferences'
import { useChatStreaming } from '@/features/sessions/useChatStreaming'
import { useMessageHistoryActions } from '@/features/sessions/useMessageHistoryActions'
import { useSafetyPolicyActionRule } from '@/features/sessions/useSafetyPolicyActionRule'
import { useSessionCommands } from '@/features/sessions/useSessionCommands'
import { useSessionHistorySync } from '@/features/sessions/useSessionHistorySync'
import { useSessionToolCatalog } from '@/features/sessions/useSessionToolCatalog'
import { useToolApprovalDecision } from '@/features/sessions/useToolApprovalDecision'
import { useUserInteractionResponse } from '@/features/sessions/useUserInteractionResponse'

export default function ChatWindow() {
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)

  const [readWriteConfirm, setReadWriteConfirm] = useState<{ sessionId: string; message: string; remember: boolean } | null>(null)
  const [dismissedPolicyBlockKey, setDismissedPolicyBlockKey] = useState<string | null>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const inputDrafts = useChatInputDrafts(currentSessionId, textareaRef)

  const session = currentSessionId ? sessions[currentSessionId] : null
  const messages = session?.messages || []
  const isStreaming = session?.isStreaming || false
  const input = inputDrafts.input
  const {
    availableModels,
    modelName,
    readWriteWarningEnabled,
    setModelName,
    setThinkingMode,
    thinkingMode,
  } = useChatRuntimePreferences()
  const toolCatalog = useSessionToolCatalog(currentSessionId, session?.asset_type, session?.protocol)
  const chatAttachments = useChatAttachments(currentSessionId, isStreaming)
  const pendingAttention = findPendingAttention(messages)
  const latestPolicyBlock = findLatestPolicyBlock(messages)
  const latestPolicyBlockKey = latestPolicyBlock ? policyBlockKey(latestPolicyBlock) : null
  const visiblePolicyBlock = latestPolicyBlock && latestPolicyBlockKey !== dismissedPolicyBlockKey ? latestPolicyBlock : null
  const commandManager = useSessionCommands({ currentSessionId, session, toolCatalog })
  const assetProfile = useAssetProfile(currentSessionId, modelName)
  const toolApprovalDecision = useToolApprovalDecision(currentSessionId, messages)
  const safetyPolicyActionRule = useSafetyPolicyActionRule(
    latestPolicyBlock,
    setDismissedPolicyBlockKey,
  )
  const userInteractionResponse = useUserInteractionResponse(currentSessionId, sessions)
  const slashCommands = commandManager.slashCommands
  const quickCommands = buildQuickCommands(slashCommands)
  const visibleSlashCommands = visibleSlashCommandsForInput(input, slashCommands)

  const { sendMessage, stopStreaming, hasActiveStream } = useChatStreaming({
    currentSessionId,
    sessions,
    input,
    draftsBySession: inputDrafts.draftsBySession,
    attachments: chatAttachments.attachments,
    attachmentsBySession: chatAttachments.attachmentsBySession,
    readWriteWarningEnabled,
    modelName,
    thinkingMode,
    setReadWriteConfirm,
    setInputHistory: inputDrafts.setInputHistory,
    setHistoryIndex: inputDrafts.setHistoryIndex,
    setDraftsBySession: inputDrafts.setDraftsBySession,
    revokeAttachmentPreviews: chatAttachments.revokePreviews,
    setAttachmentsBySession: chatAttachments.setAttachmentsBySession,
  })
  const messageHistoryActions = useMessageHistoryActions(currentSessionId)
  useSessionHistorySync(currentSessionId, session, hasActiveStream)

  // Scroll to bottom on new messages
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 260)}px`
  }, [input, currentSessionId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.nativeEvent.isComposing) return

    if (inputDrafts.handleHistoryKeyDown(e)) return

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const confirmReadWriteSend = () => {
    if (!readWriteConfirm) return
    if (readWriteConfirm.remember) {
      sessionStorage.setItem(`opscore_rw_confirmed_${readWriteConfirm.sessionId}`, '1')
    }
    const { sessionId, message } = readWriteConfirm
    setReadWriteConfirm(null)
    void sendMessage(message, sessionId)
  }

  if (!session) {
    return <ChatEmptyState />
  }

  return (
    <>
      <ChatWindowOverlays
        commandManager={commandManager}
        messageHistoryActions={messageHistoryActions}
        readWriteConfirm={readWriteConfirm}
        session={session}
        toolApprovalDecision={toolApprovalDecision}
        onConfirmReadWriteSend={confirmReadWriteSend}
        onReadWriteConfirmChange={setReadWriteConfirm}
        onReadWriteConfirmClose={() => setReadWriteConfirm(null)}
      />
    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-ops-dark/20">
      <SessionToolsetBar
        catalog={toolCatalog}
        session={session}
        availableModels={availableModels}
        modelName={modelName}
        thinkingMode={thinkingMode}
        onModelChange={setModelName}
        onThinkingModeChange={setThinkingMode}
      />
      <AssetProfilePanel
        session={session}
        profile={assetProfile.profile}
        open={assetProfile.open}
        busy={assetProfile.busy}
        onToggle={assetProfile.toggle}
        onGenerate={assetProfile.generate}
      />
      <ChatMessageList
        containerRef={messagesContainerRef}
        isStreaming={isStreaming}
        messages={messages}
        onApproval={toolApprovalDecision.openDecision}
        onInteraction={userInteractionResponse.respond}
        onTraceActionRule={safetyPolicyActionRule.saveActionRule}
        policyRuleBusy={safetyPolicyActionRule.busyKey}
        onEdit={messageHistoryActions.startEditMessage}
        onDelete={messageHistoryActions.deleteMessage}
      />

      <ChatComposerArea
        attachments={chatAttachments.attachments}
        fileInputRef={chatAttachments.fileInputRef}
        input={input}
        isDragging={chatAttachments.isDragging}
        isStreaming={isStreaming}
        pendingAttention={pendingAttention}
        policyRuleBusy={safetyPolicyActionRule.busyKey}
        quickCommands={quickCommands}
        textareaRef={textareaRef}
        uploadingAttachment={chatAttachments.uploading}
        visiblePolicyBlock={visiblePolicyBlock}
        visibleSlashCommands={visibleSlashCommands}
        onApproval={toolApprovalDecision.openDecision}
        onApplySlashCommand={inputDrafts.applySlashCommand}
        onDismissPolicyBlock={() => visiblePolicyBlock && setDismissedPolicyBlockKey(policyBlockKey(visiblePolicyBlock))}
        onDragLeave={chatAttachments.handleDragLeave}
        onDragOver={chatAttachments.handleDragOver}
        onDrop={chatAttachments.handleDrop}
        onFiles={chatAttachments.handleFiles}
        onHistoryReset={() => inputDrafts.setHistoryIndex(null)}
        onInputChange={inputDrafts.setInput}
        onInteraction={userInteractionResponse.respond}
        onKeyDown={handleKeyDown}
        onManageCommands={commandManager.openManager}
        onPaste={chatAttachments.handleInputPaste}
        onRemoveAttachment={chatAttachments.removeAttachment}
        onSend={() => sendMessage()}
        onStop={stopStreaming}
        onTraceActionRule={safetyPolicyActionRule.saveActionRule}
      />
    </div>
    </>
  )
}
