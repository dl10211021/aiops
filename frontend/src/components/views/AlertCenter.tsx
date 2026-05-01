import { useCallback, useEffect, useMemo, useState } from 'react'
import { getAlertEvents, updateAlertEvent } from '@/api/client'
import PageHeader from '@/components/layout/PageHeader'
import { useStore } from '@/store'
import {
  AlertDetail,
  AlertEmptyState,
  AlertFilters,
  AlertMetric,
  AlertQueueList,
} from './AlertCenterParts'
import type { AlertEvent, AlertEventStatus } from '@/types'

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
  const [assignee, setAssignee] = useState(() => localStorage.getItem('OPSCORE_OPERATOR') || 'user')
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
    setAssignee(selectedAlert.assignee || localStorage.getItem('OPSCORE_OPERATOR') || 'user')
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
    if (!assignee.trim()) {
      addToast('负责人不能为空', 'error')
      return
    }
    setBusy(true)
    try {
      localStorage.setItem('OPSCORE_OPERATOR', assignee.trim())
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
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          eyebrow="告警事件台"
          title="告警事件"
          description="集中处理外部告警，跟踪负责人、处置备注和事件闭环状态。"
          actions={(
            <button
              onClick={() => void load()}
              className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-4 py-2 text-sm text-ops-text transition-colors hover:border-ops-accent/60"
            >
              刷新
            </button>
          )}
        />

        <div className="mb-5 grid gap-3 md:grid-cols-4">
          <AlertMetric label="未处理" value={summary.byStatus.open || 0} tone="red" />
          <AlertMetric label="处理中" value={summary.byStatus.acknowledged || 0} tone="amber" />
          <AlertMetric label="已关闭" value={summary.byStatus.closed || 0} tone="green" />
          <AlertMetric label="全部事件" value={summary.total} tone="slate" />
        </div>

        <AlertFilters
          status={status}
          severity={severity}
          host={host}
          onStatusChange={setStatus}
          onSeverityChange={setSeverity}
          onHostChange={setHost}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        {loading || alerts.length > 0 ? (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
            <AlertQueueList
              alerts={alerts}
              selectedAlert={selectedAlert}
              loading={loading}
              onSelect={setSelectedId}
            />

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
        ) : (
          <AlertEmptyState
            onReset={() => { setStatus('open'); setSeverity('all'); setHost('') }}
            onRefresh={() => void load()}
          />
        )}
      </div>
    </div>
  )
}
