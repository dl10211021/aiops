import { streamChat } from '@/api/client'
import type { ChatMessage } from '@/types'
import { applyChatStreamEvent } from './chatStreamEvents'
import { consumeChatStream } from './chatStreamReader'
import { applyChatStreamingFailure } from './chatStreamingLifecycle'

type AttachmentPayload = Array<{
  filename: string
  ext: string
  size: number
  content_type?: string
  kind?: string
  rows?: number
  pages?: number
  sheets?: string[]
  truncated?: boolean
  data_url?: string | null
}>

type AddToast = (message: string, type?: 'success' | 'error' | 'info') => void
type UpdateLastAssistantMessage = (sessionId: string, updater: (message: ChatMessage) => ChatMessage) => void
type ScheduledFlush = ReturnType<typeof window.setTimeout> | number | null
const STREAM_FLUSH_INTERVAL_MS = 48
const LONG_STREAM_FLUSH_INTERVAL_MS = 96
const HUGE_STREAM_FLUSH_INTERVAL_MS = 160

function streamString(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback
}

export async function runChatStream({
  addToast,
  attachmentPayload,
  controller,
  displayContent,
  modelMessageContent,
  modelName,
  orchestrationMode,
  sessionId,
  thinkingMode,
  updateLastAssistantMessage,
}: {
  addToast: AddToast
  attachmentPayload: AttachmentPayload
  controller: AbortController
  displayContent: string
  modelMessageContent: string
  modelName: string
  orchestrationMode: 'single' | 'split' | 'fast'
  sessionId: string
  thinkingMode: string
  updateLastAssistantMessage: UpdateLastAssistantMessage
}) {
  let accumulatedMarkdown = ''
  let renderedMarkdown = ''
  let scheduledFlush: ScheduledFlush = null

  const flushMarkdown = () => {
    scheduledFlush = null
    if (renderedMarkdown === accumulatedMarkdown) return
    renderedMarkdown = accumulatedMarkdown
    updateLastAssistantMessage(sessionId, (message) => ({
      ...message,
      content: renderedMarkdown,
    }))
  }

  const scheduleMarkdownFlush = () => {
    if (scheduledFlush !== null) return
    const interval = accumulatedMarkdown.length > 48_000
      ? HUGE_STREAM_FLUSH_INTERVAL_MS
      : accumulatedMarkdown.length > 14_000
        ? LONG_STREAM_FLUSH_INTERVAL_MS
        : STREAM_FLUSH_INTERVAL_MS
    scheduledFlush = window.setTimeout(flushMarkdown, interval)
  }

  try {
    const response = await streamChat(
      sessionId,
      modelMessageContent,
      modelName,
      thinkingMode,
      orchestrationMode,
      displayContent,
      attachmentPayload,
      controller.signal,
    )
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || `HTTP Error ${response.status}: ${response.statusText}`)
    }
    await consumeChatStream(response, (data) => {
      if (data.type === 'chunk') {
        accumulatedMarkdown += streamString(data.content)
        scheduleMarkdownFlush()
        return false
      }
      flushMarkdown()
      const result = applyChatStreamEvent({
        sessionId,
        data,
        accumulatedMarkdown,
        updateLastAssistantMessage,
      })
      accumulatedMarkdown = result.accumulatedMarkdown
      return result.done
    })
    flushMarkdown()
  } catch (err: unknown) {
    flushMarkdown()
    applyChatStreamingFailure({
      err,
      sessionId,
      addToast,
      updateLastAssistantMessage,
    })
  }
}
