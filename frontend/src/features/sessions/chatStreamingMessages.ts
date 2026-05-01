import type { ChatMessage, Session } from '@/types'
import {
  chatAttachmentPayload,
  chatMessageAttachments,
  composeChatMessage,
} from './chatAttachments'
import type { ChatAttachmentPreview } from './chatTypes'

export interface OutgoingChatContext {
  activeAttachments: ChatAttachmentPreview[]
  activeSession: Session | null
  canSend: boolean
  displayContent: string
  modelMessageContent: string
  sessionId: string | null
  text: string
}

export function resolveOutgoingChatContext({
  attachments,
  attachmentsBySession,
  currentSessionId,
  draftsBySession,
  forcedMessage,
  forcedSessionId,
  input,
  sessions,
}: {
  attachments: ChatAttachmentPreview[]
  attachmentsBySession: Record<string, ChatAttachmentPreview[]>
  currentSessionId: string | null
  draftsBySession: Record<string, string>
  forcedMessage?: string
  forcedSessionId?: string
  input: string
  sessions: Record<string, Session>
}): OutgoingChatContext {
  const sessionId = forcedSessionId || currentSessionId
  const activeSession = sessionId ? sessions[sessionId] : null
  const draft = sessionId === currentSessionId ? input : (sessionId ? draftsBySession[sessionId] || '' : '')
  const text = (forcedMessage ?? draft).trim()
  const activeAttachments = sessionId === currentSessionId ? attachments : (sessionId ? attachmentsBySession[sessionId] || [] : [])
  const displayContent = text || '请阅读并分析本次随附附件。'
  return {
    activeAttachments,
    activeSession,
    canSend: Boolean((text || activeAttachments.length > 0) && sessionId && !activeSession?.isStreaming),
    displayContent,
    modelMessageContent: composeChatMessage(text, activeAttachments),
    sessionId,
    text,
  }
}

export function readWriteConfirmationKey(sessionId: string) {
  return `opscore_rw_confirmed_${sessionId}`
}

export function shouldRequestReadWriteConfirmation({
  forcedMessage,
  readWriteWarningEnabled,
  session,
  sessionId,
}: {
  forcedMessage?: string
  readWriteWarningEnabled: boolean
  session: Session | null
  sessionId: string
}) {
  if (forcedMessage || !session?.isReadWriteMode || !readWriteWarningEnabled) return false
  return sessionStorage.getItem(readWriteConfirmationKey(sessionId)) !== '1'
}

export function createOutgoingChatMessages(
  displayContent: string,
  activeAttachments: ChatAttachmentPreview[],
) {
  const userMessage: ChatMessage = {
    id: `u-${Date.now()}`,
    role: 'user',
    content: displayContent,
    timestamp: Date.now(),
    attachments: chatMessageAttachments(activeAttachments),
  }
  const assistantMessage: ChatMessage = {
    id: `a-${Date.now()}`,
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
    execTrace: [],
  }
  return {
    assistantMessage,
    attachmentPayload: chatAttachmentPayload(activeAttachments),
    userMessage,
  }
}
