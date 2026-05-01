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

export async function runChatStream({
  addToast,
  attachmentPayload,
  controller,
  displayContent,
  modelMessageContent,
  modelName,
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
  sessionId: string
  thinkingMode: string
  updateLastAssistantMessage: UpdateLastAssistantMessage
}) {
  let accumulatedMarkdown = ''

  try {
    const response = await streamChat(
      sessionId,
      modelMessageContent,
      modelName,
      thinkingMode,
      displayContent,
      attachmentPayload,
      controller.signal,
    )
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || `HTTP Error ${response.status}: ${response.statusText}`)
    }
    await consumeChatStream(response, (data) => {
      const result = applyChatStreamEvent({
        sessionId,
        data,
        accumulatedMarkdown,
        updateLastAssistantMessage,
      })
      accumulatedMarkdown = result.accumulatedMarkdown
      return result.done
    })
  } catch (err: unknown) {
    applyChatStreamingFailure({
      err,
      sessionId,
      addToast,
      updateLastAssistantMessage,
    })
  }
}
