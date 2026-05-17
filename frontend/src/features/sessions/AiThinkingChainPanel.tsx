import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type {
  ApprovalRequest,
  ChatMessage,
  ChatRuntimeEvent,
  ExecTraceItem,
  RunTraceAuditSummary,
  RunTraceEvent,
  RunTraceRun,
  SessionMemoryActivity,
  SessionRunLearningPreview,
} from '@/types'
import { getApproval } from '@/api/approvals'
import { isAbortError } from '@/api/http'
import {
  createSessionRunLearningCandidate,
  getSessionHistoryEvidenceTrace,
  getSessionMemoryActivity,
  getSessionRunLearningPreview,
  getSessionRunTrace,
  getSessionRunTraceAuditSummary,
} from '@/api/sessionHistory'
import { toolLabel } from '@/utils/assetDisplay'
import { ApprovalInfo, ApprovalStatusBadge } from '@/components/views/ApprovalCenterShared'
import { EvidenceReferenceChip } from '@/components/views/EvidenceReferenceChip'
import { ApprovalSourceSummary } from './ApprovalSourceSummary'
import { parseJsonRecord } from './jsonRecords'
import ToolTraceList from './ToolTraceList'
import { resultReason, traceExecutionText, traceTargetLabel } from './traceUtils'
import {
  commandActionFromTrace,
  evidenceLabel,
  evidenceToneClass,
  httpActionFromTrace,
  operationLabel,
  operationToneClass,
  recordValue,
  runtimeExecutionLabels,
  runtimePolicyLabels,
  sessionModePolicyLabel,
  sessionModePolicyToneClass,
  sqlActionFromTrace,
  toolPolicyFromTrace,
  toolPolicySearchText,
} from './toolPolicyPresentation'

interface AiThinkingChainPanelProps {
  sessionId: string | null
  messages: ChatMessage[]
  defaultTab?: 'trace' | 'memory'
  fixedTab?: 'trace' | 'memory'
  sessionMode?: 'readonly' | 'readwrite'
  traceLabel?: string
}

const collapsedGroupId = '__collapsed__'

interface ThinkingChainGroup {
  id: string
  userMessageId: string
  scrollMessageId: string
  turnNumber: number
  dateLabel: string
  startedAt: number
  outputAt?: number
  outputMessageId?: string
  userPrompt: string
  assistantSummary: string
  traces: ExecTraceItem[]
  runtimeEvents: ChatRuntimeEvent[]
}

function compactText(value: string, fallback: string, max = 96) {
  const text = value.replace(/\s+/g, ' ').trim() || fallback
  return text.length > max ? `${text.slice(0, max)}...` : text
}

function buildThinkingGroups(messages: ChatMessage[]): ThinkingChainGroup[] {
  const dailyTurnCount = new Map<string, number>()
  const groups: ThinkingChainGroup[] = []
  let currentGroup: ThinkingChainGroup | null = null

  messages.forEach((message, index) => {
    if (message.role === 'user') {
      const dateLabel = formatTimelineDate(message.timestamp)
      const turnNumber = (dailyTurnCount.get(dateLabel) || 0) + 1
      dailyTurnCount.set(dateLabel, turnNumber)
      currentGroup = {
        id: message.id || `turn-${turnNumber}-${index}`,
        userMessageId: message.id,
        scrollMessageId: message.id,
        turnNumber,
        dateLabel,
        startedAt: message.timestamp,
        userPrompt: compactText(message.content, `第 ${turnNumber} 轮用户请求`, 180),
        assistantSummary: '',
        traces: [],
        runtimeEvents: [],
      }
      groups.push(currentGroup)
      return
    }
    if (message.role !== 'assistant') return
    if (!currentGroup) {
      currentGroup = {
        id: message.id || `turn-1-${index}`,
        userMessageId: message.id,
        scrollMessageId: message.id,
        turnNumber: 1,
        dateLabel: formatTimelineDate(message.timestamp),
        startedAt: message.timestamp,
        userPrompt: `第 ${index + 1} 条消息前的用户请求`,
        assistantSummary: '',
        traces: [],
        runtimeEvents: [],
      }
      groups.push(currentGroup)
    }
    if (message.execTrace?.length) {
      currentGroup.traces.push(...message.execTrace)
    }
    if (message.runtimeEvents?.length) {
      currentGroup.runtimeEvents.push(...message.runtimeEvents)
    }
    if (message.content.trim()) {
      currentGroup.assistantSummary = compactText(message.content, 'AI 已输出结果', 180)
      currentGroup.outputMessageId = message.id
      currentGroup.outputAt = message.timestamp
      currentGroup.scrollMessageId = message.id
    }
  })

  return groups.map((group) => {
    const traces = dedupeTraces(group.traces)
    return {
      ...group,
      traces,
      runtimeEvents: dedupeRuntimeEvents(group.runtimeEvents),
    assistantSummary: group.assistantSummary || (
      traces.length > 0 || group.runtimeEvents.length > 0
        ? 'AI 已调用工具，结果汇总在左侧会话输出中。'
        : '本轮暂无 AI 输出摘要。'
    ),
    }
  })
}

function dedupeRuntimeEvents(events: ChatRuntimeEvent[]) {
  const seen = new Set<string>()
  const deduped: ChatRuntimeEvent[] = []
  for (const event of events) {
    const key = [event.type, event.content, event.timestamp].join('\u0001')
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(event)
  }
  return deduped
}

function dedupeTraces(traces: ExecTraceItem[]) {
  const seen = new Set<string>()
  const deduped: ExecTraceItem[] = []
  for (const trace of traces) {
    const key = [
      trace.tool,
      trace.args || '',
      trace.result || '',
      trace.evidenceId || trace.evidence?.evidence_id || '',
      trace.status || '',
      trace.startedAt || '',
      trace.completedAt || '',
    ].join('\u0001')
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(trace)
  }
  return deduped
}

function traceResultLabel(trace: ExecTraceItem) {
  if (trace.status === 'running') return '执行中'
  if (trace.status === 'error') return '失败'
  if (trace.resultMeta) {
    const summary = recordResultLabel(trace.resultMeta)
    if (summary) return summary
  }
  const parsed = parseJsonRecord(trace.result || '')
  if (parsed) {
    const summary = recordResultLabel(parsed)
    if (summary) return summary
  }
  if (trace.result?.trim()) return compactText(trace.result, '已完成', 72)
  return trace.status === 'done' ? '已完成' : '等待结果'
}

function traceResultDetail(trace: ExecTraceItem) {
  if (trace.evidence?.output_preview?.trim()) return trace.evidence.output_preview.trim()
  const parsed = parseJsonRecord(trace.result || '')
  if (parsed) {
    const output = parsed.output || parsed.stdout || parsed.result || parsed.data
    if (typeof output === 'string' && output.trim()) return output.trim()
    const error = parsed.stderr || parsed.error
    if (typeof error === 'string' && error.trim()) return error.trim()
  }
  return trace.result?.trim() || ''
}

function traceExecutionDetail(trace: ExecTraceItem) {
  const evidenceInput = trace.evidence?.input_summary || trace.evidence?.redacted_input || ''
  if (evidenceInput.trim()) return evidenceInput.trim()
  return traceExecutionText(trace).trim()
}

function traceEvidenceId(trace: ExecTraceItem) {
  return trace.evidenceId || trace.evidence?.evidence_id || ''
}

function tracePolicySearchText(trace: ExecTraceItem) {
  const httpAction = httpActionFromTrace(trace)
  const commandAction = commandActionFromTrace(trace)
  return [
    toolPolicySearchText(toolPolicyFromTrace(trace)),
    ...runtimeExecutionLabels(trace),
    sqlActionFromTrace(trace)?.searchText || '',
    httpAction?.searchText || '',
    commandAction?.searchText || '',
  ].filter(Boolean).join(' ')
}

function recordResultLabel(record: Record<string, unknown>) {
  const reason = record.reason || record.error
  if (typeof reason === 'string' && reason.trim()) return resultReason(record)
  const rawStatus = String(record.status || '').toUpperCase()
  if (rawStatus === 'BLOCKED' || rawStatus === 'ERROR' || rawStatus === 'FAILED') return resultReason(record)
  const message = record.message
  if (typeof message === 'string' && message.trim()) return compactText(message, '已完成', 72)
  const output = record.output || record.stdout || record.result
  if (typeof output === 'string' && output.trim()) {
    const firstUsefulLine = output.split(/\r?\n/).map((line) => line.trim()).find(Boolean)
    return compactText(firstUsefulLine || output, '已完成', 96)
  }
  const count = record.count ?? record.affected_rows
  if (count !== undefined && count !== null) return `已完成，返回 ${count} 条/行`
  if (record.success === true || rawStatus === 'OK' || rawStatus === 'SUCCESS') return '已完成'
  return ''
}

function formatTimelineTime(timestamp: number) {
  return new Date(timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function formatRunTraceTime(event: RunTraceEvent) {
  const raw = event.event_ts
    ? event.event_ts * 1000
    : event.created_at
      ? new Date(event.created_at).getTime()
      : Date.now()
  return formatTimelineTime(Number.isFinite(raw) ? raw : Date.now())
}

function runTraceStatus(event: RunTraceEvent) {
  const payload = event.payload || {}
  const status = String(payload.status || '').toLowerCase()
  if (event.event_type === 'run:end') {
    if (status === 'failed') return '失败'
    if (status === 'cancelled') return '取消'
    return '完成'
  }
  if (event.event_type === 'run:start') return '开始'
  if (event.event_type === 'agent:step') return `第 ${Number(payload.iteration ?? 0) + 1} 步`
  if (event.event_type === 'tool:before') return '工具开始'
  if (event.event_type === 'tool:after') return status === 'error' ? '工具失败' : '工具结束'
  return event.event_type
}

function runTraceTone(event: RunTraceEvent) {
  const status = String((event.payload || {}).status || '').toLowerCase()
  if (status === 'failed' || status === 'error' || status === 'blocked') return 'bg-ops-alert'
  if (event.event_type === 'run:end') return 'bg-ops-success'
  return 'bg-ops-accent'
}

function runTraceEvidenceId(event: RunTraceEvent) {
  const payload = event.payload || {}
  const evidenceId = payload.evidence_id
  return typeof evidenceId === 'string' ? evidenceId.trim() : ''
}

function runTraceApprovalRef(event: RunTraceEvent) {
  const payload = event.payload || {}
  const approvalRef = payload.approval_ref || payload.approval_id
  return typeof approvalRef === 'string' ? approvalRef.trim() : ''
}

interface RunTraceGroup {
  id: string
  events: RunTraceEvent[]
  startedAt?: RunTraceEvent
  endedAt?: RunTraceEvent
}

interface ContextSourceAudit {
  source: string
  enabled: boolean
  hit: boolean
  referenceCount: number
  status: string
}

interface PromptModuleAudit {
  module: string
  enabled: boolean
}

interface PromptManifestAudit {
  surface: string
  mode: string
  modules: PromptModuleAudit[]
}

interface RunTraceAuditViewSummary {
  contextSources: number
  contextHits: number
  contextErrors: number
  promptModules: number
  unauditedRuns: number
}

interface RunTraceEvidenceDetail {
  evidenceId: string
  trace?: ExecTraceItem | null
  loading?: boolean
  error?: string
}

interface RunTraceApprovalDetail {
  approvalId: string
  approval?: ApprovalRequest | null
  loading?: boolean
  error?: string
}

interface RunTraceLearningPreviewDetail {
  runId?: string
  preview?: SessionRunLearningPreview | null
  loading?: boolean
  submitting?: boolean
  submittedCandidateId?: string
  submittedDeduped?: boolean
  error?: string
}

function eventRunId(event: RunTraceEvent, index: number) {
  const payloadRunId = typeof event.payload?.run_id === 'string' ? event.payload.run_id : ''
  return event.run_id || payloadRunId || `ungrouped-${event.event_ts || event.created_at || index}`
}

function groupRunTraceEvents(events: RunTraceEvent[]) {
  const groups = new Map<string, RunTraceGroup>()
  events.forEach((event, index) => {
    const runId = eventRunId(event, index)
    const group = groups.get(runId) || { id: runId, events: [] }
    group.events.push(event)
    if (event.event_type === 'run:start') group.startedAt = event
    if (event.event_type === 'run:end') group.endedAt = event
    groups.set(runId, group)
  })
  return Array.from(groups.values())
}

function runTraceGroupStatus(group: RunTraceGroup) {
  const terminal = group.endedAt
  if (!terminal) return '运行中'
  return runTraceStatus(terminal)
}

function runTraceGroupTone(group: RunTraceGroup) {
  const terminal = group.endedAt
  if (!terminal) return 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
  const status = String((terminal.payload || {}).status || '').toLowerCase()
  if (status === 'failed' || status === 'error' || status === 'blocked') {
    return 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
  }
  if (status === 'cancelled') return 'border-amber-400/35 bg-amber-400/10 text-amber-200'
  return 'border-ops-success/35 bg-ops-success/10 text-ops-success'
}

function runTraceContextSources(group: RunTraceGroup): ContextSourceAudit[] {
  const startEvent = group.startedAt || group.events.find((event) => event.event_type === 'run:start')
  const context = startEvent?.payload?.context
  if (!context || typeof context !== 'object' || Array.isArray(context)) return []
  const sources = (context as Record<string, unknown>).context_sources
  if (!Array.isArray(sources)) return []
  return sources
    .map((source) => {
      if (!source || typeof source !== 'object' || Array.isArray(source)) return null
      const record = source as Record<string, unknown>
      const sourceId = String(record.source || '').trim()
      if (!sourceId) return null
      const referenceCount = Number(record.reference_count ?? 0)
      return {
        source: sourceId,
        enabled: record.enabled !== false,
        hit: record.hit === true,
        referenceCount: Number.isFinite(referenceCount) ? Math.max(0, Math.round(referenceCount)) : 0,
        status: String(record.status || 'ok'),
      }
    })
    .filter((source): source is ContextSourceAudit => Boolean(source))
}

function runTracePromptManifest(group: RunTraceGroup): PromptManifestAudit | null {
  const startEvent = group.startedAt || group.events.find((event) => event.event_type === 'run:start')
  const context = startEvent?.payload?.context
  if (!context || typeof context !== 'object' || Array.isArray(context)) return null
  const manifest = (context as Record<string, unknown>).prompt_modules
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) return null
  const record = manifest as Record<string, unknown>
  const rawModules = record.modules
  if (!Array.isArray(rawModules) || rawModules.length === 0) return null
  const enabledMap = record.enabled && typeof record.enabled === 'object' && !Array.isArray(record.enabled)
    ? record.enabled as Record<string, unknown>
    : {}
  const modules = rawModules
    .map((module) => String(module || '').trim())
    .filter(Boolean)
    .map((module) => ({
      module,
      enabled: enabledMap[module] !== false,
    }))
  if (modules.length === 0) return null
  return {
    surface: String(record.surface || ''),
    mode: String(record.mode || ''),
    modules,
  }
}

function contextSourceLabel(source: string) {
  const labels: Record<string, string> = {
    system_prompt: '系统提示词',
    long_term_memory: '长期记忆',
    knowledge_base: '知识库',
    asset_profile: '资产画像',
  }
  return labels[source] || source
}

function promptModuleLabel(module: string) {
  const labels: Record<string, string> = {
    evidence_contract: '证据契约',
    context_precedence: '上下文优先级',
    skill_instructions: 'Skill 指令',
    rag_context: '知识库上下文',
    ltm_context: '长期记忆上下文',
    asset_profile: '资产画像',
    analysis_only: '只分析模式',
    delegated_task: '委派任务',
    tool_catalog: '工具目录',
    skill_paths: '本地 Skill 路径',
  }
  return labels[module] || module
}

function contextSourceTone(source: ContextSourceAudit) {
  if (!source.enabled) return 'border-ops-surface1 bg-ops-dark/25 text-ops-overlay'
  if (source.status === 'error') return 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
  if (source.hit) return 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
  return 'border-ops-surface1 bg-ops-panel/30 text-ops-subtext'
}

function contextSourceStateText(source: ContextSourceAudit) {
  if (!source.enabled) return '未启用'
  if (source.status === 'error') return '读取失败'
  if (source.hit) return `命中 ${source.referenceCount}`
  return '未命中'
}

function promptModuleTone(module: PromptModuleAudit) {
  return module.enabled
    ? 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
    : 'border-ops-surface1 bg-ops-dark/25 text-ops-overlay'
}

function runTraceAuditSummary(groups: RunTraceGroup[]) {
  return groups.reduce(
    (acc, group) => {
      const contextSources = runTraceContextSources(group)
      const promptManifest = runTracePromptManifest(group)
      const hasAudit = contextSources.length > 0 || Boolean(promptManifest)
      acc.contextSources += contextSources.length
      acc.contextHits += contextSources.filter((source) => source.enabled && source.hit).length
      acc.contextErrors += contextSources.filter((source) => source.status === 'error').length
      acc.promptModules += promptManifest?.modules.filter((module) => module.enabled).length || 0
      if (!hasAudit) acc.unauditedRuns += 1
      return acc
    },
    { contextSources: 0, contextHits: 0, contextErrors: 0, promptModules: 0, unauditedRuns: 0 },
  )
}

function runTraceAuditViewSummary(summary: RunTraceAuditSummary | null | undefined): RunTraceAuditViewSummary | null {
  if (!summary) return null
  return {
    contextSources: Number(summary.context_sources || 0),
    contextHits: Number(summary.context_hits || 0),
    contextErrors: Number(summary.context_errors || 0),
    promptModules: Number(summary.prompt_modules || 0),
    unauditedRuns: Number(summary.unaudited_run_count || 0),
  }
}

function formatRunTraceDuration(durationMs?: number | null) {
  if (durationMs === undefined || durationMs === null) return ''
  if (!Number.isFinite(durationMs)) return ''
  if (durationMs < 1000) return `${Math.max(0, Math.round(durationMs))}ms`
  const seconds = durationMs / 1000
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}m ${rest}s`
}

function formatTimelineDate(timestamp: number) {
  return new Date(timestamp).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function groupSearchText(group: ThinkingChainGroup) {
  return [
    `第 ${group.turnNumber} 轮`,
    formatTimelineTime(group.startedAt),
    group.outputAt ? formatTimelineTime(group.outputAt) : '',
    group.userPrompt,
    group.assistantSummary,
    ...group.runtimeEvents.map((event) => event.content),
    ...group.traces.flatMap((trace) => [
      trace.tool,
      trace.args || '',
      trace.result || '',
      traceEvidenceId(trace),
      trace.evidence?.tool_family || '',
      trace.evidence?.input_summary || '',
      trace.evidence?.redacted_input || '',
      trace.evidence?.output_preview || '',
      traceTargetLabel(trace),
      tracePolicySearchText(trace),
    ]),
  ].join(' ').toLowerCase()
}

function scrollChatMessage(messageId: string) {
  window.dispatchEvent(new CustomEvent('opscore:scroll-chat-message', {
    detail: { messageId },
  }))
}

export default function AiThinkingChainPanel({
  defaultTab = 'trace',
  fixedTab,
  sessionId,
  messages,
  sessionMode,
  traceLabel = '思维链',
}: AiThinkingChainPanelProps) {
  const traceSource = sessionMode ? 'session_snapshot' : 'inferred_unknown'
  const [query, setQuery] = useState('')
  const [selectedGroupId, setSelectedGroupId] = useState('all')
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'trace' | 'memory'>(defaultTab)
  const [memoryActivity, setMemoryActivity] = useState<SessionMemoryActivity | null>(null)
  const [memoryLoading, setMemoryLoading] = useState(false)
  const [runTraceEvents, setRunTraceEvents] = useState<RunTraceEvent[]>([])
  const [runTraceRuns, setRunTraceRuns] = useState<RunTraceRun[]>([])
  const [runTraceRunIndex, setRunTraceRunIndex] = useState<RunTraceRun[]>([])
  const [runTraceAuditSummary, setRunTraceAuditSummary] = useState<RunTraceAuditSummary | null>(null)
  const [selectedRunTraceId, setSelectedRunTraceId] = useState('')
  const [runTraceEvidenceDetail, setRunTraceEvidenceDetail] = useState<RunTraceEvidenceDetail | null>(null)
  const [runTraceApprovalDetail, setRunTraceApprovalDetail] = useState<RunTraceApprovalDetail | null>(null)
  const [runTraceLearningPreview, setRunTraceLearningPreview] = useState<RunTraceLearningPreviewDetail | null>(null)
  const [runTraceLoading, setRunTraceLoading] = useState(false)
  const deferredMessages = useDeferredValue(messages)
  const displayTab = fixedTab || activeTab
  const traceGroups = useMemo(() => buildThinkingGroups(deferredMessages), [deferredMessages])
  const latestGroupId = traceGroups[traceGroups.length - 1]?.id || null
  const activeExpandedGroupId = expandedGroupId === collapsedGroupId
    ? null
    : expandedGroupId || latestGroupId
  const filteredGroups = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const searched = needle
      ? traceGroups.filter((group) => groupSearchText(group).includes(needle))
      : traceGroups
    return selectedGroupId === 'all'
      ? searched
      : searched.filter((group) => group.id === selectedGroupId)
  }, [query, selectedGroupId, traceGroups])

  const groupedOptions = useMemo(() => {
    const byDate = new Map<string, ThinkingChainGroup[]>()
    for (const group of [...traceGroups].reverse()) {
      const date = group.dateLabel
      byDate.set(date, [...(byDate.get(date) || []), group])
    }
    return Array.from(byDate.entries())
  }, [traceGroups])

  useEffect(() => {
    setSelectedRunTraceId('')
    setRunTraceLearningPreview(null)
  }, [sessionId])

  useEffect(() => {
    if (displayTab !== 'memory') {
      setMemoryLoading(false)
      return
    }
    if (!sessionId) {
      setMemoryActivity(null)
      setMemoryLoading(false)
      return
    }
    let cancelled = false
    const controller = new AbortController()
    setMemoryLoading(true)
    getSessionMemoryActivity(sessionId, { signal: controller.signal })
      .then((response) => {
        if (!cancelled) setMemoryActivity(response.data.activity)
      })
      .catch((error) => {
        if (isAbortError(error)) return
        if (!cancelled) setMemoryActivity(null)
      })
      .finally(() => {
        if (!cancelled) setMemoryLoading(false)
      })
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [sessionId, deferredMessages.length, displayTab])

  useEffect(() => {
    if (displayTab !== 'trace') {
      setRunTraceLoading(false)
      return
    }
    if (!sessionId) {
      setRunTraceEvents([])
      setRunTraceRuns([])
      setRunTraceRunIndex([])
      setRunTraceAuditSummary(null)
      setSelectedRunTraceId('')
      setRunTraceLoading(false)
      return
    }
    let cancelled = false
    const controller = new AbortController()
    setRunTraceLoading(true)
    const runTraceLimit = selectedRunTraceId ? 500 : 120
    Promise.all([
      getSessionRunTrace(sessionId, runTraceLimit, {
        signal: controller.signal,
        runId: selectedRunTraceId || undefined,
      }),
      getSessionRunTraceAuditSummary(sessionId, runTraceLimit, {
        signal: controller.signal,
        runId: selectedRunTraceId || undefined,
      }).catch(() => null),
    ])
      .then(([response, auditResponse]) => {
        if (!cancelled) {
          setRunTraceEvents(response.data.events || [])
          setRunTraceRuns(response.data.runs || [])
          setRunTraceAuditSummary(auditResponse?.data.summary || null)
          if (!selectedRunTraceId) setRunTraceRunIndex(response.data.runs || [])
        }
      })
      .catch((error) => {
        if (isAbortError(error)) return
        if (!cancelled) {
          setRunTraceEvents([])
          setRunTraceRuns([])
          setRunTraceAuditSummary(null)
          if (!selectedRunTraceId) setRunTraceRunIndex([])
        }
      })
      .finally(() => {
        if (!cancelled) setRunTraceLoading(false)
      })
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [sessionId, deferredMessages.length, displayTab, selectedRunTraceId])

  const selectGroup = (groupId: string) => {
    setSelectedGroupId(groupId)
    if (groupId === 'all') return
    const group = traceGroups.find((item) => item.id === groupId)
    if (!group) return
    setExpandedGroupId(group.id)
    scrollChatMessage(group.outputMessageId || group.scrollMessageId || group.userMessageId)
  }

  const openGroup = (group: ThinkingChainGroup) => {
    if (activeExpandedGroupId === group.id) {
      setExpandedGroupId(collapsedGroupId)
      return
    }
    setExpandedGroupId(group.id)
    scrollChatMessage(group.outputMessageId || group.scrollMessageId || group.userMessageId)
  }

  const openRunTraceEvidence = async (event: RunTraceEvent) => {
    const evidenceId = runTraceEvidenceId(event)
    if (!sessionId || !evidenceId) return
    setRunTraceEvidenceDetail({ evidenceId, loading: true })
    try {
      const response = await getSessionHistoryEvidenceTrace(sessionId, { evidenceId, limit: 200 })
      setRunTraceEvidenceDetail({ evidenceId, trace: response.data.trace })
    } catch (error: unknown) {
      setRunTraceEvidenceDetail({
        evidenceId,
        trace: null,
        error: error instanceof Error ? error.message : '加载工具证据详情失败',
      })
    }
  }

  const openRunTraceApproval = async (event: RunTraceEvent) => {
    const approvalId = runTraceApprovalRef(event)
    if (!approvalId) return
    setRunTraceApprovalDetail({ approvalId, loading: true })
    try {
      const response = await getApproval(approvalId)
      setRunTraceApprovalDetail({ approvalId, approval: response.data.approval })
    } catch (error: unknown) {
      setRunTraceApprovalDetail({
        approvalId,
        approval: null,
        error: error instanceof Error ? error.message : '加载审批详情失败',
      })
    }
  }

  const openRunTraceLearningPreview = async (runId: string) => {
    if (!sessionId) return
    const targetRunId = runId || selectedRunTraceId
    setRunTraceLearningPreview({ runId: targetRunId || undefined, loading: true })
    try {
      const response = await getSessionRunLearningPreview(sessionId, 300, {
        runId: targetRunId || undefined,
      })
      setRunTraceLearningPreview({ runId: targetRunId || undefined, preview: response.data.preview })
    } catch (error: unknown) {
      setRunTraceLearningPreview({
        runId: targetRunId || undefined,
        preview: null,
        error: error instanceof Error ? error.message : '加载学习预览失败',
      })
    }
  }

  const submitRunTraceLearningCandidate = async () => {
    if (!sessionId || !runTraceLearningPreview?.preview || runTraceLearningPreview.submitting) return
    const runId = runTraceLearningPreview.preview.run_id || runTraceLearningPreview.runId || ''
    setRunTraceLearningPreview({ ...runTraceLearningPreview, submitting: true, error: undefined })
    try {
      const response = await createSessionRunLearningCandidate(sessionId, {
        runId,
        reason: '从 Run Trace 学习预览人工提交',
      })
      setRunTraceLearningPreview({
        ...runTraceLearningPreview,
        submitting: false,
        submittedCandidateId: response.data.learning_candidate?.id || response.data.candidate?.candidate_id || '已提交',
        submittedDeduped: Boolean(response.data.deduped),
      })
    } catch (error: unknown) {
      setRunTraceLearningPreview({
        ...runTraceLearningPreview,
        submitting: false,
        error: error instanceof Error ? error.message : '提交学习候选失败',
      })
    }
  }

  return (
    <section className="min-h-0 flex min-w-0 flex-1 flex-col overflow-hidden border-t border-ops-surface0/80">
      <header className="space-y-2 border-b border-ops-surface0/80 bg-ops-dark/55 px-3 py-2.5">
        <div className="flex items-center justify-between gap-3 text-xs font-semibold tracking-wide text-ops-text">
          {fixedTab ? (
            <div className="text-xs font-black text-ops-text">{displayTab === 'trace' ? traceLabel : '会话记忆'}</div>
          ) : (
            <div className="flex items-center gap-1 rounded-md border border-ops-surface0 bg-ops-panel/70 p-0.5">
              <button
                type="button"
                onClick={() => setActiveTab('trace')}
                className={`rounded px-2 py-1 ${activeTab === 'trace' ? 'bg-ops-accent text-ops-ink' : 'text-ops-subtext hover:text-ops-text'}`}
              >
                {traceLabel}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('memory')}
                className={`rounded px-2 py-1 ${activeTab === 'memory' ? 'bg-ops-accent text-ops-ink' : 'text-ops-subtext hover:text-ops-text'}`}
              >
                记忆
              </button>
            </div>
          )}
          <span className="font-mono text-[10px] font-normal text-ops-overlay">
            {displayTab === 'trace'
              ? (sessionId ? `${traceGroups.length} 轮 / ${runTraceEvents.length} 事件` : '未绑定')
              : (sessionId ? `${memoryActivity?.summary.referenced_count || 0} 引用` : '未绑定')}
          </span>
        </div>
        {displayTab === 'trace' && (
          <>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="h-9 w-full rounded-xl border border-ops-surface1/80 bg-ops-panel/65 px-3 text-xs text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent/60"
              placeholder="查找时间 / 会话内容 / 工具 / 结果"
            />
            <select
              value={selectedGroupId}
              onChange={(event) => selectGroup(event.target.value)}
              className="h-9 w-full rounded-xl border border-ops-surface1/80 bg-ops-panel/65 px-3 text-xs text-ops-text outline-none focus:border-ops-accent/60"
              title="按日期和轮次定位思维链"
            >
              <option value="all">全部日期 / 全部轮次</option>
              {groupedOptions.map(([date, groups]) => (
                <optgroup key={date} label={date}>
                  {groups.map((group) => (
                    <option key={group.id} value={group.id}>
                      {`${group.dateLabel} 第 ${group.turnNumber} 轮 · 输出 ${formatTimelineTime(group.outputAt || group.startedAt)} · ${group.userPrompt}`}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </>
        )}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto bg-transparent px-3 py-3">
        {displayTab === 'memory' ? (
          <MemoryActivityPanel activity={memoryActivity} loading={memoryLoading} />
        ) : (
          <div className="space-y-3">
            <RunTraceStrip
              events={runTraceEvents}
              runs={runTraceRuns}
              runIndex={runTraceRunIndex}
              serverAuditSummary={runTraceAuditSummary}
              loading={runTraceLoading}
              selectedRunId={selectedRunTraceId}
              onSelectRun={setSelectedRunTraceId}
              onOpenEvidence={(event) => void openRunTraceEvidence(event)}
              onOpenApproval={(event) => void openRunTraceApproval(event)}
              onOpenLearningPreview={(runId) => void openRunTraceLearningPreview(runId)}
            />
            {traceGroups.length === 0 ? (
              <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
                暂无会话轮次。发送消息后会按轮次展示当前会话的执行链路。
              </div>
            ) : filteredGroups.length === 0 ? (
              <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
                没有匹配的思维链。可以按时间、工具名、用户问题或结果关键字搜索。
              </div>
            ) : filteredGroups.slice(-30).reverse().map((group) => (
              <div
                key={`${group.id}-${group.traces.length}`}
                className="w-full overflow-hidden rounded-2xl border border-ops-surface0/90 bg-ops-dark/32 text-left transition hover:border-ops-accent/45 hover:bg-ops-dark/45"
              >
                <button
                  type="button"
                  onClick={() => openGroup(group)}
                  className="w-full border-b border-ops-surface0/70 bg-ops-panel/24 px-3 py-2.5 text-left"
                  title="点击定位左侧对应 AI 输出报告"
                >
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="font-semibold text-ops-text">
                      {activeExpandedGroupId === group.id ? '▼' : '▶'} {group.dateLabel} 第 {group.turnNumber} 轮
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] text-ops-overlay">
                        输出 {formatTimelineTime(group.outputAt || group.startedAt)}
                      </span>
                      <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[11px] text-ops-subtext">
                        {group.traces.length > 0
                          ? `${group.traces.length} 步`
                          : group.runtimeEvents.length > 0
                            ? `${group.runtimeEvents.length} 条状态`
                            : '无工具链路'}
                      </span>
                    </div>
                  </div>
                  <div className="mt-1 font-mono text-[10px] text-ops-overlay">
                    输入 {formatTimelineTime(group.startedAt)}
                  </div>
                </button>
                {activeExpandedGroupId === group.id && (
                  <>
                    <div className="grid gap-2 px-3 py-2 text-[11px] leading-5">
                    <div className="rounded-xl border border-ops-surface0 bg-ops-panel/35 px-2.5 py-2">
                      <span className="font-semibold text-ops-overlay">左侧用户：</span>
                      <span className="text-ops-subtext">{group.userPrompt}</span>
                    </div>
                    <div className="rounded-xl border border-ops-surface0 bg-ops-panel/35 px-2.5 py-2">
                      <span className="font-semibold text-ops-overlay">AI 回复：</span>
                      <span className="text-ops-subtext">{group.assistantSummary}</span>
                    </div>
                    </div>
                    <div className="space-y-2 px-3 py-3">
                      {group.runtimeEvents.length > 0 && (
                        <div className="rounded-xl border border-ops-accent/25 bg-ops-accent/10 px-3 py-2">
                          <div className="mb-1.5 text-[11px] font-semibold text-ops-accent">运行状态</div>
                          <div className="space-y-1">
                            {group.runtimeEvents.slice(-12).map((event, index) => (
                              <div key={`${event.timestamp}-${index}`} className="flex gap-2 text-[11px] leading-5 text-ops-subtext">
                                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-ops-accent" />
                                <span className="font-mono text-[10px] text-ops-overlay">{formatTimelineTime(event.timestamp)}</span>
                                <span>{event.content}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {group.traces.length === 0 ? (
                        <div className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2 text-[11px] leading-5 text-ops-subtext">
                          {group.runtimeEvents.length > 0
                            ? '本轮暂未产生工具执行结果，状态会先显示在这里；工具开始执行后会追加命令链路。'
                            : '本轮没有可展示的工具执行链路。通常表示模型直接生成了回复，或后端没有为本轮持久化工具轨迹。'}
                        </div>
                      ) : group.traces.map((trace, index) => {
                        const toolPolicy = toolPolicyFromTrace(trace)
                        const operationMode = recordValue(toolPolicy, 'operation_mode')
                        const evidenceFamily = recordValue(toolPolicy, 'evidence_family')
                        const operation = operationMode ? operationLabel(operationMode) : ''
                        const evidence = evidenceFamily ? evidenceLabel(evidenceFamily) : ''
                        const approval = recordValue(toolPolicy, 'approval_policy')
                        const approvalText = approval ? sessionModePolicyLabel(operationMode, approval, sessionMode) : ''
                        const runtimeLabels = runtimePolicyLabels(toolPolicy)
                        const executionLabels = runtimeExecutionLabels(trace)
                        const sqlAction = sqlActionFromTrace(trace)
                        const httpAction = httpActionFromTrace(trace)
                        const commandAction = commandActionFromTrace(trace)
                        return (
                          <div
                            key={`${trace.tool}-${index}-${trace.startedAt || trace.completedAt || ''}`}
                            className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2"
                          >
                            <div className="flex items-center gap-2 text-xs">
                              <span className={`h-2 w-2 rounded-full ${
                                trace.status === 'running'
                                  ? 'animate-pulse bg-ops-accent'
                                  : trace.status === 'error'
                                    ? 'bg-ops-alert'
                                    : 'bg-ops-success'
                              }`} />
                              <span className="font-semibold text-ops-text">{index + 1}. {toolLabel(trace.tool)}</span>
                              <span className="ml-auto text-[10px] text-ops-overlay">{trace.status || 'done'}</span>
                            </div>
                            <div className="mt-1 text-[11px] leading-5 text-ops-subtext">
                              <span className="font-semibold text-ops-overlay">执行：</span>
                              {compactText(traceTargetLabel(trace), trace.tool, 160)}
                            </div>
                            {(trace.evidence?.tool_family || traceEvidenceId(trace) || toolPolicy) && (
                              <div className="mt-2 flex flex-wrap gap-1.5">
                                {operation && (
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${operationToneClass(operationMode)}`}
                                    title="工具自身能力边界：只读、可读写、外发或破坏性。"
                                  >
                                    模式：{operation}
                                  </span>
                                )}
                                {sqlAction && (
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sqlAction.className}`}
                                    title="本次 SQL 的实际动作类型，和工具自身可读写能力分开显示。"
                                  >
                                    {sqlAction.label}
                                  </span>
                                )}
                                {httpAction && (
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${httpAction.className}`}
                                    title="本次 HTTP/API 请求的实际方法，和工具自身可读写能力分开显示。"
                                  >
                                    {httpAction.label}
                                  </span>
                                )}
                                {commandAction && (
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${commandAction.className}`}
                                    title="本次命令的实际动作，和工具自身可读写能力分开显示。"
                                  >
                                    {commandAction.label}
                                  </span>
                                )}
                                {approvalText && approval !== 'none' && (
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sessionModePolicyToneClass(
                                      operationMode,
                                      approval,
                                      sessionMode,
                                      traceSource,
                                    )}`}
                                    title="当前执行门禁：是否可直接运行，还是写入/高危动作需要审批。"
                                  >
                                    门禁：{approvalText}
                                  </span>
                                )}
                                {evidence && (
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${evidenceToneClass(evidenceFamily)}`}
                                    title="结果会归档到哪类证据链，用于审计、报告和追踪。"
                                  >
                                    证据：{evidence}
                                  </span>
                                )}
                                {trace.evidence?.tool_family && (
                                  <span className="rounded-full border border-ops-surface1 px-2 py-0.5 font-mono text-[10px] text-ops-overlay">
                                    {trace.evidence.tool_family}
                                  </span>
                                )}
                                {traceEvidenceId(trace) && (
                                  <span className="rounded-full border border-ops-surface1 px-2 py-0.5 font-mono text-[10px] text-ops-overlay">
                                    evidence: {traceEvidenceId(trace)}
                                  </span>
                                )}
                                {runtimeLabels.map((label) => (
                                  <span key={label} className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-subtext">
                                    {label}
                                  </span>
                                ))}
                                {executionLabels.map((label) => (
                                  <span key={label} className="rounded-full border border-amber-400/35 bg-amber-400/10 px-2 py-0.5 text-[10px] text-amber-100">
                                    {label}
                                  </span>
                                ))}
                              </div>
                            )}
                            {traceExecutionDetail(trace) && (
                              <div className="mt-2 rounded-md border border-ops-surface0 bg-ops-dark/35">
                                <div className="border-b border-ops-surface0 px-2.5 py-1.5 text-[11px] font-semibold text-ops-overlay">
                                  完整命令 / SQL / 参数
                                </div>
                                <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-words px-2.5 py-2 text-[11px] leading-5 text-ops-text">
                                  {traceExecutionDetail(trace)}
                                </pre>
                              </div>
                            )}
                            <div className="mt-1 text-[11px] leading-5 text-ops-subtext">
                              <span className="font-semibold text-ops-overlay">结果：</span>
                              {traceResultLabel(trace)}
                            </div>
                            {traceResultDetail(trace) && (
                              <details className="mt-2 rounded-md border border-ops-surface0 bg-ops-dark/35">
                                <summary className="cursor-pointer px-2.5 py-1.5 text-[11px] font-semibold text-ops-overlay hover:text-ops-text">
                                  查看完整结果
                                </summary>
                                <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words px-2.5 pb-2 text-[11px] leading-5 text-ops-subtext">
                                  {traceResultDetail(trace)}
                                </pre>
                              </details>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <RunTraceEvidenceDialog
        detail={runTraceEvidenceDetail}
        sessionMode={sessionMode}
        onClose={() => setRunTraceEvidenceDetail(null)}
      />
      <RunTraceApprovalDialog
        detail={runTraceApprovalDetail}
        onClose={() => setRunTraceApprovalDetail(null)}
      />
      <RunTraceLearningPreviewDialog
        detail={runTraceLearningPreview}
        onSubmit={() => void submitRunTraceLearningCandidate()}
        onClose={() => setRunTraceLearningPreview(null)}
      />
    </section>
  )
}

function RunTraceStrip({
  events,
  runs,
  runIndex,
  serverAuditSummary,
  loading,
  selectedRunId,
  onSelectRun,
  onOpenEvidence,
  onOpenApproval,
  onOpenLearningPreview,
}: {
  events: RunTraceEvent[]
  runs: RunTraceRun[]
  runIndex: RunTraceRun[]
  serverAuditSummary?: RunTraceAuditSummary | null
  loading: boolean
  selectedRunId: string
  onSelectRun: (runId: string) => void
  onOpenEvidence: (event: RunTraceEvent) => void
  onOpenApproval: (event: RunTraceEvent) => void
  onOpenLearningPreview: (runId: string) => void
}) {
  const recentRuns = groupRunTraceEvents(events).slice(-6).reverse()
  const runSummaries = new Map(runs.map((run) => [run.run_id, run]))
  const runOptions = [...runIndex].slice(-30).reverse()
  const auditSummary = runTraceAuditViewSummary(serverAuditSummary) || runTraceAuditSummary(recentRuns)
  return (
    <div className="rounded-2xl border border-ops-accent/22 bg-ops-accent/8 px-3 py-2.5">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="text-[11px] font-black uppercase tracking-[0.18em] text-ops-accent">
          AIOps Run Trace
        </div>
        <div className="flex min-w-0 items-center gap-2">
          {runOptions.length > 0 && (
            <select
              value={selectedRunId}
              onChange={(event) => onSelectRun(event.target.value)}
              className="h-7 max-w-[180px] rounded-md border border-ops-surface1/80 bg-ops-panel/70 px-2 text-[10px] text-ops-text outline-none focus:border-ops-accent/60"
              title="按单次运行查看完整事件"
            >
              <option value="">全部运行</option>
              {runOptions.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {`${run.status || 'unknown'} · ${run.tool_count} tool · ${run.run_id}`}
                </option>
              ))}
            </select>
          )}
          <div className="font-mono text-[10px] text-ops-overlay">
            {loading ? '同步中' : `${recentRuns.length} 次 / ${events.length} 条`}
          </div>
          <button
            type="button"
            onClick={() => onOpenLearningPreview(selectedRunId)}
            disabled={events.length === 0}
            className="h-7 rounded-md border border-ops-surface1 px-2 text-[10px] font-semibold text-ops-subtext hover:border-ops-accent/60 hover:text-ops-accent disabled:cursor-not-allowed disabled:opacity-45"
            title="只读生成学习候选预览，不写入记忆。"
          >
            学习预览
          </button>
        </div>
      </div>
      {recentRuns.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5 rounded-lg border border-ops-surface0 bg-ops-dark/25 px-2 py-1.5 text-[10px] text-ops-overlay">
          <span className="font-semibold text-ops-subtext">Context/Prompt 审计</span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5">上下文源 {auditSummary.contextSources}</span>
          <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-ops-accent">命中 {auditSummary.contextHits}</span>
          <span className={`rounded-full border px-2 py-0.5 ${auditSummary.contextErrors > 0 ? 'border-ops-alert/35 text-ops-alert' : 'border-ops-surface1 text-ops-overlay'}`}>
            失败 {auditSummary.contextErrors}
          </span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5">Prompt 模块 {auditSummary.promptModules}</span>
          <span className={`rounded-full border px-2 py-0.5 ${auditSummary.unauditedRuns > 0 ? 'border-amber-400/35 text-amber-200' : 'border-ops-surface1 text-ops-overlay'}`}>
            未审计 {auditSummary.unauditedRuns}
          </span>
        </div>
      )}
      {selectedRunId && (
        <div className="mb-2 flex items-center justify-between gap-2 rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-2 py-1 text-[10px] text-ops-subtext">
          <span className="min-w-0 truncate font-mono">当前只看：{selectedRunId}</span>
          <button
            type="button"
            onClick={() => onSelectRun('')}
            className="shrink-0 rounded border border-ops-surface1 px-2 py-0.5 text-ops-text hover:border-ops-accent/60"
          >
            全部
          </button>
        </div>
      )}
      {recentRuns.length === 0 ? (
        <div className="text-[11px] leading-5 text-ops-subtext">
          暂无运行事件。新会话开始执行后会显示 run、step 和 tool 生命周期。
        </div>
      ) : (
        <div className="space-y-2">
          {recentRuns.map((run) => {
            const summary = runSummaries.get(run.id)
            const first = run.startedAt || run.events[0]
            const latest = run.endedAt || run.events[run.events.length - 1]
            const previewEvents = run.events.slice(-5).reverse()
            const contextSources = runTraceContextSources(run)
            const promptManifest = runTracePromptManifest(run)
            return (
              <div key={run.id} className="rounded-xl border border-ops-surface0/75 bg-ops-panel/35 px-2.5 py-2">
                <div className="mb-1.5 flex min-w-0 items-center gap-2">
                  <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${runTraceGroupTone(run)}`}>
                    {runTraceGroupStatus(run)}
                  </span>
                  <span className="min-w-0 truncate font-mono text-[10px] text-ops-overlay">
                    {formatRunTraceTime(first)} · {summary?.event_count || run.events.length} 事件
                  </span>
                  <span className="ml-auto max-w-[42%] truncate font-mono text-[10px] text-ops-overlay" title={run.id}>
                    {run.id}
                  </span>
                  <button
                    type="button"
                    onClick={() => onOpenLearningPreview(run.id)}
                    className="shrink-0 rounded border border-ops-surface1 px-1.5 py-0.5 text-[10px] text-ops-subtext hover:border-ops-accent/60 hover:text-ops-accent"
                    title="预览这次运行可以沉淀成什么运维经验。"
                  >
                    预览
                  </button>
                </div>
                {summary && (summary.step_count > 0 || summary.tool_count > 0) && (
                  <div className="mb-1.5 flex gap-1.5 text-[10px] text-ops-overlay">
                    <span className="rounded-full border border-ops-surface1 px-2 py-0.5">step {summary.step_count}</span>
                    <span className="rounded-full border border-ops-surface1 px-2 py-0.5">tool {summary.tool_count}</span>
                    {formatRunTraceDuration(summary.duration_ms) && (
                      <span className="rounded-full border border-ops-surface1 px-2 py-0.5">
                        {formatRunTraceDuration(summary.duration_ms)}
                      </span>
                    )}
                  </div>
                )}
                {summary?.reason && (
                  <div className="mb-1.5 line-clamp-2 rounded-lg border border-ops-alert/25 bg-ops-alert/8 px-2 py-1 text-[10px] leading-4 text-ops-alert">
                    {summary.reason}
                  </div>
                )}
                {contextSources.length > 0 && (
                  <div className="mb-1.5 rounded-lg border border-ops-surface0 bg-ops-dark/25 px-2 py-1.5">
                    <div className="mb-1 text-[10px] font-semibold text-ops-overlay">上下文来源</div>
                    <div className="flex flex-wrap gap-1.5">
                      {contextSources.map((source) => (
                        <span
                          key={source.source}
                          className={`rounded-full border px-2 py-0.5 text-[10px] ${contextSourceTone(source)}`}
                          title={`${contextSourceLabel(source.source)}：${contextSourceStateText(source)}`}
                        >
                          {contextSourceLabel(source.source)} · {contextSourceStateText(source)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {promptManifest && (
                  <div className="mb-1.5 rounded-lg border border-ops-surface0 bg-ops-dark/25 px-2 py-1.5">
                    <div className="mb-1 flex flex-wrap items-center gap-1.5 text-[10px] font-semibold text-ops-overlay">
                      <span>Prompt 模块</span>
                      {promptManifest.surface && (
                        <span className="rounded-full border border-ops-surface1 px-1.5 py-0.5 font-mono font-normal text-ops-overlay">
                          {promptManifest.surface}
                        </span>
                      )}
                      {promptManifest.mode && (
                        <span className="rounded-full border border-ops-surface1 px-1.5 py-0.5 font-mono font-normal text-ops-overlay">
                          {promptManifest.mode}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {promptManifest.modules.slice(0, 10).map((module) => (
                        <span
                          key={module.module}
                          className={`rounded-full border px-2 py-0.5 text-[10px] ${promptModuleTone(module)}`}
                          title={`${promptModuleLabel(module.module)}：${module.enabled ? '已启用' : '未启用'}`}
                        >
                          {promptModuleLabel(module.module)} · {module.enabled ? '已启用' : '未启用'}
                        </span>
                      ))}
                      {promptManifest.modules.length > 10 && (
                        <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-overlay">
                          +{promptManifest.modules.length - 10}
                        </span>
                      )}
                    </div>
                  </div>
                )}
                <div className="space-y-1.5">
                  {previewEvents.map((event, index) => (
                    <div
                      key={`${event.id || event.event_ts || event.created_at || index}-${event.event_type}`}
                      className="grid grid-cols-[auto_minmax(0,1fr)] gap-2 rounded-lg border border-ops-surface0/60 bg-ops-dark/20 px-2 py-1.5"
                    >
                      <span className={`mt-1.5 h-2 w-2 rounded-full ${runTraceTone(event)}`} />
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <span className="shrink-0 text-[11px] font-semibold text-ops-text">{runTraceStatus(event)}</span>
                          <span className="truncate font-mono text-[10px] text-ops-overlay">{formatRunTraceTime(event)}</span>
                        </div>
                        <div className="mt-0.5 line-clamp-2 text-[11px] leading-5 text-ops-subtext">
                          {event.summary || event.event_type}
                        </div>
                        {(runTraceEvidenceId(event) || runTraceApprovalRef(event)) && (
                          <div className="mt-1 flex flex-wrap gap-1.5">
                            {runTraceEvidenceId(event) && (
                              <EvidenceReferenceChip
                                kind="evidence"
                                value={runTraceEvidenceId(event)}
                                onClick={() => onOpenEvidence(event)}
                                title="查看本次工具执行归档的完整证据详情。"
                              />
                            )}
                            {runTraceApprovalRef(event) && (
                              <EvidenceReferenceChip
                                kind="approval"
                                value={runTraceApprovalRef(event)}
                                onClick={() => onOpenApproval(event)}
                                title="查看本次工具执行关联的审批详情。"
                              />
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {latest !== first && (
                  <div className="mt-1.5 font-mono text-[10px] text-ops-overlay">
                    最近更新 {formatRunTraceTime(latest)}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function RunTraceLearningPreviewDialog({
  detail,
  onSubmit,
  onClose,
}: {
  detail: RunTraceLearningPreviewDetail | null
  onSubmit: () => void
  onClose: () => void
}) {
  if (!detail) return null
  const preview = detail.preview || null
  const statusEntries = preview ? Object.entries(preview.status_counts || {}) : []
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-xl border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-ops-text">Run Trace 学习预览</div>
            <div className="mt-1 text-[11px] text-ops-overlay">
              只读预览，不会自动写入记忆或发布 Skill。
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-ops-surface0 px-2 py-1 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
          >
            关闭
          </button>
        </div>
        <div className="max-h-[72vh] space-y-3 overflow-y-auto p-4">
          {detail.loading && (
            <div className="rounded border border-ops-accent/30 bg-ops-accent/10 px-3 py-2 text-xs text-ops-accent">
              正在生成学习预览...
            </div>
          )}
          {detail.error && (
            <div className="rounded border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
              {detail.error}
            </div>
          )}
          {preview ? (
            <>
              <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                    preview.eligible
                      ? 'border-ops-success/35 bg-ops-success/10 text-ops-success'
                      : 'border-ops-surface1 bg-ops-dark/25 text-ops-overlay'
                  }`}>
                    {preview.eligible ? '可进入候选池' : '证据不足'}
                  </span>
                  {preview.run_id && (
                    <span className="font-mono text-[11px] text-ops-overlay">{preview.run_id}</span>
                  )}
                </div>
                <div className="mt-2 text-sm font-semibold text-ops-text">{preview.title}</div>
                <div className="mt-1 text-xs leading-5 text-ops-subtext">{preview.summary}</div>
              </div>
              <div className="grid gap-2 text-xs md:grid-cols-4">
                <RunTracePreviewMetric label="运行" value={preview.run_count} />
                <RunTracePreviewMetric label="事件" value={preview.event_count} />
                <RunTracePreviewMetric label="工具" value={preview.tool_count} />
                <RunTracePreviewMetric label="证据" value={preview.evidence_refs?.length || 0} />
              </div>
              {statusEntries.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {statusEntries.map(([status, count]) => (
                    <span key={status} className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-subtext">
                      {status}: {count}
                    </span>
                  ))}
                </div>
              )}
              <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-3">
                <div className="mb-2 text-xs font-semibold text-ops-text">{preview.draft?.title || 'Runbook 草稿'}</div>
                <div className="space-y-1.5">
                  {(preview.draft?.outline || []).map((item, index) => (
                    <div key={`${item}-${index}`} className="flex gap-2 text-xs leading-5 text-ops-subtext">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-ops-accent" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-3">
                <div className="mb-2 text-xs font-semibold text-ops-text">证据引用</div>
                {preview.evidence_refs?.length ? (
                  <div className="space-y-1.5">
                    {preview.evidence_refs.slice(0, 8).map((ref, index) => (
                      <div key={`${ref.id || index}-${ref.tool || ''}`} className="flex min-w-0 flex-wrap items-center gap-2 rounded border border-ops-surface0 bg-ops-panel/35 px-2 py-1.5 text-[11px] text-ops-subtext">
                        <span className="font-mono text-ops-overlay">{ref.id || '-'}</span>
                        {ref.tool && <span>{toolLabel(ref.tool)}</span>}
                        {ref.status && <span className="rounded-full border border-ops-surface1 px-1.5 py-0.5 text-[10px]">{ref.status}</span>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-ops-overlay">暂无可关联的工具证据。</div>
                )}
              </div>
              {preview.next_action && (
                <div className="rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-xs leading-5 text-ops-accent">
                  {preview.next_action}
                </div>
              )}
              <div className="flex flex-wrap items-center justify-end gap-2 border-t border-ops-surface0 pt-3">
                {detail.submittedCandidateId && (
                  <span className="mr-auto rounded-full border border-ops-success/35 bg-ops-success/10 px-2 py-1 text-xs text-ops-success">
                    {detail.submittedDeduped ? '已存在候选' : '已提交'}：{detail.submittedCandidateId}
                  </span>
                )}
                <button
                  type="button"
                  onClick={onSubmit}
                  disabled={!preview.eligible || detail.submitting || Boolean(detail.submittedCandidateId)}
                  className="rounded-md border border-ops-accent/45 bg-ops-accent/12 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/18 disabled:cursor-not-allowed disabled:opacity-45"
                  title="提交后进入学习候选池，仍需人工审核质量清单。"
                >
                  {detail.submitting ? '提交中...' : detail.submittedCandidateId ? (detail.submittedDeduped ? '已存在候选' : '已提交候选池') : '提交候选池'}
                </button>
              </div>
            </>
          ) : !detail.loading && !detail.error ? (
            <div className="rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-3 text-xs text-ops-subtext">
              暂无学习预览。
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

function RunTracePreviewMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-2">
      <div className="text-[10px] text-ops-overlay">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold text-ops-text">{value}</div>
    </div>
  )
}

function RunTraceEvidenceDialog({
  detail,
  onClose,
  sessionMode,
}: {
  detail: RunTraceEvidenceDetail | null
  onClose: () => void
  sessionMode?: 'readonly' | 'readwrite'
}) {
  if (!detail) return null
  const trace = detail.trace || null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-xl border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-ops-text">Run Trace 工具证据</div>
            <div className="mt-1 font-mono text-[11px] text-ops-overlay">{detail.evidenceId}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-ops-surface0 px-2 py-1 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
          >
            关闭
          </button>
        </div>
        <div className="max-h-[72vh] overflow-y-auto p-4">
          {detail.loading && (
            <div className="rounded border border-ops-accent/30 bg-ops-accent/10 px-3 py-2 text-xs text-ops-accent">
              正在加载工具证据详情...
            </div>
          )}
          {detail.error && (
            <div className="rounded border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
              {detail.error}
            </div>
          )}
          {trace ? (
            <ToolTraceList items={[trace]} sessionMode={sessionMode} />
          ) : !detail.loading && !detail.error ? (
            <div className="rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-3 text-xs text-ops-subtext">
              暂未在会话历史中匹配到完整执行轨迹，仅保留当前 Run Trace 上的证据引用。
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

function RunTraceApprovalDialog({
  detail,
  onClose,
}: {
  detail: RunTraceApprovalDetail | null
  onClose: () => void
}) {
  if (!detail) return null
  const approval = detail.approval || null
  const context = approval?.context || {}
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-xl border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-ops-text">Run Trace 审批详情</div>
            <div className="mt-1 font-mono text-[11px] text-ops-overlay">{detail.approvalId}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-ops-surface0 px-2 py-1 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
          >
            关闭
          </button>
        </div>
        <div className="max-h-[72vh] overflow-y-auto p-4">
          {detail.loading && (
            <div className="rounded border border-ops-accent/30 bg-ops-accent/10 px-3 py-2 text-xs text-ops-accent">
              正在加载审批详情...
            </div>
          )}
          {detail.error && (
            <div className="rounded border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
              {detail.error}
            </div>
          )}
          {approval ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <ApprovalStatusBadge status={approval.status} />
                <span className="text-sm font-semibold text-ops-accent">{toolLabel(approval.tool_name)}</span>
                <span className="font-mono text-[11px] text-ops-overlay">{approval.id}</span>
              </div>
              <ApprovalSourceSummary
                source={approval.metadata?.approval_source || null}
                sources={approval.metadata?.approval_sources || null}
                reason={approval.reason}
              />
              <div className="grid gap-2 md:grid-cols-2">
                <ApprovalInfo label="会话" value={approval.session_id || '-'} />
                <ApprovalInfo label="资产" value={context.remark || context.host || '-'} />
                <ApprovalInfo label="申请时间" value={approval.requested_at || '-'} />
                <ApprovalInfo label="处理人" value={approval.operator || '-'} />
                <ApprovalInfo label="处理结果" value={approval.decision || approval.status} />
                <ApprovalInfo label="到期时间" value={approval.expires_at || '-'} />
              </div>
              {approval.note && (
                <div className="rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-2 text-xs text-ops-subtext">
                  备注：{approval.note}
                </div>
              )}
              <pre className="ops-data-panel max-h-56 overflow-auto p-3 text-xs leading-relaxed text-ops-subtext">
                {JSON.stringify(approval.args || {}, null, 2)}
              </pre>
            </div>
          ) : !detail.loading && !detail.error ? (
            <div className="rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-3 text-xs text-ops-subtext">
              暂未找到该审批记录，当前 Run Trace 仅保留审批引用 ID。
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

function MemoryActivityPanel({
  activity,
  loading,
}: {
  activity: SessionMemoryActivity | null
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
        正在读取本会话记忆活动...
      </div>
    )
  }
  if (!activity) {
    return (
      <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
        暂无本会话记忆活动。
      </div>
    )
  }

  const summary = activity.summary
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <MemoryStat label="引用记忆" value={summary.referenced_count} />
        <MemoryStat label="候选记忆" value={summary.pending_candidate_count || 0} />
        <MemoryStat label="点踩纠错" value={summary.rejected_count} warn />
        <MemoryStat label="待确认" value={summary.pending_conflict_count} warn />
      </div>
      <MemorySection title="本轮引用记忆" empty="本会话还没有引用长期记忆。">
        {activity.referenced.map((row, rowIndex) => (
          <article key={`${row.message_id || rowIndex}-refs`} className="rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
            <p className="line-clamp-2 text-xs text-ops-text">{row.message_preview || 'AI 输出未保存摘要'}</p>
            <div className="mt-2 space-y-1">
              {row.refs.map((ref, index) => (
                <div key={`${ref.path || ref.scope_id}-${index}`} className="rounded border border-ops-surface0 bg-ops-panel/45 px-2 py-1">
                  <div className="text-[11px] font-semibold text-ops-accent">{ref.scope_label || ref.path || ref.scope_id}</div>
                  <div className="mt-0.5 line-clamp-2 text-[10px] text-ops-overlay">{ref.summary_preview || ref.path || '已引用记忆'}</div>
                </div>
              ))}
            </div>
          </article>
        ))}
      </MemorySection>
      <MemorySection title="人工反馈沉淀" empty="还没有点赞或点踩反馈。">
        {activity.feedback.map((row, index) => (
          <article key={`${row.message_id || index}-feedback`} className="rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
            <div className="flex items-center justify-between gap-2 text-[11px]">
              <span className={row.rating === 'up' ? 'text-ops-accent' : 'text-amber-300'}>
                {row.rating === 'up' ? '点赞生成候选' : '点踩纠错，不保留'}
              </span>
              <span className="font-mono text-[10px] text-ops-overlay">{row.created_at || ''}</span>
            </div>
            <p className="mt-2 line-clamp-3 text-xs text-ops-subtext">{row.message_preview}</p>
            {row.note ? <p className="mt-2 text-[11px] text-ops-overlay">备注：{row.note}</p> : null}
          </article>
        ))}
      </MemorySection>
      <MemorySection title="待确认记忆冲突" empty="暂无待确认冲突。">
        {activity.pending_conflicts.map((row, index) => (
          <article key={`${row.version_id || row.path}-${index}`} className="rounded-md border border-amber-400/30 bg-amber-400/5 px-3 py-2">
            <div className="text-[11px] font-semibold text-amber-200">{row.path}</div>
            <p className="mt-2 line-clamp-3 text-xs text-ops-subtext">
              {row.reason || row.new_preview || row.existing_preview || '需要人工确认后再写入长期记忆。'}
            </p>
            <p className="mt-2 text-[10px] text-ops-overlay">可到知识库 / 记忆管理确认。</p>
          </article>
        ))}
      </MemorySection>
    </div>
  )
}

function MemoryStat({ label, value, warn = false }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
      <div className="text-[10px] text-ops-overlay">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${warn ? 'text-amber-300' : 'text-ops-accent'}`}>{value}</div>
    </div>
  )
}

function MemorySection({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : []
  return (
    <section>
      <h4 className="mb-2 text-xs font-semibold text-ops-text">{title}</h4>
      {items.length > 0 ? (
        <div className="space-y-2">{children}</div>
      ) : (
        <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
          {empty}
        </div>
      )}
    </section>
  )
}
