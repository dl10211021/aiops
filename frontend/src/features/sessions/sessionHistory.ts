import type { ChatMessage } from '@/types'

export interface SessionHistoryMessage {
  role: string
  content: string
  _memory_id?: number
  attachments?: ChatMessage['attachments']
  exec_trace?: ChatMessage['execTrace']
  execTrace?: ChatMessage['execTrace']
  timestamp?: number | string
  created_at?: string
}

function parseHistoryTimestamp(message: SessionHistoryMessage) {
  if (typeof message.timestamp === 'number') return message.timestamp
  const raw = typeof message.timestamp === 'string'
    ? message.timestamp
    : message.created_at
  if (!raw) return NaN
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(raw)
    ? `${raw.replace(' ', 'T')}Z`
    : raw
  return Date.parse(normalized)
}

export function normalizeHistoryMessages(sessionId: string, messages: SessionHistoryMessage[]): ChatMessage[] {
  return messages.map((message, index) => {
    const parsedTimestamp = parseHistoryTimestamp(message)
    return {
      id: message._memory_id ? `mem-${message._memory_id}` : `hist-${sessionId}-${index}`,
      memoryId: message._memory_id,
      _memory_id: message._memory_id,
      role: message.role as 'user' | 'assistant',
      content: message.content,
      attachments: message.attachments,
      execTrace: message.execTrace || message.exec_trace,
      timestamp: Number.isFinite(parsedTimestamp)
        ? parsedTimestamp
        : Date.now() - (messages.length - index) * 1000,
    }
  })
}

export function messageMemoryId(message: ChatMessage) {
  return message.memoryId || message._memory_id
}
