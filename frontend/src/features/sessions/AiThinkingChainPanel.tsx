import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { ChatMessage, ChatRuntimeEvent, ExecTraceItem, SessionMemoryActivity } from '@/types'
import { isAbortError } from '@/api/http'
import { getSessionMemoryActivity } from '@/api/sessionHistory'
import { toolLabel } from '@/utils/assetDisplay'
import { parseJsonRecord } from './jsonRecords'
import { resultReason, traceExecutionText, traceTargetLabel } from './traceUtils'
import {
  approvalLabel,
  evidenceLabel,
  operationLabel,
  recordValue,
  toolPolicyFromTrace,
  toolPolicySearchText,
} from './toolPolicyPresentation'

interface AiThinkingChainPanelProps {
  sessionId: string | null
  messages: ChatMessage[]
  defaultTab?: 'trace' | 'memory'
  fixedTab?: 'trace' | 'memory'
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
  return toolPolicySearchText(toolPolicyFromTrace(trace))
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
  traceLabel = '思维链',
}: AiThinkingChainPanelProps) {
  const [query, setQuery] = useState('')
  const [selectedGroupId, setSelectedGroupId] = useState('all')
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'trace' | 'memory'>(defaultTab)
  const [memoryActivity, setMemoryActivity] = useState<SessionMemoryActivity | null>(null)
  const [memoryLoading, setMemoryLoading] = useState(false)
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
              ? (sessionId ? `${traceGroups.length} 轮` : '未绑定')
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
        ) : traceGroups.length === 0 ? (
          <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
            暂无会话轮次。发送消息后会按轮次展示当前会话的执行链路。
          </div>
        ) : filteredGroups.length === 0 ? (
          <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
            没有匹配的思维链。可以按时间、工具名、用户问题或结果关键字搜索。
          </div>
        ) : (
          <div className="space-y-3">
            {filteredGroups.slice(-30).reverse().map((group) => (
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
                        const operation = operationLabel(recordValue(toolPolicy, 'operation_mode'))
                        const evidence = evidenceLabel(recordValue(toolPolicy, 'evidence_family'))
                        const approval = recordValue(toolPolicy, 'approval_policy')
                        const approvalText = approvalLabel(approval)
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
                                  <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-subtext">
                                    {operation}
                                  </span>
                                )}
                                {evidence && (
                                  <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-subtext">
                                    {evidence}
                                  </span>
                                )}
                                {approvalText && approval !== 'none' && (
                                  <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-[10px] text-ops-accent">
                                    {approvalText}
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
    </section>
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
        <MemoryStat label="点赞沉淀" value={summary.promoted_count} />
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
                {row.rating === 'up' ? '点赞保留记忆' : '点踩纠错，不保留'}
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
