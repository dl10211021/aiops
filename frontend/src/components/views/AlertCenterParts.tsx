import type { AlertEvent, AlertEventStatus } from '@/types'
import {
  alertNoiseActionLabel,
  alertPriorityLabel,
  alertQueueClassLabel,
  alertSourceLabel,
  formatAlertDate,
  type AlertMetricTone,
} from './alertDisplay'
import { AlertSeverityBadge, AlertStatusBadge } from './AlertCenterShared'

export { AlertDetail } from './AlertDetail'

type AlertSummary = {
  byStatus: Record<string, number>
  total: number
}

const STATUS_OPTIONS: Array<{ id: AlertEventStatus | 'all'; label: string }> = [
  { id: 'all', label: '全部' },
  { id: 'open', label: '未处理' },
  { id: 'acknowledged', label: '处理中' },
  { id: 'closed', label: '已关闭' },
  { id: 'suppressed', label: '已抑制' },
]

const SEVERITY_OPTIONS = [
  { id: 'all', label: '全部级别' },
  { id: 'critical', label: '严重' },
  { id: 'warning', label: '警告' },
  { id: 'error', label: '错误' },
  { id: 'major', label: '主要' },
  { id: 'minor', label: '次要' },
  { id: 'info', label: '信息' },
]

const SOURCE_FAMILY_OPTIONS = [
  { id: 'all', label: '全部平台' },
  { id: 'zabbix', label: 'Zabbix' },
  { id: 'prometheus', label: 'Prometheus' },
  { id: 'grafana', label: 'Grafana' },
  { id: 'manageengine', label: 'ManageEngine' },
  { id: 'generic', label: '通用接入' },
]

const AUTOMATION_OPTIONS = [
  { id: 'all', label: '全部流程' },
  { id: 'ai', label: '会走 AI' },
  { id: 'record_only', label: '只记录' },
]

export function AlertConsoleHeader({
  summary,
  onOpenPolicy,
  onRefresh,
  webhookUrl,
  testing,
  onCopy,
  onSendTest,
}: {
  summary: AlertSummary
  onOpenPolicy: () => void
  onRefresh: () => void
  webhookUrl: string
  testing: boolean
  onCopy: () => void
  onSendTest: () => void
}) {
  const flowItems = [
    { title: '接入', text: '监控平台推送告警' },
    { title: '降噪', text: '同主机同类合并' },
    { title: '分析', text: 'AI 查监控和会话' },
    { title: '通知', text: '只读建议或确认修复' },
  ]
  return (
    <section className="mb-3 overflow-hidden rounded-lg border border-ops-surface0 bg-ops-panel/80">
      <div className="flex flex-col gap-4 px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent">
              告警流程
            </span>
            <h1 className="text-xl font-black text-ops-text">告警处理台</h1>
          </div>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-ops-subtext">
            外部告警进来后先变成事件；同一机器同类告警 30 分钟内不重复拉 AI，只更新事件并转发通知。
          </p>
        </div>

        <div className="grid min-w-0 flex-1 grid-cols-2 gap-2 md:grid-cols-4 xl:max-w-xl">
          <AlertMetric label="未处理" value={summary.byStatus.open || 0} tone="red" />
          <AlertMetric label="处理中" value={summary.byStatus.acknowledged || 0} tone="amber" />
          <AlertMetric label="已关闭" value={summary.byStatus.closed || 0} tone="green" />
          <AlertMetric label="全部事件" value={summary.total} tone="slate" />
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          <button onClick={onOpenPolicy} className="ops-primary-action px-4 py-2 text-sm font-semibold">
            配置告警流程
          </button>
          <button onClick={onRefresh} className="ops-muted-action px-4 py-2 text-sm font-semibold">
            刷新
          </button>
        </div>
      </div>
      <div className="grid gap-2 border-t border-ops-surface0 bg-ops-dark/15 px-5 py-3 md:grid-cols-4">
        {flowItems.map((item, index) => (
          <div key={item.title} className="rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="grid h-5 w-5 place-items-center rounded bg-ops-accent text-[10px] font-black text-ops-dark">{index + 1}</span>
              <span className="text-xs font-semibold text-ops-text">{item.title}</span>
            </div>
            <div className="mt-1 text-[11px] text-ops-subtext">{item.text}</div>
          </div>
        ))}
      </div>
      <details className="border-t border-ops-surface0 bg-ops-dark/20 px-5 py-2">
        <summary className="cursor-pointer text-xs font-semibold text-ops-subtext hover:text-ops-text">
          接入地址和测试
        </summary>
        <div className="mt-3 flex flex-col gap-2 lg:flex-row lg:items-center">
          <code className="ops-control min-w-0 flex-1 truncate px-3 py-2 text-xs text-ops-text">
            {webhookUrl}
          </code>
          <button onClick={onCopy} className="ops-muted-action px-3 py-2 text-xs">
            复制地址
          </button>
          <button onClick={onSendTest} disabled={testing} className="ops-primary-action px-3 py-2 text-xs disabled:opacity-50">
            {testing ? '发送中...' : '发送测试告警'}
          </button>
        </div>
      </details>
    </section>
  )
}

export function AlertMetric({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: AlertMetricTone
}) {
  const toneClass = {
    amber: 'text-ops-accent',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    slate: 'text-ops-subtext',
  }[tone]
  return (
    <div className="rounded-lg bg-ops-dark/35 px-3 py-2">
      <div className="text-[11px] text-ops-subtext">{label}</div>
      <div className={`mt-0.5 font-mono text-xl font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

export function AlertFilters({
  status,
  severity,
  host,
  sourceFamily,
  automationMode,
  onStatusChange,
  onSeverityChange,
  onHostChange,
  onSourceFamilyChange,
  onAutomationModeChange,
  onReset,
}: {
  status: AlertEventStatus | 'all'
  severity: string
  host: string
  sourceFamily: string
  automationMode: string
  onStatusChange: (value: AlertEventStatus | 'all') => void
  onSeverityChange: (value: string) => void
  onHostChange: (value: string) => void
  onSourceFamilyChange: (value: string) => void
  onAutomationModeChange: (value: string) => void
  onReset: () => void
}) {
  return (
    <section className="mb-3 rounded-lg border border-ops-surface0 bg-ops-panel/45 px-3 py-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap gap-1.5">
          {STATUS_OPTIONS.map((item) => (
            <button
              key={item.id}
              onClick={() => onStatusChange(item.id)}
              className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors ${
                status === item.id
                  ? 'border-ops-accent bg-ops-accent text-ops-dark'
                  : 'border-ops-surface0 bg-ops-panel/55 text-ops-subtext hover:border-ops-surface1 hover:text-ops-text'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="grid gap-2 md:grid-cols-[240px_auto]">
          <input
            value={host}
            onChange={(event) => onHostChange(event.target.value)}
            placeholder="搜索主机 / IP"
            className="ops-control rounded-md bg-ops-panel/55 px-3 py-1.5 text-xs"
          />
          <button
            onClick={onReset}
            className="ops-muted-action rounded-md px-3 py-1.5 text-xs font-semibold"
          >
            清空
          </button>
        </div>
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer text-xs font-semibold text-ops-subtext hover:text-ops-text">
          平台、级别和 AI 流程
        </summary>
        <div className="mt-2 grid gap-2 md:grid-cols-3 xl:w-[620px]">
          <select
            value={severity}
            onChange={(event) => onSeverityChange(event.target.value)}
            className="ops-control px-3 py-1.5 text-xs"
          >
            {SEVERITY_OPTIONS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
          <select
            value={sourceFamily}
            onChange={(event) => onSourceFamilyChange(event.target.value)}
            className="ops-control px-3 py-1.5 text-xs"
          >
            {SOURCE_FAMILY_OPTIONS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
          <select
            value={automationMode}
            onChange={(event) => onAutomationModeChange(event.target.value)}
            className="ops-control px-3 py-1.5 text-xs"
          >
            {AUTOMATION_OPTIONS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
        </div>
      </details>
    </section>
  )
}

export function AlertQueueList({
  alerts,
  selectedAlert,
  loading,
  onSelect,
}: {
  alerts: AlertEvent[]
  selectedAlert: AlertEvent | null
  loading: boolean
  onSelect: (alertId: string) => void
}) {
  return (
    <section className="flex min-h-[420px] flex-col overflow-hidden rounded-lg border border-ops-surface0 bg-ops-panel/65 md:min-h-[560px] xl:max-h-[calc(100vh-14rem)]">
      <div className="shrink-0 border-b border-ops-surface0 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-ops-text">事件队列</h2>
            <p className="mt-1 text-xs text-ops-subtext">一条事件代表一组已归并的同类告警。</p>
          </div>
          <span className="ops-control px-3 py-1 text-xs text-ops-accent">
            {alerts.length} 条
          </span>
        </div>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
        {loading && <div className="p-8 text-center text-sm text-ops-subtext">正在加载告警事件...</div>}
        {!loading && alerts.map((alert) => (
          <button
            key={alert.id}
            onClick={() => onSelect(alert.id)}
            className={`w-full rounded-lg border border-l-4 px-3 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ops-accent/65 ${
              selectedAlert?.id === alert.id ? 'border-ops-surface0 border-l-ops-accent bg-ops-surface0/65' : 'border-ops-surface0 border-l-transparent bg-ops-dark/20 hover:bg-ops-surface0/45'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <AlertSeverityBadge severity={alert.severity} />
                  <AlertStatusBadge status={alert.status} />
                  <span className="rounded border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent">
                    {alertPriorityLabel(alert.priority)}
                  </span>
                </div>
                <div className="mt-2 truncate text-sm font-bold text-ops-text">{alert.alert_name || '系统告警'}</div>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-[11px] font-semibold text-ops-subtext">{alert.automation_decision?.run_ai ? 'AI 分析' : '只记录'}</div>
                <div className="mt-1 text-[10px] text-ops-overlay">重复 {alert.repeat_count || 1} 次</div>
              </div>
            </div>
            <p className="mt-2 line-clamp-2 text-sm leading-5 text-ops-subtext">{alert.description || '-'}</p>
            <div className="mt-3 grid gap-2 text-xs text-ops-subtext md:grid-cols-2">
              <div className="min-w-0 truncate">
                <span className="text-ops-overlay">主机</span>
                <span className="ml-2 font-mono text-ops-text">{alert.host || '-'}</span>
              </div>
              <div className="min-w-0 truncate">
                <span className="text-ops-overlay">来源</span>
                <span className="ml-2 text-ops-text">{alertSourceLabel(alert.source_family || alert.source_type || alert.source)}</span>
              </div>
              <div className="min-w-0 truncate">
                <span className="text-ops-overlay">类型</span>
                <span className="ml-2 text-ops-text">{alertQueueClassLabel(alert)}</span>
              </div>
              <div className="min-w-0 truncate">
                <span className="text-ops-overlay">时间</span>
                <span className="ml-2 text-ops-text">{formatAlertDate(alert.created_at)}</span>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-ops-overlay">
              <span className="rounded border border-ops-surface1 bg-ops-dark/25 px-2 py-0.5">
                {alertNoiseActionLabel(alert.noise_action)}
              </span>
              <span className="rounded border border-ops-surface1 bg-ops-dark/25 px-2 py-0.5">
                处理人 {alert.assignee || '-'}
              </span>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}

export function AlertEmptyState({
  onReset,
  onRefresh,
}: {
  onReset: () => void
  onRefresh: () => void
}) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/65 p-10">
      <div className="mx-auto max-w-xl text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg border border-ops-accent/35 bg-ops-accent/10 text-lg font-black text-ops-accent">
          !
        </div>
        <div className="mt-4 text-base font-bold text-ops-text">当前没有符合条件的告警</div>
        <p className="mt-2 text-sm leading-6 text-ops-subtext">
          可以清空筛选查看全部历史，或者发送一条测试告警确认接入链路。
        </p>
      </div>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <button
          onClick={onReset}
          className="ops-muted-action px-3 py-1.5 text-sm"
        >
          重置过滤
        </button>
        <button
          onClick={onRefresh}
          className="ops-primary-action px-3 py-1.5 text-sm"
        >
          刷新事件
        </button>
      </div>
    </section>
  )
}
