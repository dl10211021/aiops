import type { ChatMessage } from '@/types'

export interface SessionHistoryMessage {
  role: string
  content: string
  _memory_id?: number
  attachments?: ChatMessage['attachments']
}

export function normalizeHistoryMessages(sessionId: string, messages: SessionHistoryMessage[]): ChatMessage[] {
  return messages.map((message, index) => ({
    id: message._memory_id ? `mem-${message._memory_id}` : `hist-${sessionId}-${index}`,
    memoryId: message._memory_id,
    _memory_id: message._memory_id,
    role: message.role as 'user' | 'assistant',
    content: message.content,
    attachments: message.attachments,
    timestamp: Date.now() - (messages.length - index) * 1000,
  }))
}

export function messageMemoryId(message: ChatMessage) {
  return message.memoryId || message._memory_id
}
