import { useEffect, useMemo, useState } from 'react'
import type { AlertEvent, AlertEventStatus } from '@/types'
import {
  alertNoiseActionLabel,
  alertPurposeLabel,
  alertPriorityLabel,
  alertSourceLabel,
  formatAlertDate,
  isWebhookTestAlert,
} from './alertDisplay'
import { AlertInfo, AlertSeverityBadge, AlertStatusBadge } from './AlertCenterShared'
import { AlertWorkflowPanel } from './AlertWorkflowPanel'

type AlertDetailTab = 'overview' | 'workflow' | 'handling' | 'payload'

const DETAIL_TABS: Array<{ id: AlertDetailTab; label: string }> = [
  { id: 'overview', label: '事件' },
  { id: 'workflow', label: 'AI 与会话' },
  { id: 'handling', label: '处理' },
  { id: 'payload', label: '原始' },
]

function remediationModeLabel(mode?: string) {
  const labels: Record<string, string> = {
    disabled: '关闭',
    suggest: '建议模式',
    approval: '审批模式',
    auto_low_risk: '低风险自动修复',
  }
  return labels[String(mode || 'disabled')] || mode || '关闭'
}

function notificationChannelLabel(alert: AlertEvent) {
  const targets = alert.notification_plan?.targets || []
  if (targets.length > 0) return targets.join(', ')
  const channel = String(alert.notification_plan?.channel || '').toLowerCase()
  if (!channel || channel === 'none') return '不通知'
  return alert.notification_plan?.channel || '不通知'
}

function nextStepLabel(alert: AlertEvent) {
  if (alert.status === 'closed') return '已关闭，后续只需复盘。'
  if (alert.status === 'suppressed') return '已抑制，等待后续重复告警情况。'
  if (alert.automation_decision?.run_ai) return '先看 AI 与资产会话的只读分析，再决定是否接手或允许修复。'
  return '这条告警当前只记录，可人工接手或关闭。'
}

type AlertFlowStep = {
  text: string
  title: string
  state: 'active' | 'done' | 'wait'
}

function alertFlowSteps(alert: AlertEvent): AlertFlowStep[] {
  const steps: AlertFlowStep[] = [
    { title: '接入', text: alertSourceLabel(alert.source_family || alert.source_type || alert.source), state: 'done' },
    { title: '归并', text: alert.host || '-', state: 'done' },
    { title: '规则', text: alert.automation_decision?.rule_name || alertNoiseActionLabel(alert.noise_action), state: 'done' },
  ]
  if (alert.automation_decision?.run_ai) {
    steps.push({ title: 'AI 与会话', text: '查监控和资产会话', state: alert.status === 'open' ? 'active' : 'done' })
  }
  if (alert.automation_decision?.remediation_mode && alert.automation_decision.remediation_mode !== 'disabled') {
    steps.push({ title: '修复', text: remediationModeLabel(alert.automation_decision.remediation_mode), state: alert.status === 'acknowledged' ? 'active' : 'wait' })
  }
  steps.push({
    title: '通知闭环',
    text: alert.status === 'closed' ? '已关闭' : alert.status === 'suppressed' ? '已抑制' : alert.status === 'acknowledged' ? '处理中' : '待处理',
    state: alert.status === 'closed' || alert.status === 'suppressed' ? 'done' : alert.status === 'acknowledged' ? 'active' : 'wait',
  })
  return steps
}

function flowStepClass(state: AlertFlowStep['state']) {
  if (state === 'done') return 'border-ops-success/40 bg-ops-success/10 text-ops-success'
  if (state === 'active') return 'border-ops-accent/60 bg-ops-accent/12 text-ops-accent'
  return 'border-ops-surface0 bg-ops-dark/20 text-ops-subtext'
}

function AlertFlowSteps({ alert }: { alert: AlertEvent }) {
  const items = alertFlowSteps(alert)
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
      <div className="mb-3 text-sm font-semibold text-ops-text">这条事件会怎么处理</div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-5">
        {items.map((item, index) => {
          const state = item.state
          return (
            <div key={item.title} className={`rounded-lg border p-3 ${flowStepClass(state)}`}>
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-current/15 font-mono text-xs font-black">
                  {index + 1}
                </span>
                <span className="text-xs font-semibold">{item.title}</span>
              </div>
              <div className="mt-2 truncate text-[11px] text-ops-subtext">{item.text}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export function AlertDetail({
  alert,
  assignee,
  note,
  busy,
  onAssigneeChange,
  onNoteChange,
  onUpdate,
}: {
  alert: AlertEvent | null
  assignee: string
  note: string
  busy: boolean
  onAssigneeChange: (value: string) => void
  onNoteChange: (value: string) => void
  onUpdate: (alert: AlertEvent, status?: AlertEventStatus) => void
}) {
  const [activeTab, setActiveTab] = useState<AlertDetailTab>('overview')

  const rawPayload = useMemo(
    () => JSON.stringify(alert?.payload || {}, null, 2),
    [alert?.id, alert?.payload],
  )

  useEffect(() => {
    setActiveTab('overview')
  }, [alert?.id])

  if (!alert) {
    return (
      <aside className="ops-card p-5 xl:sticky xl:top-5">
        <div className="py-20 text-center text-sm text-ops-subtext">选择一条告警后查看详情</div>
      </aside>
    )
  }

  return (
    <aside className="flex min-h-[420px] flex-col overflow-hidden rounded-lg border border-ops-surface0 bg-ops-panel/65 md:min-h-[560px] xl:sticky xl:top-4 xl:max-h-[calc(100vh-14rem)]">
      <div className="shrink-0 border-b border-ops-surface0 px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <AlertStatusBadge status={alert.status} />
          <AlertSeverityBadge severity={alert.severity} />
          <span className="rounded-full border border-ops-surface1 bg-ops-surface0 px-2.5 py-1 text-[11px] font-semibold text-ops-subtext">
            {alertPurposeLabel(alert)}
          </span>
        </div>
        <h2 className="mt-3 text-xl font-black text-ops-text">{alert.alert_name || '系统告警'}</h2>
        <p className="mt-2 text-sm leading-6 text-ops-subtext">{alert.description || '-'}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-ops-overlay">
          <span className="rounded border border-ops-surface1 bg-ops-dark/25 px-2 py-1">主机 {alert.host || '-'}</span>
          <span className="rounded border border-ops-surface1 bg-ops-dark/25 px-2 py-1">重复 {alert.repeat_count || 1} 次</span>
          <span className="rounded border border-ops-surface1 bg-ops-dark/25 px-2 py-1">{alert.automation_decision?.run_ai ? '会走 AI' : '只记录'}</span>
        </div>
      </div>

      <div className="shrink-0 border-b border-ops-surface0 bg-ops-dark/10 px-4 py-2">
        <div className="grid grid-cols-4 gap-1">
          {DETAIL_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-lg px-2 py-2 text-xs font-semibold transition-colors ${
                activeTab === tab.id
                  ? 'bg-ops-accent text-ops-dark'
                  : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {isWebhookTestAlert(alert) && (
              <section className="rounded-lg border border-ops-accent/35 bg-ops-accent/10 p-4">
                <div className="text-sm font-semibold text-ops-text">接入测试已进入事件队列</div>
                <p className="mt-2 text-xs leading-5 text-ops-subtext">
                  这条告警用于验证 Webhook 接收、归一化、分类降噪和事件详情链路。默认只记录，不触发 AI 分析、不发送通知、不执行修复。
                </p>
              </section>
            )}

            <AlertFlowSteps alert={alert} />

            <section className="rounded-lg border border-ops-accent/25 bg-ops-dark/25 p-4">
              <div className="text-sm font-semibold text-ops-text">下一步</div>
              <p className="mt-2 text-sm leading-6 text-ops-subtext">{nextStepLabel(alert)}</p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                <button
                  disabled={busy}
                  onClick={() => onUpdate(alert, 'acknowledged')}
                  className="ops-primary-action px-3 py-2 text-sm disabled:opacity-50"
                >
                  接手处理
                </button>
                <button
                  disabled={busy}
                  onClick={() => setActiveTab('workflow')}
                  className="ops-muted-action px-3 py-2 text-sm disabled:opacity-50"
                >
                  看 AI 与会话
                </button>
                <button
                  disabled={busy}
                  onClick={() => onUpdate(alert, 'closed')}
                  className="ops-muted-action px-3 py-2 text-sm disabled:opacity-50"
                >
                  关闭
                </button>
              </div>
            </section>

            <section className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
                <div className="mb-3 text-sm font-semibold text-ops-text">影响对象</div>
                <div className="grid gap-2 text-xs text-ops-subtext">
                  <AlertInfo label="主机" value={alert.host || '-'} />
                  <AlertInfo label="来源" value={alertSourceLabel(alert.source_family || alert.source_type || alert.source)} />
                  <AlertInfo label="类型" value={alertPurposeLabel(alert)} />
                  <AlertInfo label="优先级" value={alertPriorityLabel(alert.priority)} />
                </div>
              </div>
              <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
                <div className="mb-3 text-sm font-semibold text-ops-text">平台动作</div>
                <div className="grid gap-2 text-xs text-ops-subtext">
                  <AlertInfo label="降噪" value={alertNoiseActionLabel(alert.noise_action)} />
                  <AlertInfo label="AI" value={alert.automation_decision?.run_ai ? '只读分析' : '不自动分析'} />
                  <AlertInfo label="通知" value={alert.automation_decision?.notify ? notificationChannelLabel(alert) : '不通知'} />
                  <AlertInfo label="修复" value={remediationModeLabel(alert.automation_decision?.remediation_mode)} />
                </div>
              </div>
            </section>

            <details className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
              <summary className="cursor-pointer text-sm font-semibold text-ops-text">更多信息</summary>
              <div className="grid gap-2 text-xs text-ops-subtext">
                <AlertInfo label="事件ID" value={alert.id} />
                <AlertInfo label="重复次数" value={alert.repeat_count || 1} />
                <AlertInfo label="开始" value={formatAlertDate(alert.starts_at)} />
                <AlertInfo label="恢复" value={formatAlertDate(alert.ends_at)} />
                <AlertInfo label="关闭" value={alert.closed_at ? formatAlertDate(alert.closed_at) : '-'} />
                <AlertInfo label="来源标识" value={alert.external_id || '-'} />
                <AlertInfo label="指纹" value={alert.fingerprint || '-'} />
                <AlertInfo label="策略原因" value={alert.automation_decision?.reason || '-'} />
              </div>
            </details>
          </div>
        )}

        {activeTab === 'workflow' && <AlertWorkflowPanel alert={alert} />}

        {activeTab === 'handling' && (
          <div className="space-y-4">
            <div className="ops-data-panel p-4">
              <label className="text-xs text-ops-subtext">负责人</label>
              <input
                value={assignee}
                onChange={(event) => onAssigneeChange(event.target.value)}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              />
              <label className="mt-3 block text-xs text-ops-subtext">处置备注</label>
              <textarea
                value={note}
                onChange={(event) => onNoteChange(event.target.value)}
                rows={4}
                className="ops-control mt-1 w-full resize-none px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                placeholder="记录定位、影响面、处置动作或关闭原因"
              />
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  disabled={busy}
                  onClick={() => onUpdate(alert, 'acknowledged')}
                  className="ops-primary-action px-3 py-2 text-sm disabled:opacity-50"
                >
                  接手处理
                </button>
                <button
                  disabled={busy}
                  onClick={() => onUpdate(alert, 'closed')}
                  className="ops-primary-action bg-ops-success px-3 py-2 text-sm disabled:opacity-50"
                >
                  关闭事件
                </button>
                <button
                  disabled={busy}
                  onClick={() => onUpdate(alert, 'suppressed')}
                  className="ops-muted-action px-3 py-2 text-sm disabled:opacity-50"
                >
                  抑制
                </button>
                <button
                  disabled={busy}
                  onClick={() => onUpdate(alert)}
                  className="ops-muted-action px-3 py-2 text-sm disabled:opacity-50"
                >
                  保存备注
                </button>
              </div>
            </div>

            <section>
              <div className="mb-2 text-sm font-semibold text-ops-text">处置记录</div>
              <div className="space-y-2">
                {(alert.notes || []).length === 0 && (
                  <div className="ops-data-panel px-3 py-3 text-xs text-ops-overlay">
                    暂无备注
                  </div>
                )}
                {(alert.notes || []).slice().reverse().map((item, index) => (
                  <div key={`${item.time}-${index}`} className="ops-data-panel px-3 py-3">
                    <div className="font-mono text-[11px] text-ops-overlay">{formatAlertDate(item.time)}</div>
                    <div className="mt-1 text-sm text-ops-subtext">{item.content}</div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {activeTab === 'payload' && (
          <section>
            <div className="mb-2 text-sm font-semibold text-ops-text">原始负载</div>
            <pre className="ops-data-panel max-h-[calc(100vh-14rem)] overflow-auto p-3 text-xs leading-relaxed text-ops-subtext">
              {rawPayload}
          </pre>
          </section>
        )}
      </div>
    </aside>
  )
}
