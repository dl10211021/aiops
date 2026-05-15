import { streamChat } from '@/api/client'
import type { ChatMessage } from '@/types'
import { isRecord, responseErrorMessage } from '@/api/http'
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

function formatApprovalSource(label: string) {
  if (label === 'runtime_policy') return '运行时门禁'
  if (label === 'safety_policy') return '安全策略'
  if (label === 'action_policy') return '动作策略'
  return label
}

function formatApprovalSources(sources: unknown): string[] {
  if (!Array.isArray(sources)) return []
  return sources
    .map((source) => (typeof source === 'string' ? formatApprovalSource(source) : ''))
    .filter(Boolean)
}

function formatChatBackendApprovalMessage(errData: unknown, fallback: string) {
  if (!isRecord(errData)) return responseErrorMessage(errData, fallback)
  const detail = isRecord(errData.detail) ? errData.detail : errData
  if (!isRecord(detail) || String(detail.code || '') !== 'approval_required') {
    return responseErrorMessage(detail, fallback)
  }

  const base = responseErrorMessage(detail, fallback)
  const lines = [base]
  const approvalSources = formatApprovalSources(detail.approval_sources)
  if (approvalSources.length > 0) {
    lines.push(`门禁来源：${approvalSources.join(' / ')}`)
  }

  const safetyPolicy = isRecord(detail.safety_policy) ? detail.safety_policy : null
  if (safetyPolicy?.required) {
    const reason = String(safetyPolicy.reason || '').trim()
    if (reason) {
      lines.push(`安全策略：${reason}`)
    }
  }

  const runtimePolicy = isRecord(detail.runtime_policy) ? detail.runtime_policy : null
  if (runtimePolicy?.required) {
    const reason = String(runtimePolicy.reason || '').trim()
    if (reason) {
      lines.push(`运行时门禁：${reason}`)
    }
  }

  return lines.join('\n')
}

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
  analysisOnly = false,
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
  analysisOnly?: boolean
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
      analysisOnly,
    )
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(formatChatBackendApprovalMessage(
        errData,
        `HTTP Error ${response.status}: ${response.statusText}`,
      ))
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
