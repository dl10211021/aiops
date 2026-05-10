import { useCallback, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { stopChat } from '@/api/client'
import { useStore } from '@/store'
import type { ChatAttachmentPreview } from './chatTypes'
import {
  finishStreamingSession,
  releaseStreamController,
} from './chatStreamingLifecycle'
import {
  createOutgoingChatMessages,
  resolveOutgoingChatContext,
  shouldRequestReadWriteConfirmation,
} from './chatStreamingMessages'
import { applyOutgoingChatOptimisticUpdate } from './chatStreamingOptimisticUpdate'
import { runChatStream } from './chatStreamingRunner'

interface ReadWriteConfirmation {
  sessionId: string
  message: string
  remember: boolean
}

interface UseChatStreamingArgs {
  currentSessionId: string | null
  input: string
  draftsBySession: Record<string, string>
  attachments: ChatAttachmentPreview[]
  attachmentsBySession: Record<string, ChatAttachmentPreview[]>
  readWriteWarningEnabled: boolean
  modelName: string
  orchestrationMode: 'single' | 'split' | 'fast'
  thinkingMode: string
  setReadWriteConfirm: (confirmation: ReadWriteConfirmation | null) => void
  setInputHistory: Dispatch<SetStateAction<string[]>>
  setHistoryIndex: Dispatch<SetStateAction<number | null>>
  setDraftsBySession: Dispatch<SetStateAction<Record<string, string>>>
  revokeAttachmentPreviews: (items: ChatAttachmentPreview[]) => void
  setAttachmentsBySession: Dispatch<SetStateAction<Record<string, ChatAttachmentPreview[]>>>
}

export function useChatStreaming({
  currentSessionId,
  input,
  draftsBySession,
  attachments,
  attachmentsBySession,
  readWriteWarningEnabled,
  modelName,
  orchestrationMode,
  thinkingMode,
  setReadWriteConfirm,
  setInputHistory,
  setHistoryIndex,
  setDraftsBySession,
  revokeAttachmentPreviews,
  setAttachmentsBySession,
}: UseChatStreamingArgs) {
  const appendMessage = useStore((state) => state.appendMessage)
  const setSessionMessages = useStore((state) => state.setSessionMessages)
  const updateLastAssistantMessage = useStore((state) => state.updateLastAssistantMessage)
  const removeEmptyAssistantMessages = useStore((state) => state.removeEmptyAssistantMessages)
  const updateSession = useStore((state) => state.updateSession)
  const chatController = useStore((state) => state.chatController)
  const setChatController = useStore((state) => state.setChatController)
  const addToast = useStore((state) => state.addToast)
  const streamControllersRef = useRef<Record<string, AbortController>>({})

  const hasActiveStream = useCallback((sessionId: string) => {
    return Boolean(streamControllersRef.current[sessionId])
  }, [])

  const sendMessage = useCallback(async (forcedMessage?: string, forcedSessionId?: string) => {
    const sessions = useStore.getState().sessions
    const outgoing = resolveOutgoingChatContext({
      attachments,
      attachmentsBySession,
      currentSessionId,
      draftsBySession,
      forcedMessage,
      forcedSessionId,
      input,
      sessions,
    })
    const { activeAttachments, activeSession, displayContent, modelMessageContent, sessionId, text } = outgoing
    if (!outgoing.canSend || !sessionId) return

    if (shouldRequestReadWriteConfirmation({
      forcedMessage,
      readWriteWarningEnabled,
      session: activeSession,
      sessionId,
    })) {
      setReadWriteConfirm({ sessionId, message: text, remember: false })
      return
    }

    const { assistantMessage, attachmentPayload, userMessage } = createOutgoingChatMessages(displayContent, activeAttachments)
    applyOutgoingChatOptimisticUpdate({
      activeAttachments,
      appendMessage,
      assistantMessage,
      revokeAttachmentPreviews,
      sessionId,
      setAttachmentsBySession,
      setDraftsBySession,
      setHistoryIndex,
      setInputHistory,
      text,
      updateSession,
      userMessage,
    })

    const controller = new AbortController()
    streamControllersRef.current[sessionId] = controller
    setChatController(controller)

    try {
      const effectiveThinkingMode = orchestrationMode === 'fast' ? 'off' : thinkingMode
      await runChatStream({
        addToast,
        attachmentPayload,
        controller,
        displayContent,
        sessionId,
        modelMessageContent,
        modelName,
        orchestrationMode,
        thinkingMode: effectiveThinkingMode,
        updateLastAssistantMessage,
      })
    } finally {
      await finishStreamingSession({
        controller,
        removeEmptyAssistantMessages,
        sessionId,
        setChatController,
        setSessionMessages,
        streamControllersRef,
        updateSession,
      })
    }
  }, [
    addToast,
    appendMessage,
    attachments,
    attachmentsBySession,
    currentSessionId,
    draftsBySession,
    input,
    modelName,
    orchestrationMode,
    readWriteWarningEnabled,
    removeEmptyAssistantMessages,
    revokeAttachmentPreviews,
    setAttachmentsBySession,
    setChatController,
    setDraftsBySession,
    setHistoryIndex,
    setInputHistory,
    setReadWriteConfirm,
    setSessionMessages,
    thinkingMode,
    updateLastAssistantMessage,
    updateSession,
  ])

  const stopStreaming = useCallback(async () => {
    const sessionId = currentSessionId
    if (!sessionId) return
    const controller = streamControllersRef.current[sessionId] || chatController
    controller?.abort()
    try {
      await stopChat(sessionId)
    } catch {
      // Stop is best effort; the UI state still needs to leave streaming mode.
    }
    removeEmptyAssistantMessages(sessionId)
    updateSession(sessionId, { isStreaming: false, backendStreaming: false })
    releaseStreamController({
      clearWhenMissing: true,
      controller,
      sessionId,
      setChatController,
      streamControllersRef,
    })
  }, [chatController, currentSessionId, removeEmptyAssistantMessages, setChatController, updateSession])

  return {
    hasActiveStream,
    sendMessage,
    stopStreaming,
  }
}
