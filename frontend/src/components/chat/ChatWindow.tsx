import { useRef, useEffect, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent, MouseEvent as ReactMouseEvent } from 'react'
import { useStore } from '@/store'
import AssetProfilePanel from '@/features/sessions/AssetProfilePanel'
import AiThinkingChainPanel from '@/features/sessions/AiThinkingChainPanel'
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

const rightPanelStorageKey = 'opscore_chat_right_panel_width_v2'
const rightPanelCollapsedStorageKey = 'opscore_chat_right_panel_collapsed'
const defaultRightPanelWidth = 460
const wideRightPanelWidth = 640
const minRightPanelWidth = 340
const maxRightPanelWidth = 760
const orchestrationModeStorageKey = 'opscore_chat_orchestration_mode'

export default function ChatWindow() {
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)
  const setView = useStore((s) => s.setView)

  const [readWriteConfirm, setReadWriteConfirm] = useState<{ sessionId: string; message: string; remember: boolean } | null>(null)
  const [dismissedPolicyBlockKey, setDismissedPolicyBlockKey] = useState<string | null>(null)
  const [rightPanelWidth, setRightPanelWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return defaultRightPanelWidth
    const storedWidth = Number(localStorage.getItem(rightPanelStorageKey))
    if (Number.isFinite(storedWidth)) {
      return Math.min(Math.max(storedWidth, minRightPanelWidth), maxRightPanelWidth)
    }
    return defaultRightPanelWidth
  })
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem(rightPanelCollapsedStorageKey) === '1'
  })
  const [isResizing, setIsResizing] = useState(false)
  const [profileFocusPulse, setProfileFocusPulse] = useState(false)
  const [selectedSlashCommandIndex, setSelectedSlashCommandIndex] = useState(0)
  const [orchestrationMode, setOrchestrationModeState] = useState<'single' | 'split'>(() => {
    if (typeof window === 'undefined') return 'single'
    return localStorage.getItem(orchestrationModeStorageKey) === 'split' ? 'split' : 'single'
  })
  const dragStartRef = useRef<{ startX: number; startWidth: number } | null>(null)
  const rightPanelWidthRef = useRef(defaultRightPanelWidth)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const profilePanelRef = useRef<HTMLDivElement>(null)
  const profileFocusTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
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

  useEffect(() => {
    setSelectedSlashCommandIndex(0)
  }, [input, visibleSlashCommands.length])

  useEffect(() => {
    const handleProfileFocus = () => {
      setView('chat')
      setRightPanelCollapsed(false)
      localStorage.setItem(rightPanelCollapsedStorageKey, '0')
      const nextWidth = Math.max(rightPanelWidthRef.current, defaultRightPanelWidth)
      rightPanelWidthRef.current = nextWidth
      setRightPanelWidth(nextWidth)
      localStorage.setItem(rightPanelStorageKey, String(nextWidth))
      if (!assetProfile.open && assetProfile.profile) {
        assetProfile.toggle()
      }
      window.setTimeout(() => {
        profilePanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 80)
      setProfileFocusPulse(true)
      if (profileFocusTimeoutRef.current) {
        window.clearTimeout(profileFocusTimeoutRef.current)
      }
      profileFocusTimeoutRef.current = window.setTimeout(() => {
        setProfileFocusPulse(false)
      }, 2200)
    }
    window.addEventListener('opscore:session-profile-focus', handleProfileFocus)
    return () => {
      window.removeEventListener('opscore:session-profile-focus', handleProfileFocus)
      if (profileFocusTimeoutRef.current) {
        window.clearTimeout(profileFocusTimeoutRef.current)
      }
    }
  }, [assetProfile, setView])

  const { sendMessage, stopStreaming, hasActiveStream } = useChatStreaming({
    currentSessionId,
    sessions,
    input,
    draftsBySession: inputDrafts.draftsBySession,
    attachments: chatAttachments.attachments,
    attachmentsBySession: chatAttachments.attachmentsBySession,
    readWriteWarningEnabled,
    modelName,
    orchestrationMode,
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

  useEffect(() => {
    rightPanelWidthRef.current = rightPanelWidth
  }, [rightPanelWidth])

  useEffect(() => {
    if (!isResizing) return

    const onMouseMove = (event: MouseEvent) => {
      if (!dragStartRef.current) return
      const delta = dragStartRef.current.startX - event.clientX
      const width = Math.min(Math.max(dragStartRef.current.startWidth + delta, minRightPanelWidth), maxRightPanelWidth)
      rightPanelWidthRef.current = width
      setRightPanelWidth(width)
    }

    const onMouseUp = () => {
      dragStartRef.current = null
      localStorage.setItem(rightPanelStorageKey, String(rightPanelWidthRef.current))
      setIsResizing(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.nativeEvent.isComposing) return

    if (visibleSlashCommands.length > 0) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedSlashCommandIndex((current) => {
          const delta = e.key === 'ArrowDown' ? 1 : -1
          return (current + delta + visibleSlashCommands.length) % visibleSlashCommands.length
        })
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        const command = visibleSlashCommands[selectedSlashCommandIndex] || visibleSlashCommands[0]
        if (command) inputDrafts.applySlashCommand(command.prompt)
        return
      }
    }

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

  const handleResizeStart = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (rightPanelCollapsed) return
    if (event.button !== 0) return
    event.preventDefault()
    dragStartRef.current = {
      startX: event.clientX,
      startWidth: rightPanelWidth,
    }
    setIsResizing(true)
  }

  const handleResizeKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      toggleRightPanel()
      return
    }
    if (rightPanelCollapsed) return
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const delta = event.key === 'ArrowLeft' ? 24 : -24
    setRightPanelWidth((current) => {
      const next = Math.min(Math.max(current + delta, minRightPanelWidth), maxRightPanelWidth)
      rightPanelWidthRef.current = next
      localStorage.setItem(rightPanelStorageKey, String(next))
      return next
    })
  }

  const toggleRightPanel = () => {
    setRightPanelCollapsed((current) => {
      const next = !current
      localStorage.setItem(rightPanelCollapsedStorageKey, next ? '1' : '0')
      return next
    })
  }

  const toggleWideRightPanel = () => {
    const next = rightPanelWidth < wideRightPanelWidth ? wideRightPanelWidth : defaultRightPanelWidth
    rightPanelWidthRef.current = next
    setRightPanelWidth(next)
    localStorage.setItem(rightPanelStorageKey, String(next))
  }

  const setOrchestrationMode = (mode: 'single' | 'split') => {
    setOrchestrationModeState(mode)
    localStorage.setItem(orchestrationModeStorageKey, mode)
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
    <section className="flex min-h-0 min-w-0 overflow-hidden rounded-lg border border-ops-surface1/80 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
      <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
        <div className="flex h-full min-h-0 min-w-0 flex-col">
          <SessionToolsetBar
            catalog={toolCatalog}
            session={session}
            availableModels={availableModels}
            modelName={modelName}
            orchestrationMode={orchestrationMode}
            thinkingMode={thinkingMode}
            onModelChange={setModelName}
            onOrchestrationModeChange={setOrchestrationMode}
            onThinkingModeChange={setThinkingMode}
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
            onFeedback={messageHistoryActions.feedbackMessage}
            showInlineTrace={false}
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
            selectedSlashCommandIndex={selectedSlashCommandIndex}
            onApproval={toolApprovalDecision.openDecision}
            onApplySlashCommand={inputDrafts.applySlashCommand}
            onSlashCommandIndexChange={setSelectedSlashCommandIndex}
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
      </div>
      <div
        className={`z-10 flex w-3 items-stretch justify-center border-l border-ops-surface1/80 ${
          rightPanelCollapsed
            ? 'pointer-events-none opacity-0'
            : isResizing
              ? 'cursor-col-resize bg-ops-accent/25'
              : 'cursor-col-resize bg-ops-surface0/40 hover:bg-ops-accent/20'
        }`}
        role="separator"
        aria-orientation="vertical"
        aria-valuemin={minRightPanelWidth}
        aria-valuemax={maxRightPanelWidth}
        aria-valuenow={rightPanelWidth}
        tabIndex={0}
        onMouseDown={handleResizeStart}
        onKeyDown={handleResizeKeyDown}
      >
        <span className="my-3 w-[2px] rounded-full bg-ops-surface0/90" />
      </div>
      <section
        className="flex min-h-0 min-w-0 shrink-0 flex-col overflow-hidden border-l border-ops-surface1/80 bg-ops-panel/95 transition-[width] duration-200"
        style={{ width: rightPanelCollapsed ? '48px' : `${rightPanelWidth}px` }}
      >
        <div className="flex h-10 shrink-0 items-center justify-between border-b border-ops-surface0/80 bg-ops-dark px-2">
          {!rightPanelCollapsed && (
            <span className="truncate text-xs font-semibold text-ops-text">会话侧栏</span>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            {!rightPanelCollapsed && (
              <button
                type="button"
                onClick={toggleWideRightPanel}
                className="h-7 rounded-md border border-ops-surface1 px-2 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
                title={rightPanelWidth < wideRightPanelWidth ? '放大右侧栏' : '恢复普通宽度'}
                aria-label={rightPanelWidth < wideRightPanelWidth ? '放大右侧栏' : '恢复普通宽度'}
              >
                {rightPanelWidth < wideRightPanelWidth ? '⤢' : '⤡'}
              </button>
            )}
            <button
              type="button"
              onClick={toggleRightPanel}
              className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-ops-surface1 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
              title={rightPanelCollapsed ? '展开右侧栏' : '收起右侧栏'}
              aria-label={rightPanelCollapsed ? '展开右侧栏' : '收起右侧栏'}
            >
              {rightPanelCollapsed ? '‹' : '›'}
            </button>
          </div>
        </div>
        {rightPanelCollapsed ? (
          <button
            type="button"
            onClick={toggleRightPanel}
            className="flex min-h-0 flex-1 items-center justify-center px-2 text-xs font-semibold text-ops-subtext hover:text-ops-accent"
            title="展开右侧栏"
          >
            <span className="[writing-mode:vertical-rl]">画像 / 思维链</span>
          </button>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <div
              ref={profilePanelRef}
              className={`transition-[box-shadow,filter] duration-300 ${
                profileFocusPulse ? 'ring-2 ring-ops-accent/70 drop-shadow-[0_0_18px_rgba(45,212,191,0.35)]' : ''
              }`}
            >
              <AssetProfilePanel
                session={session}
                profile={assetProfile.profile}
                open={assetProfile.open}
                busy={assetProfile.busy}
                onToggle={assetProfile.toggle}
                onGenerate={assetProfile.generate}
              />
            </div>
            <AiThinkingChainPanel
              sessionId={currentSessionId}
              messages={messages}
            />
          </div>
        )}
      </section>
    </section>
    </>
  )
}
