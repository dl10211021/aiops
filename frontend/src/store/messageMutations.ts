import type { ChatMessage, Session } from '@/types'
import { hasMeaningfulAssistantPayload } from './messageState'

type MessageStateSnapshot = {
  sessions: Record<string, Session>
}

export function appendMessageState(st: MessageStateSnapshot, sessionId: string, message: ChatMessage) {
  const session = st.sessions[sessionId]
  if (!session) return st
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages: [...session.messages, message] },
    },
  }
}

export function setSessionMessagesState(st: MessageStateSnapshot, sessionId: string, messages: ChatMessage[]) {
  const session = st.sessions[sessionId]
  if (!session) return st
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages },
    },
  }
}

export function removeMessageState(st: MessageStateSnapshot, sessionId: string, messageId: string) {
  const session = st.sessions[sessionId]
  if (!session) return st
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages: session.messages.filter((message) => message.id !== messageId) },
    },
  }
}

export function updateMessageState(
  st: MessageStateSnapshot,
  sessionId: string,
  messageId: string,
  updater: (message: ChatMessage) => ChatMessage,
) {
  const session = st.sessions[sessionId]
  if (!session) return st
  let changed = false
  const messages = session.messages.map((message) => {
    if (message.id !== messageId) return message
    changed = true
    return updater(message)
  })
  if (!changed) return st
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages },
    },
  }
}

export function updateLastAssistantMessageState(
  st: MessageStateSnapshot,
  sessionId: string,
  updater: (message: ChatMessage) => ChatMessage,
) {
  const session = st.sessions[sessionId]
  if (!session) return st
  const messages = [...session.messages]
  for (let index = messages.length - 1; index >= 0; index--) {
    if (messages[index].role === 'assistant') {
      messages[index] = updater(messages[index])
      break
    }
  }
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages },
    },
  }
}

export function removeEmptyAssistantMessagesState(st: MessageStateSnapshot, sessionId: string) {
  const session = st.sessions[sessionId]
  if (!session) return st
  const messages = session.messages.filter(hasMeaningfulAssistantPayload)
  if (messages.length === session.messages.length) return st
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages },
    },
  }
}

export function clearMessagesState(st: MessageStateSnapshot, sessionId: string) {
  const session = st.sessions[sessionId]
  if (!session) return st
  return {
    sessions: {
      ...st.sessions,
      [sessionId]: { ...session, messages: [] },
    },
  }
}
