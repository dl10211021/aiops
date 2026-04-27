import { useCallback, useEffect, useMemo, useState } from 'react'
import { getAlertEvents, updateAlertEvent } from '@/api/client'
import { useStore } from '@/store'
import type { AlertEvent, AlertEventStatus } from '@/types'

const STATUS_OPTIONS: Array<{ id: AlertEventStatus | 'all'; label: string }> = [
  { id: 'open', label: '未处理' },
  { id: 'acknowledged', label: '处理中' },
  { id: 'closed', label: '已关闭' },
  { id: 'suppressed', label: '已抑制' },
  { id: 'all', label: '全部' },
]

const SEVERITY_OPTIONS = [
  { id: 'all', label: '全部级别' },
  { id: 'critical', label: 'Critical' },
  { id: 'warning', label: 'Warning' },
  { id: 'error', label: 'Error' },
  { id: 'major', label: 'Major' },
  { id: 'minor', label: 'Minor' },
  { id: 'info', label: 'Info' },
]

export default function AlertCenter() {
  const addToast = useStore((s) => s.addToast)
  const [status, setStatus] = useState<AlertEventStatus | 'all'>('open')
  const [severity, setSeverity] = useState('all')
  const [host, setHost] = useState('')
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [allAlerts, setAllAlerts] = useState<AlertEvent[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [assignee, setAssignee] = useState('ops-admin')
  const [note, setNote] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [filteredRes, allRes] = await Promise.all([
        getAlertEvents({ status, severity, host: host.trim(), limit: 300 }),
        getAlertEvents({ limit: 1000 }),
      ])
      const nextAlerts = filteredRes.data.alerts || []
      setAlerts(nextAlerts)
      setAllAlerts(allRes.data.alerts || [])
      setSelectedId((current) => {
        if (current && nextAlerts.some((item) => item.id === current)) return current
        return nextAlerts[0]?.id || null
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载告警事件失败')
    } finally {
      setLoading(false)
    }
  }, [host, severity, status])

  useEffect(() => { void load() }, [load])

  const selectedAlert = useMemo(
    () => alerts.find((item) => item.id === selectedId) || alerts[0] || null,
    [alerts, selectedId]
  )

  useEffect(() => {
    if (!selectedAlert) return
    setAssignee(selectedAlert.assignee || 'ops-admin')
    setNote('')
  }, [selectedAlert?.id])

  const summary = useMemo(() => {
    const byStatus: Record<string, number> = { open: 0, acknowledged: 0, closed: 0, suppressed: 0 }
    const bySeverity: Record<string, number> = {}
    for (const alert of allAlerts) {
      byStatus[alert.status] = (byStatus[alert.status] || 0) + 1
      const key = String(alert.severity || 'unknown').toLowerCase()
      bySeverity[key] = (bySeverity[key] || 0) + 1
    }
    return { byStatus, bySeverity, total: allAlerts.length }
  }, [allAlerts])

  const handleUpdate = async (alert: AlertEvent, nextStatus?: AlertEventStatus) => {
    setBusy(true)
    try {
      await updateAlertEvent(alert.id, {
        status: nextStatus,
        assignee: assignee.trim(),
        note: note.trim() || undefined,
      })
      addToast(nextStatus ? '告警状态已更新' : '处理备注已保存', 'success')
      await load()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '更新告警失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.24em] text-ops-accent">Alert Event Desk</p>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-ops-text">告警事件</h1>
            <p className="mt-1 text-sm text-ops-subtext">集中处理 Webhook 告警，跟踪负责人、处置备注和事件闭环状态。</p>
          </div>
          <button
            onClick={() => void load()}
            className="rounded-xl border border-ops-surface1 bg-ops-surface0 px-4 py-2 text-sm text-ops-text transition-colors hover:border-ops-accent/60"
          >
            刷新
          </button>
        </div>

        <div className="mb-5 grid gap-3 md:grid-cols-4">
          <Metric label="未处理" value={summary.byStatus.open || 0} tone="red" />
          <Metric label="处理中" value={summary.byStatus.acknowledged || 0} tone="amber" />
          <Metric label="已关闭" value={summary.byStatus.closed || 0} tone="green" />
          <Metric label="全部事件" value={summary.total} tone="slate" />
        </div>

        <div className="mb-5 grid gap-3 rounded-2xl border border-ops-surface0 bg-ops-panel/55 p-4 lg:grid-cols-[1fr_220px_260px]">
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((item) => (
              <button
                key={item.id}
                onClick={() => setStatus(item.id)}
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
            onChange={(e) => setSeverity(e.target.value)}
            className="rounded-xl border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            {SEVERITY_OPTIONS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
          <input
            value={host}
            onChange={(e) => setHost(e.target.value)}
            placeholder="按主机过滤"
            className="rounded-xl border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
          <section className="ops-glass overflow-hidden rounded-3xl border">
            <div className="border-b border-ops-surface0 px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold text-ops-text">事件队列</h2>
                  <p className="mt-1 text-xs text-ops-subtext">点击事件可查看原始负载和处置记录。</p>
                </div>
                <span className="rounded-full bg-ops-surface0 px-3 py-1 font-mono text-xs text-ops-accent">
                  {alerts.length} shown
                </span>
              </div>
            </div>
            <div className="divide-y divide-ops-surface0">
              {loading && <div className="p-8 text-center text-sm text-ops-subtext">正在加载告警事件...</div>}
              {!loading && alerts.length === 0 && (
                <div className="p-10 text-center text-sm text-ops-subtext">当前筛选条件下暂无告警事件</div>
              )}
              {!loading && alerts.map((alert) => (
                <button
                  key={alert.id}
                  onClick={() => setSelectedId(alert.id)}
                  className={`grid w-full gap-3 p-4 text-left transition-colors md:grid-cols-[160px_1fr_130px] ${
                    selectedAlert?.id === alert.id ? 'bg-ops-accent/10' : 'hover:bg-ops-surface0/50'
                  }`}
                >
                  <div className="min-w-0">
                    <SeverityBadge severity={alert.severity} />
                    <div className="mt-2 truncate font-mono text-xs text-ops-overlay">{alert.id}</div>
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={alert.status} />
                      <span className="truncate font-semibold text-ops-text">{alert.alert_name || 'System Alert'}</span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-sm text-ops-subtext">{alert.description || '-'}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-ops-overlay">
                      <span>{alert.host || '-'}</span>
                      <span>{alert.source || 'webhook'}</span>
                      <span>{formatDate(alert.created_at)}</span>
                    </div>
                  </div>
                  <div className="text-right text-xs text-ops-subtext">
                    <div>负责人</div>
                    <div className="mt-1 truncate font-mono text-ops-text">{alert.assignee || '-'}</div>
                    <div className="mt-3 text-ops-overlay">{alert.notes?.length || 0} notes</div>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <AlertDetail
            alert={selectedAlert}
            assignee={assignee}
            note={note}
            busy={busy}
            onAssigneeChange={setAssignee}
            onNoteChange={setNote}
            onUpdate={handleUpdate}
          />
        </div>
      </div>
    </div>
  )
}

function AlertDetail({
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
  if (!alert) {
    return (
      <aside className="ops-glass rounded-3xl border p-6">
        <div className="py-20 text-center text-sm text-ops-subtext">选择一条告警后查看详情</div>
      </aside>
    )
  }

  return (
    <aside className="ops-glass overflow-hidden rounded-3xl border">
      <div className="border-b border-ops-surface0 px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={alert.status} />
          <SeverityBadge severity={alert.severity} />
        </div>
        <h2 className="mt-3 text-lg font-bold text-ops-text">{alert.alert_name || 'System Alert'}</h2>
        <p className="mt-1 text-sm text-ops-subtext">{alert.description || '-'}</p>
      </div>

      <div className="space-y-4 p-5">
        <div className="grid gap-2 text-xs text-ops-subtext">
          <Info label="事件ID" value={alert.id} />
          <Info label="主机" value={alert.host || '-'} />
          <Info label="来源" value={alert.source || 'webhook'} />
          <Info label="创建" value={formatDate(alert.created_at)} />
          <Info label="更新" value={formatDate(alert.updated_at)} />
          <Info label="关闭" value={alert.closed_at ? formatDate(alert.closed_at) : '-'} />
        </div>

        <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
          <label className="text-xs text-ops-subtext">负责人</label>
          <input
            value={assignee}
            onChange={(e) => onAssigneeChange(e.target.value)}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
          <label className="mt-3 block text-xs text-ops-subtext">处置备注</label>
          <textarea
            value={note}
            onChange={(e) => onNoteChange(e.target.value)}
            rows={3}
            className="mt-1 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            placeholder="记录定位、影响面、处置动作或关闭原因"
          />
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button
              disabled={busy}
              onClick={() => onUpdate(alert, 'acknowledged')}
              className="rounded-lg bg-ops-accent/85 px-3 py-2 text-sm font-semibold text-ops-dark transition-opacity disabled:opacity-50"
            >
              接手处理
            </button>
            <button
              disabled={busy}
              onClick={() => onUpdate(alert, 'closed')}
              className="rounded-lg bg-ops-success/85 px-3 py-2 text-sm font-semibold text-ops-dark transition-opacity disabled:opacity-50"
            >
              关闭事件
            </button>
            <button
              disabled={busy}
              onClick={() => onUpdate(alert, 'suppressed')}
              className="rounded-lg bg-ops-surface0 px-3 py-2 text-sm text-ops-subtext transition-colors hover:text-ops-text disabled:opacity-50"
            >
              抑制
            </button>
            <button
              disabled={busy}
              onClick={() => onUpdate(alert)}
              className="rounded-lg bg-ops-surface0 px-3 py-2 text-sm text-ops-subtext transition-colors hover:text-ops-text disabled:opacity-50"
            >
              保存备注
            </button>
          </div>
        </div>

        <section>
          <div className="mb-2 text-sm font-semibold text-ops-text">处置记录</div>
          <div className="space-y-2">
            {(alert.notes || []).length === 0 && (
              <div className="rounded-xl border border-ops-surface0 bg-ops-dark/25 px-3 py-3 text-xs text-ops-overlay">
                暂无备注
              </div>
            )}
            {(alert.notes || []).slice().reverse().map((item, index) => (
              <div key={`${item.time}-${index}`} className="rounded-xl border border-ops-surface0 bg-ops-dark/25 px-3 py-3">
                <div className="font-mono text-[11px] text-ops-overlay">{formatDate(item.time)}</div>
                <div className="mt-1 text-sm text-ops-subtext">{item.content}</div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="mb-2 text-sm font-semibold text-ops-text">原始负载</div>
          <pre className="max-h-72 overflow-auto rounded-2xl border border-ops-surface0 bg-ops-dark/45 p-3 text-xs leading-relaxed text-ops-subtext">
            {JSON.stringify(alert.payload || {}, null, 2)}
          </pre>
        </section>
      </div>
    </aside>
  )
}

function Metric({ label, value, tone }: { label: string; value: number; tone: 'amber' | 'green' | 'red' | 'slate' }) {
  const toneClass = {
    amber: 'text-ops-accent',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    slate: 'text-ops-subtext',
  }[tone]
  return (
    <div className="ops-glass rounded-2xl border p-4">
      <div className="text-xs text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const normalized = String(severity || 'warning').toLowerCase()
  const cls = normalized === 'critical' || normalized === 'error'
    ? 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert'
    : normalized === 'warning' || normalized === 'major'
      ? 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent'
      : 'border-ops-success/40 bg-ops-success/10 text-ops-success'
  return <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase ${cls}`}>{normalized}</span>
}

function StatusBadge({ status }: { status: string }) {
  const normalized = String(status || 'open')
  const label: Record<string, string> = {
    open: '未处理',
    acknowledged: '处理中',
    closed: '已关闭',
    suppressed: '已抑制',
  }
  const cls: Record<string, string> = {
    open: 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert',
    acknowledged: 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent',
    closed: 'border-ops-success/40 bg-ops-success/10 text-ops-success',
    suppressed: 'border-ops-surface1 bg-ops-surface0 text-ops-subtext',
  }
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${cls[normalized] || cls.open}`}>
      {label[normalized] || normalized}
    </span>
  )
}

function Info({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-ops-overlay">{label}</span>
      <span className="truncate text-right font-mono text-ops-text">{String(value)}</span>
    </div>
  )
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}
