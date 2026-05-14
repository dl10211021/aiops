import { useEffect, useMemo, useState } from 'react'
import { appendAlertWorkflowMessage, getAlertWorkflow, runAlertWorkflowReadonly } from '@/api/client'
import { useStore } from '@/store'
import type { AlertEvent, AlertWorkflow, AlertWorkflowStep } from '@/types'
import { formatAlertDate } from './alertDisplay'

const STATUS_CLASS: Record<string, string> = {
  done: 'border-ops-success/45 bg-ops-success/10 text-ops-success',
  running: 'border-ops-accent/45 bg-ops-accent/10 text-ops-accent',
  ready: 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent',
  waiting: 'border-ops-surface1 bg-ops-surface0 text-ops-subtext',
  skipped: 'border-ops-surface1 bg-ops-dark/30 text-ops-overlay',
  disabled: 'border-ops-surface1 bg-ops-dark/30 text-ops-overlay',
}

function stepTone(step: AlertWorkflowStep) {
  return STATUS_CLASS[step.status] || STATUS_CLASS.waiting
}

function statusLabel(status: string) {
  return {
    done: '完成',
    running: '运行中',
    ready: '待执行',
    waiting: '等待',
    skipped: '跳过',
    disabled: '关闭',
  }[status] || status
}

function queryItems(step: AlertWorkflowStep) {
  const queries = (step.details?.queries || []) as Array<{ name?: string; query?: string }>
  return Array.isArray(queries) ? queries : []
}

function remediationModeLabel(mode?: string) {
  return {
    disabled: '关闭',
    suggest: '建议模式',
    approval: '审批模式',
    auto_low_risk: '低风险自动修复',
  }[mode || 'disabled'] || mode || '关闭'
}

function stepSummary(workflow: AlertWorkflow | null) {
  const steps = workflow?.steps || []
  const completed = steps.filter((step) => step.status === 'done').length
  const active = steps.filter((step) => step.status === 'running' || step.status === 'ready').length
  return {
    active,
    completed,
    total: steps.length,
  }
}

export function AlertWorkflowPanel({ alert }: { alert: AlertEvent }) {
  const addToast = useStore((s) => s.addToast)
  const [workflow, setWorkflow] = useState<AlertWorkflow | null>(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await getAlertWorkflow(alert.id)
      setWorkflow(res.data.workflow)
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '加载告警工作流失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [alert.id])

  const remediationStep = useMemo(
    () => workflow?.steps.find((step) => step.id === 'remediation'),
    [workflow?.steps],
  )
  const remediationMode = String(remediationStep?.details?.mode || alert.automation_decision?.remediation_mode || 'disabled')
  const hasLinkedSession = Boolean((workflow?.linked_sessions || []).length)
  const summary = stepSummary(workflow)

  const submitMessage = async () => {
    if (!message.trim()) return
    setSending(true)
    try {
      const res = await appendAlertWorkflowMessage(alert.id, { role: 'user', content: message.trim() })
      setWorkflow(res.data.workflow)
      setMessage('')
      addToast('人工介入记录已写入工作流', 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '写入工作流消息失败', 'error')
    } finally {
      setSending(false)
    }
  }

  const runReadonly = async () => {
    setRunning(true)
    try {
      const res = await runAlertWorkflowReadonly(alert.id)
      setWorkflow(res.data.workflow)
      const count = res.data.injected_count || 0
      addToast(count > 0 ? `已触发 ${count} 个会话进行只读分析` : '未找到在线资产会话，已记录到工作流', count > 0 ? 'success' : 'info')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '触发只读分析失败', 'error')
    } finally {
      setRunning(false)
    }
  }

  return (
    <section className="ops-data-panel overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-ops-surface0 px-4 py-3 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="text-sm font-semibold text-ops-text">告警工作流</div>
          <div className="mt-1 text-xs text-ops-subtext">
            AI 分析、监控上下文、资产会话和人工介入记录。
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={runReadonly}
            disabled={running || !hasLinkedSession}
            className="ops-primary-action px-3 py-1.5 text-xs disabled:opacity-50"
            title={hasLinkedSession ? '向已关联资产会话触发只读 AI 分析' : '当前没有在线资产会话'}
          >
            {running ? '触发中...' : '只读分析'}
          </button>
          <button onClick={() => void load()} disabled={loading} className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50">
            刷新
          </button>
        </div>
      </div>

      {loading && !workflow ? (
        <div className="py-6 text-center text-xs text-ops-subtext">正在加载工作流...</div>
      ) : workflow ? (
        <div className="space-y-3 p-3">
          <div className="grid gap-2 text-xs md:grid-cols-3">
            <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-2">
              <div className="text-ops-overlay">步骤进度</div>
              <div className="mt-1 font-mono text-sm font-semibold text-ops-text">
                {summary.completed}/{summary.total}
                <span className="ml-2 text-[11px] font-normal text-ops-subtext">待执行 {summary.active}</span>
              </div>
            </div>
            <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-2">
              <div className="text-ops-overlay">关联会话</div>
              <div className="mt-1 truncate font-mono text-sm font-semibold text-ops-text">
                {(workflow.linked_sessions || []).map((item) => item.session_id.slice(0, 8)).join(', ') || '-'}
              </div>
            </div>
            <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-2">
              <div className="text-ops-overlay">自动修复</div>
              <div className="mt-1 truncate text-sm font-semibold text-ops-text">{remediationModeLabel(remediationMode)}</div>
            </div>
          </div>

          {!hasLinkedSession && (
            <div className="rounded-lg border border-ops-surface1 bg-ops-dark/25 px-3 py-2 text-[11px] leading-5 text-ops-overlay">
              当前未匹配在线资产会话。可先在会话中心连接该资产，或后续开启自动创建后台会话策略。
            </div>
          )}

          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs font-semibold text-ops-text">执行步骤</div>
              <div className="truncate text-[11px] text-ops-overlay">
                资产候选：{(workflow.asset_candidates || []).map((item) => item.remark || item.host).join(', ') || '-'}
              </div>
            </div>
            <div className="grid max-h-72 gap-2 overflow-y-auto pr-1 lg:grid-cols-2">
              {workflow.steps.map((step) => {
                const queries = queryItems(step)
                return (
                  <div key={step.id} className="rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-ops-text">{step.title}</div>
                        {step.summary && <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-ops-subtext">{step.summary}</div>}
                      </div>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${stepTone(step)}`}>
                        {statusLabel(step.status)}
                      </span>
                    </div>
                    {queries.length > 0 && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-[10px] font-semibold text-ops-accent">
                          查看查询 {queries.length} 条
                        </summary>
                        <div className="mt-2 space-y-1">
                          {queries.slice(0, 3).map((item, index) => (
                            <div key={`${item.name}-${index}`} className="rounded border border-ops-surface1 bg-ops-panel/50 px-2 py-1.5">
                              <div className="text-[10px] text-ops-overlay">{item.name || 'PromQL'}</div>
                              <div className="mt-1 break-all font-mono text-[10px] leading-4 text-ops-subtext">{item.query || '-'}</div>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px]">
            <div>
              <div className="mb-2 text-xs font-semibold text-ops-text">工作流记录</div>
              <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-ops-surface0 bg-ops-dark/25 p-2">
                {(workflow.messages || []).length === 0 && (
                  <div className="px-2 py-4 text-center text-xs text-ops-overlay">暂无会话记录</div>
                )}
                {(workflow.messages || []).map((item, index) => (
                  <div key={`${item.time}-${index}`} className="rounded-md bg-ops-panel/60 px-2.5 py-2">
                    <div className="flex items-center justify-between gap-2 text-[10px] text-ops-overlay">
                      <span>{item.role === 'user' ? '人工' : item.role}</span>
                      <span>{formatAlertDate(item.time)}</span>
                    </div>
                    <div className="mt-1 whitespace-pre-wrap text-xs leading-5 text-ops-subtext">{item.content}</div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-2 text-xs font-semibold text-ops-text">人工介入</div>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={6}
                className="ops-control w-full resize-none px-3 py-2 text-xs leading-5"
                placeholder="补充现象、接管说明或禁止自动修复"
              />
              <button onClick={submitMessage} disabled={sending || !message.trim()} className="ops-primary-action mt-2 w-full px-3 py-2 text-xs disabled:opacity-50">
                {sending ? '写入中...' : '写入工作流'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="py-6 text-center text-xs text-ops-subtext">暂无工作流记录</div>
      )}
    </section>
  )
}
