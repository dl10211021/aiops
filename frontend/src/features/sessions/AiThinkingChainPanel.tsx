import { useMemo, useState } from 'react'
import type { ChatMessage, ExecTraceItem } from '@/types'
import { toolLabel } from '@/utils/assetDisplay'
import { parseJsonRecord } from './jsonRecords'
import { resultReason, traceTargetLabel } from './traceUtils'

interface AiThinkingChainPanelProps {
  sessionId: string | null
  messages: ChatMessage[]
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
      }
      groups.push(currentGroup)
    }
    if (message.execTrace?.length) {
      currentGroup.traces.push(...message.execTrace)
    }
    if (message.content.trim()) {
      currentGroup.assistantSummary = compactText(message.content, 'AI 已输出结果', 180)
      currentGroup.outputMessageId = message.id
      currentGroup.outputAt = message.timestamp
      currentGroup.scrollMessageId = message.id
    }
  })

  return groups
    .filter((group) => group.traces.length > 0)
    .map((group) => ({
      ...group,
      assistantSummary: group.assistantSummary || 'AI 已调用工具，结果汇总在左侧会话输出中。',
    }))
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
  const parsed = parseJsonRecord(trace.result || '')
  if (parsed) {
    const output = parsed.output || parsed.stdout || parsed.result || parsed.data
    if (typeof output === 'string' && output.trim()) return output.trim()
    const error = parsed.stderr || parsed.error
    if (typeof error === 'string' && error.trim()) return error.trim()
  }
  return trace.result?.trim() || ''
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
    ...group.traces.flatMap((trace) => [
      trace.tool,
      trace.args || '',
      trace.result || '',
      traceTargetLabel(trace),
    ]),
  ].join(' ').toLowerCase()
}

function scrollChatMessage(messageId: string) {
  window.dispatchEvent(new CustomEvent('opscore:scroll-chat-message', {
    detail: { messageId },
  }))
}

export default function AiThinkingChainPanel({
  sessionId,
  messages,
}: AiThinkingChainPanelProps) {
  const [query, setQuery] = useState('')
  const [selectedGroupId, setSelectedGroupId] = useState('all')
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null)
  const traceGroups = useMemo(() => buildThinkingGroups(messages), [messages])
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
      <header className="space-y-2 border-b border-ops-surface0/80 bg-ops-dark px-3 py-2">
        <div className="flex items-center justify-between gap-3 text-xs font-semibold tracking-wide text-ops-text">
          <span>AI 思维链</span>
          <span className="font-mono text-[10px] font-normal text-ops-overlay">
            {sessionId ? `${traceGroups.length} 次` : '未绑定'}
          </span>
        </div>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="h-8 w-full rounded-md border border-ops-surface1 bg-ops-panel/70 px-2.5 text-xs text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent/60"
          placeholder="查找时间 / 会话内容 / 工具 / 结果"
        />
        <select
          value={selectedGroupId}
          onChange={(event) => selectGroup(event.target.value)}
          className="h-8 w-full rounded-md border border-ops-surface1 bg-ops-panel/70 px-2.5 text-xs text-ops-text outline-none focus:border-ops-accent/60"
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
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto bg-ops-panel/70 px-3 py-2">
        {traceGroups.length === 0 ? (
          <div className="rounded-md border border-ops-surface0/80 bg-ops-dark/30 px-2.5 py-3 text-xs text-ops-subtext">
            暂无可展示的执行轨迹。AI 调用工具后会写入后端会话历史，并按轮次沉淀在这里。
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
                className="w-full overflow-hidden rounded-md border border-ops-surface0 bg-ops-dark/30 text-left transition hover:border-ops-accent/45 hover:bg-ops-dark/45"
              >
                <button
                  type="button"
                  onClick={() => openGroup(group)}
                  className="w-full border-b border-ops-surface0/70 px-3 py-2 text-left"
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
                        {group.traces.length} 步
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
                    <div className="rounded-md border border-ops-surface0 bg-ops-panel/35 px-2.5 py-2">
                      <span className="font-semibold text-ops-overlay">左侧用户：</span>
                      <span className="text-ops-subtext">{group.userPrompt}</span>
                    </div>
                    <div className="rounded-md border border-ops-surface0 bg-ops-panel/35 px-2.5 py-2">
                      <span className="font-semibold text-ops-overlay">AI 回复：</span>
                      <span className="text-ops-subtext">{group.assistantSummary}</span>
                    </div>
                    </div>
                    <div className="space-y-2 px-3 py-3">
                      {group.traces.map((trace, index) => (
                        <div
                          key={`${trace.tool}-${index}-${trace.startedAt || trace.completedAt || ''}`}
                          className="rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2"
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
                      ))}
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
