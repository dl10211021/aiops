import type { AlertEvent, AlertEventStatus } from '@/types'
import {
  alertClassLabel,
  alertNoiseActionLabel,
  alertPriorityLabel,
  alertSourceLabel,
  formatAlertDate,
  type AlertMetricTone,
} from './alertDisplay'
import { AlertSeverityBadge, AlertStatusBadge } from './AlertCenterShared'

export { AlertDetail } from './AlertDetail'

const STATUS_OPTIONS: Array<{ id: AlertEventStatus | 'all'; label: string }> = [
  { id: 'open', label: '未处理' },
  { id: 'acknowledged', label: '处理中' },
  { id: 'closed', label: '已关闭' },
  { id: 'suppressed', label: '已抑制' },
  { id: 'all', label: '全部' },
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
  { id: 'all', label: '全部策略' },
  { id: 'ai', label: '会触发 AI' },
  { id: 'record_only', label: '仅入库' },
]

const PLATFORM_ITEMS = [
  'Alertmanager / Grafana: 支持 alerts[]、labels、annotations、fingerprint、startsAt/endsAt。',
  'Zabbix: 支持 host、event_id、triggerid、severity、message、status 等字段。',
  'ManageEngine / 卓豪: 支持 MonitorName、AlarmName、AlarmMessage、Severity 等字段。',
  '通用 Webhook: 支持 host、alert_name、severity、description、source。',
]

const POLICY_ITEMS = [
  '按来源识别 zabbix、prometheus、grafana、manageengine、generic。',
  '按故障域识别 availability、capacity、performance、network、database、security。',
  '恢复、信息类、低优先级告警只记录；高优先级和关键基础设施告警自动进入 AI 分析。',
  'AI 分析完成后由后端统一发送企业微信、钉钉或邮件通知。',
]

export function AlertIntegrationPanel({
  webhookUrl,
  testing,
  onCopy,
  onSendTest,
}: {
  webhookUrl: string
  testing: boolean
  onCopy: () => void
  onSendTest: () => void
}) {
  return (
    <section className="ops-data-panel mb-5 p-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px_320px]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-bold text-ops-text">外部告警接入</h2>
            <span className="rounded border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent">
              Webhook
            </span>
          </div>
          <p className="mt-2 text-xs leading-5 text-ops-subtext">
            将下面地址配置到监控平台的告警通知 Webhook。系统会归一化事件、按指纹合并重复告警，先完成分类降噪，再按策略决定是否唤醒匹配主机或 localhost 值守会话。
          </p>
          <div className="mt-3 flex min-w-0 flex-wrap items-center gap-2">
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
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3">
          <div className="text-xs font-semibold text-ops-text">已适配格式</div>
          <ul className="mt-2 space-y-1.5 text-[11px] leading-5 text-ops-subtext">
            {PLATFORM_ITEMS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3">
          <div className="text-xs font-semibold text-ops-text">分类降噪策略</div>
          <ul className="mt-2 space-y-1.5 text-[11px] leading-5 text-ops-subtext">
            {POLICY_ITEMS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
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
    <div className="ops-data-panel p-4">
      <div className="text-xs text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-bold ${toneClass}`}>{value}</div>
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
}) {
  return (
    <div className="ops-data-toolbar mb-5 grid gap-3 p-3 xl:grid-cols-[1fr_190px_190px_180px_240px]">
      <div className="flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((item) => (
          <button
            key={item.id}
            onClick={() => onStatusChange(item.id)}
            className={`rounded-full border px-4 py-2 text-sm transition-colors ${
              status === item.id
                ? 'border-ops-accent bg-ops-accent text-ops-dark'
                : 'border-ops-surface1 bg-ops-surface0 text-ops-subtext hover:text-ops-text'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <select
        value={severity}
        onChange={(event) => onSeverityChange(event.target.value)}
        className="ops-control px-3 py-2 text-sm"
      >
        {SEVERITY_OPTIONS.map((item) => (
          <option key={item.id} value={item.id}>{item.label}</option>
        ))}
      </select>
      <select
        value={sourceFamily}
        onChange={(event) => onSourceFamilyChange(event.target.value)}
        className="ops-control px-3 py-2 text-sm"
      >
        {SOURCE_FAMILY_OPTIONS.map((item) => (
          <option key={item.id} value={item.id}>{item.label}</option>
        ))}
      </select>
      <select
        value={automationMode}
        onChange={(event) => onAutomationModeChange(event.target.value)}
        className="ops-control px-3 py-2 text-sm"
      >
        {AUTOMATION_OPTIONS.map((item) => (
          <option key={item.id} value={item.id}>{item.label}</option>
        ))}
      </select>
      <input
        value={host}
        onChange={(event) => onHostChange(event.target.value)}
        placeholder="按主机过滤"
        className="ops-control px-3 py-2 text-sm"
      />
    </div>
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
    <section className="ops-data-panel overflow-hidden">
      <div className="ops-data-toolbar m-3 mb-0 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-ops-text">事件队列</h2>
            <p className="mt-1 text-xs text-ops-subtext">点击事件可查看原始负载和处置记录。</p>
          </div>
          <span className="ops-control px-3 py-1 text-xs text-ops-accent">
            当前 {alerts.length} 条
          </span>
        </div>
      </div>
      <div className="divide-y divide-ops-surface0">
        {loading && <div className="p-8 text-center text-sm text-ops-subtext">正在加载告警事件...</div>}
        {!loading && alerts.map((alert) => (
          <button
            key={alert.id}
            onClick={() => onSelect(alert.id)}
            className={`grid w-full gap-3 px-4 py-3 text-left transition-colors md:grid-cols-[140px_1fr_120px] ${
              selectedAlert?.id === alert.id ? 'bg-ops-accent/10' : 'hover:bg-ops-surface0/50'
            }`}
          >
            <div className="min-w-0">
              <AlertSeverityBadge severity={alert.severity} />
              <div className="mt-2 truncate font-mono text-xs text-ops-overlay">{alert.id}</div>
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <AlertStatusBadge status={alert.status} />
                <span className="rounded border border-ops-surface1 bg-ops-surface0 px-2 py-0.5 text-[11px] font-semibold text-ops-subtext">
                  {alertSourceLabel(alert.source_family || alert.source_type || alert.source)}
                </span>
                <span className="rounded border border-ops-surface1 bg-ops-dark/30 px-2 py-0.5 text-[11px] text-ops-overlay">
                  {alertClassLabel(alert.alert_class)}
                </span>
                <span className="rounded border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent">
                  {alertPriorityLabel(alert.priority)}
                </span>
                <span className="truncate font-semibold text-ops-text">{alert.alert_name || '系统告警'}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-ops-subtext">{alert.description || '-'}</p>
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-ops-overlay">
                <span>{alert.host || '-'}</span>
                <span>{alertNoiseActionLabel(alert.noise_action)}</span>
                <span>{alert.automation_decision?.run_ai ? '会触发 AI' : '仅入库'}</span>
                <span>{formatAlertDate(alert.created_at)}</span>
              </div>
            </div>
            <div className="text-right text-xs text-ops-subtext">
              <div>负责人</div>
              <div className="mt-1 truncate font-mono text-ops-text">{alert.assignee || '-'}</div>
              <div className="mt-3 text-ops-overlay">备注 {alert.notes?.length || 0}</div>
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
    <section className="ops-data-panel p-6">
      <div className="text-sm font-semibold text-ops-text">当前筛选条件下暂无告警事件</div>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-subtext">
        可以调整状态、级别或主机过滤条件；接入告警 Webhook 后，事件会在这里进入分派、处理、备注和闭环流程。
      </p>
      <div className="mt-5 flex flex-wrap gap-2">
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
