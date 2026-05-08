import { useCallback, useEffect, useState } from 'react'
import { exportInspectionRunReport, getInspectionRunReport } from '@/api/client'
import { useStore } from '@/store'
import type { InspectionReport } from '@/types'
import { assetTypeLabel, protocolLabel, statusLabel } from '@/utils/assetDisplay'

export default function InspectionReportModal({
  runId,
  onClose,
}: {
  runId: string
  onClose: () => void
}) {
  const addToast = useStore((s) => s.addToast)
  const [report, setReport] = useState<InspectionReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await getInspectionRunReport(runId)
      setReport(res.data.report)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载巡检报告失败')
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => { void load() }, [load])

  const handleExport = async (format: 'markdown' | 'json') => {
    try {
      const res = await exportInspectionRunReport(runId, format)
      downloadText(
        `inspection-${runId}.${format === 'json' ? 'json' : 'md'}`,
        res.data.content,
        res.data.content_type
      )
      addToast('巡检报告已生成下载', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '导出巡检报告失败', 'error')
    }
  }

  return (
    <div className="ops-modal-backdrop" onClick={onClose}>
      <div
        className="ops-modal-surface max-h-[92vh] w-full max-w-5xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ops-modal-header">
          <div>
            <p className="text-[11px] font-semibold text-ops-accent">自动巡检</p>
            <h2 className="mt-1 text-lg font-bold text-ops-text">巡检报告</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              disabled={!report}
              onClick={() => void handleExport('markdown')}
              className="ops-primary-action px-3 py-1.5 text-xs disabled:opacity-50"
            >
              导出 MD
            </button>
            <button
              disabled={!report}
              onClick={() => void handleExport('json')}
              className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
            >
              导出 JSON
            </button>
            <button onClick={onClose} className="ops-muted-action px-3 py-1.5 text-xs">
              关闭
            </button>
          </div>
        </div>

        <div className="ops-modal-body max-h-[calc(92vh-76px)] p-5">
          {loading && <div className="py-16 text-center text-sm text-ops-subtext">正在加载巡检报告...</div>}
          {error && (
            <div className="rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
              {error}
            </div>
          )}
          {!loading && !error && report && (
            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-4">
                <ReportMetric label="目标数" value={report.summary.target_count} />
                <ReportMetric label="成功" value={report.summary.success_count} tone="green" />
                <ReportMetric label="失败" value={report.summary.error_count} tone="red" />
                <ReportMetric label="成功率" value={`${report.summary.success_rate}%`} tone="amber" />
              </div>

              <section className="ops-data-panel p-4">
                <div className="grid gap-2 text-xs text-ops-subtext md:grid-cols-2">
                  <Info label="运行编号" value={report.run_id} />
                  <Info label="计划编号" value={report.job_id} />
                  <Info label="状态" value={statusLabel(report.status)} />
                  <Info label="范围" value={`${report.target_scope} / ${report.scope_value || '-'}`} />
                  <Info label="开始" value={report.started_at || '-'} />
                  <Info label="完成" value={report.completed_at || '-'} />
                </div>
                <div className="mt-3 rounded-lg bg-ops-surface0/55 px-3 py-2 text-sm text-ops-subtext">
                  {report.message}
                </div>
              </section>

              <section className="ops-data-panel overflow-hidden">
                <div className="ops-data-toolbar m-3 mb-0 px-4 py-3 text-sm font-semibold text-ops-text">目标结果</div>
                <div className="divide-y divide-ops-surface0">
                  {report.targets.length === 0 && (
                    <div className="p-8 text-center text-sm text-ops-subtext">报告中暂无目标结果</div>
                  )}
                  {report.targets.map((target, index) => (
                    <div key={`${target.asset_id || index}-${target.host}`} className="p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          <span className={`rounded px-2 py-0.5 text-[11px] ${target.status === 'success' ? 'bg-ops-success/10 text-ops-success' : 'bg-ops-alert/10 text-ops-alert'}`}>
                            {statusLabel(target.status)}
                          </span>
                          <span className="truncate font-semibold text-ops-text">{target.host || '-'}</span>
                        </div>
                        <span className="font-mono text-[11px] text-ops-overlay">#{target.asset_id || '-'} {assetTypeLabel(target.asset_type || '')} / {protocolLabel(target.protocol || '')}</span>
                      </div>
                      {target.error && (
                        <div className="mt-3 rounded-lg border border-ops-alert/30 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
                          {target.error}
                        </div>
                      )}
                      {target.result && (
                        <pre className="mt-3 max-h-56 overflow-auto rounded-lg border border-ops-surface0 bg-ops-dark/55 p-3 text-xs leading-relaxed text-ops-subtext">
                          {String(target.result)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ReportMetric({ label, value, tone = 'default' }: { label: string; value: string | number; tone?: 'default' | 'green' | 'red' | 'amber' }) {
  const toneClass = {
    default: 'text-ops-text',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    amber: 'text-ops-accent',
  }[tone]
  return (
    <div className="ops-data-panel p-4">
      <div className="text-xs text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-bold ${toneClass}`}>{value}</div>
    </div>
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

function downloadText(filename: string, content: string, contentType: string) {
  const blob = new Blob([content], { type: contentType || 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
