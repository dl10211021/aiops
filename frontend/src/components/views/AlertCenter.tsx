import { useCallback, useEffect, useMemo, useState } from 'react'
import { getAlertEvents, sendAlertWebhook, updateAlertEvent } from '@/api/client'
import { useStore } from '@/store'
import {
  AlertConsoleHeader,
  AlertDetail,
  AlertEmptyState,
  AlertFilters,
  AlertQueueList,
} from './AlertCenterParts'
import { AlertPolicyDrawer } from './AlertPolicyDrawer'
import type { AlertEvent, AlertEventStatus } from '@/types'

export default function AlertCenter() {
  const addToast = useStore((s) => s.addToast)
  const [status, setStatus] = useState<AlertEventStatus | 'all'>('all')
  const [severity, setSeverity] = useState('all')
  const [host, setHost] = useState('')
  const [sourceFamily, setSourceFamily] = useState('all')
  const [automationMode, setAutomationMode] = useState('all')
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [allAlerts, setAllAlerts] = useState<AlertEvent[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [testingWebhook, setTestingWebhook] = useState(false)
  const [policyOpen, setPolicyOpen] = useState(false)
  const [error, setError] = useState('')
  const [assignee, setAssignee] = useState(() => localStorage.getItem('OPSCORE_OPERATOR') || 'user')
  const [note, setNote] = useState('')
  const webhookUrl = useMemo(() => {
    if (typeof window === 'undefined') return '/api/v1/webhook/alert'
    return `${window.location.origin}/api/v1/webhook/alert`
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [filteredRes, allRes] = await Promise.all([
        getAlertEvents({
          status,
          severity,
          host: host.trim(),
          source_family: sourceFamily,
          automation_mode: automationMode,
          limit: 300,
        }),
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
  }, [automationMode, host, severity, sourceFamily, status])

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

  const resetFilters = useCallback(() => {
    setStatus('all')
    setSeverity('all')
    setHost('')
    setSourceFamily('all')
    setAutomationMode('all')
  }, [])

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

  const handleCopyWebhookUrl = async () => {
    try {
      await navigator.clipboard.writeText(webhookUrl)
      addToast('告警 Webhook 地址已复制', 'success')
    } catch {
      addToast('复制失败，请手动选择地址', 'error')
    }
  }

  const handleSendTestAlert = async () => {
    setTestingWebhook(true)
    try {
      const res = await sendAlertWebhook({
        source: 'manual',
        source_type: 'manual',
        host: 'opscore-test.local',
        alert_name: 'OpsCore Webhook Test',
        severity: 'warning',
        description: '这是一条由告警页手动发送的接入测试告警。',
        fingerprint: `opscore-test-${Date.now()}`,
      })
      addToast(`测试告警已接收，注入会话 ${res.data.injected_count || 0} 个`, 'success')
      setStatus('open')
      setSeverity('all')
      setHost('')
      setSourceFamily('all')
      setAutomationMode('all')
      const [filteredRes, allRes] = await Promise.all([
        getAlertEvents({ status: 'open', severity: 'all', host: '', source_family: 'all', automation_mode: 'all', limit: 300 }),
        getAlertEvents({ limit: 1000 }),
      ])
      const nextAlerts = filteredRes.data.alerts || []
      setAlerts(nextAlerts)
      setAllAlerts(allRes.data.alerts || [])
      setSelectedId(res.data.alert?.id || nextAlerts[0]?.id || null)
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '测试告警发送失败', 'error')
    } finally {
      setTestingWebhook(false)
    }
  }

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <AlertConsoleHeader
          summary={summary}
          onOpenPolicy={() => setPolicyOpen(true)}
          onRefresh={() => void load()}
          webhookUrl={webhookUrl}
          testing={testingWebhook}
          onCopy={handleCopyWebhookUrl}
          onSendTest={handleSendTestAlert}
        />

        <AlertFilters
          status={status}
          severity={severity}
          host={host}
          sourceFamily={sourceFamily}
          automationMode={automationMode}
          onStatusChange={setStatus}
          onSeverityChange={setSeverity}
          onHostChange={setHost}
          onSourceFamilyChange={setSourceFamily}
          onAutomationModeChange={setAutomationMode}
          onReset={resetFilters}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        {loading || alerts.length > 0 ? (
          <div className="grid min-h-0 gap-4 xl:grid-cols-[minmax(360px,0.95fr)_minmax(520px,1.35fr)] xl:items-start">
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
            onReset={resetFilters}
            onRefresh={() => void load()}
          />
        )}
        <AlertPolicyDrawer open={policyOpen} onClose={() => setPolicyOpen(false)} />
      </div>
    </div>
  )
}
