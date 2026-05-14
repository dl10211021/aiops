import type { ChatMessage, ExecTraceItem, MemoryReference, ToolApproval, UserInteractionRequest } from '@/types'
import { resolveApprovalFromToolEnd } from './chatAttention'
import { completeLastTrace } from './traceUtils'

interface ApplyChatStreamEventArgs {
  sessionId: string
  data: Record<string, unknown>
  accumulatedMarkdown: string
  updateLastAssistantMessage: (sessionId: string, updater: (message: ChatMessage) => ChatMessage) => void
}

interface ApplyChatStreamEventResult {
  done: boolean
  accumulatedMarkdown: string
}

function streamString(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback
}

function streamArgs(value: unknown) {
  return typeof value === 'string' ? value : JSON.stringify(value || {})
}

function streamMemoryRefs(value: unknown): MemoryReference[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is MemoryReference => (
    Boolean(item) && typeof item === 'object' && !Array.isArray(item)
  ))
}

function streamRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined
}

export function applyChatStreamEvent({
  sessionId,
  data,
  accumulatedMarkdown,
  updateLastAssistantMessage,
}: ApplyChatStreamEventArgs): ApplyChatStreamEventResult {
  const type = streamString(data.type)

  switch (type) {
    case 'status':
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        runtimeEvents: [
          ...(message.runtimeEvents || []),
          {
            type: 'status' as const,
            content: streamString(data.content, '运行中...'),
            timestamp: Date.now(),
          },
        ].slice(-80),
      }))
      return { done: false, accumulatedMarkdown }

    case 'tool_start':
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        execTrace: [...(message.execTrace || []), {
          type: 'tool_start',
          toolCallId: streamString(data.id ?? data.tool_call_id),
          tool: streamString(data.tool, 'unknown'),
          args: streamArgs(data.args ?? data.cmd),
          resultMeta: streamRecord(data.result_meta),
          status: 'running',
          startedAt: typeof data.started_at === 'number' ? data.started_at : Date.now(),
        } as ExecTraceItem],
      }))
      return { done: false, accumulatedMarkdown }

    case 'tool_end':
      updateLastAssistantMessage(sessionId, (message) => resolveApprovalFromToolEnd({
        ...message,
        execTrace: completeLastTrace(message.execTrace || [], data),
      }, data))
      return { done: false, accumulatedMarkdown }

    case 'tool_ask_approval': {
      const approval: ToolApproval = {
        toolCallId: streamString(data.tool_call_id),
        toolName: streamString(data.tool_name, 'unknown'),
        args: streamArgs(data.args),
        reason: streamString(data.reason),
        actions: Array.isArray(data.actions) ? data.actions : [],
        primaryAction: data.primary_action && typeof data.primary_action === 'object'
          ? data.primary_action as ToolApproval['primaryAction']
          : null,
        toolPolicy: streamRecord(data.tool_policy) || null,
        uniqueId: `approval-${Date.now()}`,
        resolved: false,
      }
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        toolApproval: approval,
      }))
      return { done: false, accumulatedMarkdown }
    }

    case 'user_interaction_request': {
      const options = Array.isArray(data.options)
        ? data.options
          .filter((item: unknown) => item && typeof item === 'object')
          .map((item: Record<string, unknown>) => ({
            label: String(item.label || item.value || '选项'),
            value: String(item.value || item.label || ''),
            description: item.description ? String(item.description) : undefined,
          }))
        : []
      const interaction: UserInteractionRequest = {
        requestId: streamString(data.request_id),
        prompt: streamString(data.prompt, '请补充信息'),
        inputType: streamString(data.input_type, 'text'),
        options,
        placeholder: streamString(data.placeholder),
        required: data.required !== false,
        timeoutSeconds: Number(data.timeout_seconds || 300),
        resolved: false,
      }
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        userInteraction: interaction,
      }))
      return { done: false, accumulatedMarkdown }
    }

    case 'user_interaction_done': {
      const requestId = streamString(data.request_id)
      if (!requestId) return { done: false, accumulatedMarkdown }
      const updater = (message: ChatMessage) => {
        const interaction = message.userInteraction
        if (!interaction || interaction.requestId !== requestId) return message
        const displayValue = interaction.inputType === 'password' && data.value ? '******' : String(data.value || '')
        return {
          ...message,
          userInteraction: {
            ...interaction,
            resolved: true,
            status: streamString(data.status, 'submitted'),
            value: displayValue,
            label: streamString(data.label),
          },
        }
      }
      updateLastAssistantMessage(sessionId, updater)
      return { done: false, accumulatedMarkdown }
    }

    case 'chunk': {
      const nextMarkdown = accumulatedMarkdown + streamString(data.content)
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        content: nextMarkdown,
      }))
      return { done: false, accumulatedMarkdown: nextMarkdown }
    }

    case 'memory_refs': {
      const refs = streamMemoryRefs(data.refs || data.memory_refs || data.memoryRefs)
      if (!refs.length) return { done: false, accumulatedMarkdown }
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        memoryRefs: refs,
        memory_refs: refs,
      }))
      return { done: false, accumulatedMarkdown }
    }

    case 'error':
      updateLastAssistantMessage(sessionId, (message) => ({
        ...message,
        content: `${message.content}\n\n错误：${streamString(data.content, '未知错误')}`,
      }))
      return { done: false, accumulatedMarkdown }

    case 'done':
      return { done: true, accumulatedMarkdown }

    default:
      return { done: false, accumulatedMarkdown }
  }
}
