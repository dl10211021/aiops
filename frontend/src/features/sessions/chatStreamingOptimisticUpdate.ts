import type { Dispatch, SetStateAction } from 'react'
import type { ChatMessage, Session } from '@/types'
import type { ChatAttachmentPreview } from './chatTypes'

type AppendMessage = (sessionId: string, message: ChatMessage) => void
type UpdateSession = (sessionId: string, patch: Partial<Session>) => void

export function applyOutgoingChatOptimisticUpdate({
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
}: {
  activeAttachments: ChatAttachmentPreview[]
  appendMessage: AppendMessage
  assistantMessage: ChatMessage
  revokeAttachmentPreviews: (items: ChatAttachmentPreview[]) => void
  sessionId: string
  setAttachmentsBySession: Dispatch<SetStateAction<Record<string, ChatAttachmentPreview[]>>>
  setDraftsBySession: Dispatch<SetStateAction<Record<string, string>>>
  setHistoryIndex: Dispatch<SetStateAction<number | null>>
  setInputHistory: Dispatch<SetStateAction<string[]>>
  text: string
  updateSession: UpdateSession
  userMessage: ChatMessage
}) {
  if (text) setInputHistory((prev) => [text, ...prev.filter((item) => item !== text)].slice(0, 20))
  setHistoryIndex(null)
  appendMessage(sessionId, userMessage)
  setDraftsBySession((prev) => ({ ...prev, [sessionId]: '' }))
  revokeAttachmentPreviews(activeAttachments)
  setAttachmentsBySession((prev) => ({ ...prev, [sessionId]: [] }))
  appendMessage(sessionId, assistantMessage)
  updateSession(sessionId, { isStreaming: true, backendStreaming: true })
}
