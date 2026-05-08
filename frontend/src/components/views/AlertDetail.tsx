import type { AlertEvent, AlertEventStatus } from '@/types'
import { alertSourceLabel, formatAlertDate } from './alertDisplay'
import { AlertInfo, AlertSeverityBadge, AlertStatusBadge } from './AlertCenterShared'

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
  if (!alert) {
    return (
      <aside className="ops-card p-5">
        <div className="py-20 text-center text-sm text-ops-subtext">选择一条告警后查看详情</div>
      </aside>
    )
  }

  return (
    <aside className="ops-card overflow-hidden">
      <div className="ops-card-header px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <AlertStatusBadge status={alert.status} />
          <AlertSeverityBadge severity={alert.severity} />
        </div>
        <h2 className="mt-3 text-lg font-bold text-ops-text">{alert.alert_name || '系统告警'}</h2>
        <p className="mt-1 text-sm text-ops-subtext">{alert.description || '-'}</p>
      </div>

      <div className="space-y-4 p-5">
        <div className="grid gap-2 text-xs text-ops-subtext">
          <AlertInfo label="事件ID" value={alert.id} />
          <AlertInfo label="主机" value={alert.host || '-'} />
          <AlertInfo label="来源" value={alertSourceLabel(alert.source)} />
          <AlertInfo label="创建" value={formatAlertDate(alert.created_at)} />
          <AlertInfo label="更新" value={formatAlertDate(alert.updated_at)} />
          <AlertInfo label="关闭" value={alert.closed_at ? formatAlertDate(alert.closed_at) : '-'} />
        </div>

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
            rows={3}
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

        <section>
          <div className="mb-2 text-sm font-semibold text-ops-text">原始负载</div>
          <pre className="ops-data-panel max-h-72 overflow-auto p-3 text-xs leading-relaxed text-ops-subtext">
            {JSON.stringify(alert.payload || {}, null, 2)}
          </pre>
        </section>
      </div>
    </aside>
  )
}
