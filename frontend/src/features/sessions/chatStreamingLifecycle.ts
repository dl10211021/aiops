import type { MutableRefObject } from 'react'
import { getSessionHistory } from '@/api/client'
import { useStore } from '@/store'
import type { ChatMessage, Session } from '@/types'
import { normalizeHistoryMessages } from './sessionHistory'

type AddToast = (message: string, type?: 'success' | 'error' | 'info') => void
type SetChatController = (controller: AbortController | null) => void
type SetSessionMessages = (sessionId: string, messages: ChatMessage[]) => void
type UpdateLastAssistantMessage = (sessionId: string, updater: (message: ChatMessage) => ChatMessage) => void
type RemoveEmptyAssistantMessages = (sessionId: string) => void
type UpdateSession = (sessionId: string, patch: Partial<Session>) => void

export function applyChatStreamingFailure({
  err,
  sessionId,
  addToast,
  updateLastAssistantMessage,
}: {
  err: unknown
  sessionId: string
  addToast: AddToast
  updateLastAssistantMessage: UpdateLastAssistantMessage
}) {
  if (err instanceof Error && err.name === 'AbortError') {
    updateLastAssistantMessage(sessionId, (message) => ({
      ...message,
      content: `${message.content}\n\n已中止`,
    }))
    return
  }

  const errMsg = err instanceof Error ? err.message : 'Network error'
  addToast(errMsg, 'error')
  updateLastAssistantMessage(sessionId, (message) => ({
    ...message,
    content: message.content || `\n\n消息发送失败：${errMsg}`,
  }))
}

export async function refreshStreamingSessionHistory(
  sessionId: string,
  setSessionMessages: SetSessionMessages,
) {
  try {
    const history = await getSessionHistory(sessionId)
    setSessionMessages(sessionId, normalizeHistoryMessages(sessionId, history.data.messages || []))
  } catch {
    // Keep current in-memory transcript if history refresh fails.
  }
}

export function releaseStreamController({
  clearWhenMissing = false,
  controller,
  sessionId,
  setChatController,
  streamControllersRef,
}: {
  clearWhenMissing?: boolean
  controller: AbortController | null | undefined
  sessionId: string
  setChatController: SetChatController
  streamControllersRef: MutableRefObject<Record<string, AbortController>>
}) {
  if (controller && streamControllersRef.current[sessionId] === controller) {
    delete streamControllersRef.current[sessionId]
  }
  if ((!controller && clearWhenMissing) || (controller && useStore.getState().chatController === controller)) {
    setChatController(null)
  }
}

export async function finishStreamingSession({
  controller,
  removeEmptyAssistantMessages,
  sessionId,
  setChatController,
  setSessionMessages,
  streamControllersRef,
  updateSession,
}: {
  controller: AbortController
  removeEmptyAssistantMessages: RemoveEmptyAssistantMessages
  sessionId: string
  setChatController: SetChatController
  setSessionMessages: SetSessionMessages
  streamControllersRef: MutableRefObject<Record<string, AbortController>>
  updateSession: UpdateSession
}) {
  removeEmptyAssistantMessages(sessionId)
  await refreshStreamingSessionHistory(sessionId, setSessionMessages)
  updateSession(sessionId, { isStreaming: false, backendStreaming: false })
  releaseStreamController({
    controller,
    sessionId,
    setChatController,
    streamControllersRef,
  })
}
