import { useCallback, useEffect, useState } from 'react'
import { exportInspectionRunReport, getInspectionRunReport } from '@/api/client'
import { useStore } from '@/store'
import type { InspectionReport } from '@/types'
import { assetTypeLabel, protocolLabel, statusLabel } from '@/utils/assetDisplay'

type ReportView = 'summary' | 'html'

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
  const [activeView, setActiveView] = useState<ReportView>('summary')
  const [htmlPreview, setHtmlPreview] = useState('')
  const [htmlLoading, setHtmlLoading] = useState(false)
  const [htmlError, setHtmlError] = useState('')

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

  useEffect(() => {
    setActiveView('summary')
    setHtmlPreview('')
    setHtmlError('')
  }, [runId])

  const loadHtmlPreview = useCallback(async (force = false) => {
    if (!force && htmlPreview) return htmlPreview
    if (htmlLoading) return htmlPreview
    setHtmlLoading(true)
    setHtmlError('')
    try {
      const res = await exportInspectionRunReport(runId, 'html')
      setHtmlPreview(res.data.content)
      return res.data.content
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '加载 HTML 巡检报告失败'
      if (force) setHtmlPreview('')
      setHtmlError(message)
      return ''
    } finally {
      setHtmlLoading(false)
    }
  }, [htmlLoading, htmlPreview, runId])

  const selectView = (view: ReportView) => {
    setActiveView(view)
    if (view === 'html') void loadHtmlPreview()
  }

  const handleExport = async (format: 'markdown' | 'html' | 'json') => {
    try {
      const res = await exportInspectionRunReport(runId, format)
      downloadText(
        `inspection-${runId}.${format === 'json' ? 'json' : format === 'html' ? 'html' : 'md'}`,
        res.data.content,
        res.data.content_type
      )
      addToast('巡检报告已生成下载', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '导出巡检报告失败', 'error')
    }
  }

  const handleHtmlPreview = async () => {
    try {
      const content = htmlPreview || await loadHtmlPreview()
      if (!content) {
        addToast(htmlError || 'HTML 巡检报告尚未生成', 'error')
        return
      }
      const opened = openHtmlPreview(`inspection-${runId}.html`, content)
      if (opened) addToast('已在新窗口打开 HTML 巡检报告', 'success')
      else addToast('浏览器拦截了新窗口，请使用“导出 HTML”后本地打开', 'error')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '打开 HTML 巡检报告失败', 'error')
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
              onClick={() => void handleExport('html')}
              className="ops-primary-action px-3 py-1.5 text-xs disabled:opacity-50"
            >
              导出 HTML
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
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="inline-flex rounded-lg border border-ops-surface1 bg-ops-dark/45 p-1">
                  <ReportViewButton active={activeView === 'summary'} onClick={() => selectView('summary')}>
                    报告摘要
                  </ReportViewButton>
                  <ReportViewButton active={activeView === 'html'} onClick={() => selectView('html')}>
                    HTML 报告
                  </ReportViewButton>
                </div>
                <div className="text-xs text-ops-overlay">
                  HTML 报告可直接导出为本地文件，双击即可离线查看。
                </div>
              </div>

              {activeView === 'html' ? (
                <HtmlReportPreview
                  error={htmlError}
                  html={htmlPreview}
                  loading={htmlLoading}
                  onDownload={() => void handleExport('html')}
                  onOpenWindow={() => void handleHtmlPreview()}
                  onRetry={() => void loadHtmlPreview(true)}
                />
              ) : (
              <>
              <div className="grid gap-3 md:grid-cols-5">
                {report.score && (
                  <ReportMetric
                    label="健康分"
                    value={`${report.score.score}`}
                    tone={scoreTone(report.score.score)}
                  />
                )}
                <ReportMetric label="目标数" value={report.summary.target_count} />
                <ReportMetric label="成功" value={report.summary.success_count} tone="green" />
                <ReportMetric label="失败" value={report.summary.error_count} tone="red" />
                <ReportMetric label="成功率" value={`${report.summary.success_rate}%`} tone="amber" />
              </div>

              {report.score && (
                <section className="ops-data-panel p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-ops-text">健康评分</div>
                      <div className="mt-1 text-xs text-ops-subtext">
                        {report.score.profile_label} · {report.score.grade_label}（{report.score.grade}）
                      </div>
                    </div>
                    <div className={`rounded px-3 py-1.5 font-mono text-lg font-bold ${scoreTextClass(report.score.score)}`}>
                      {report.score.score}/100
                    </div>
                  </div>

                  {report.score.dimensions.length > 0 && (
                    <div className="mt-4 grid gap-2 md:grid-cols-5">
                      {report.score.dimensions.map((dimension) => (
                        <div key={dimension.id} className="rounded border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
                          <div className="truncate text-[11px] text-ops-overlay">{dimension.label}</div>
                          <div className={`mt-1 font-mono text-lg font-semibold ${scoreTextClass(dimension.score)}`}>
                            {dimension.score}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    <div className="rounded border border-ops-surface0 bg-ops-dark/30">
                      <div className="border-b border-ops-surface0 px-3 py-2 text-xs font-semibold text-ops-text">
                        目标得分
                      </div>
                      <div className="max-h-48 overflow-auto">
                        {report.score.target_scores.map((targetScore, index) => (
                          <div key={`${targetScore.target.asset_id || index}-${targetScore.target.host || '-'}`} className="flex items-center justify-between gap-3 border-b border-ops-surface0 px-3 py-2 text-xs last:border-b-0">
                            <div className="min-w-0">
                              <div className="truncate font-semibold text-ops-text">{targetScore.target.host || '-'}</div>
                              <div className="mt-0.5 truncate text-ops-overlay">{targetScore.profile_label}</div>
                            </div>
                            <div className={`shrink-0 font-mono text-sm font-semibold ${scoreTextClass(targetScore.score)}`}>
                              {targetScore.score}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded border border-ops-surface0 bg-ops-dark/30">
                      <div className="border-b border-ops-surface0 px-3 py-2 text-xs font-semibold text-ops-text">
                        主要扣分
                      </div>
                      <div className="max-h-48 overflow-auto">
                        {report.score.deductions.length === 0 && (
                          <div className="px-3 py-6 text-center text-xs text-ops-subtext">暂无明显扣分项</div>
                        )}
                        {report.score.deductions.map((deduction, index) => (
                          <div key={`${deduction.host || '-'}-${deduction.reason}-${index}`} className="border-b border-ops-surface0 px-3 py-2 text-xs last:border-b-0">
                            <div className="flex items-center justify-between gap-2">
                              <span className="truncate text-ops-text">{deduction.host || deduction.label}</span>
                              <span className="shrink-0 font-mono text-ops-alert">-{deduction.points}</span>
                            </div>
                            <div className="mt-1 text-ops-subtext">{deduction.reason}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {report.trace && (
                <section className="ops-data-panel p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-ops-text">AIOps Run Trace</div>
                      <div className="mt-1 font-mono text-[11px] text-ops-overlay">{report.trace.trace_id}</div>
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-center text-[11px] text-ops-subtext">
                      <TraceCounter label="事件" value={report.trace.counters.events} />
                      <TraceCounter label="目标" value={report.trace.counters.targets} />
                      <TraceCounter label="成功" value={report.trace.counters.success} />
                      <TraceCounter label="失败" value={report.trace.counters.error} />
                    </div>
                  </div>
                  <div className="mt-4 grid gap-2 md:grid-cols-4">
                    {report.trace.phases.map((phase) => (
                      <div key={phase.id} className="rounded border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-xs font-semibold text-ops-text">{phase.label}</span>
                          <span className={`rounded px-1.5 py-0.5 text-[10px] ${traceStatusClass(phase.status)}`}>
                            {traceStatusLabel(phase.status)}
                          </span>
                        </div>
                        <div className="mt-2 min-h-10 text-[11px] leading-5 text-ops-subtext">
                          {phase.detail || '-'}
                        </div>
                        <div className="mt-2 truncate font-mono text-[10px] text-ops-overlay">
                          {phase.completed_at || phase.started_at || '-'}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

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

              {report.notification && (
                <section className="ops-data-panel p-4">
                  <div className="text-sm font-semibold text-ops-text">通知结果</div>
                  <div className="mt-3 grid gap-2 text-xs text-ops-subtext md:grid-cols-2">
                    <Info label="状态" value={report.notification.status || '-'} />
                    <Info label="结果" value={report.notification.message || '-'} />
                  </div>
                </section>
              )}

              {report.events && report.events.length > 0 && (
                <section className="ops-data-panel p-4">
                  <div className="text-sm font-semibold text-ops-text">运行进度</div>
                  <div className="mt-3 max-h-52 overflow-auto rounded-lg border border-ops-surface0 bg-ops-dark/35">
                    {report.events.map((event, index) => (
                      <div key={`${event.time}-${index}`} className="flex gap-3 border-b border-ops-surface0 px-3 py-2 text-xs last:border-b-0">
                        <span className="w-40 shrink-0 font-mono text-ops-overlay">{event.time || '-'}</span>
                        <span className="min-w-0 flex-1 text-ops-subtext">{event.message || event.type}</span>
                        <span className="shrink-0 text-ops-overlay">{event.status || '-'}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

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
              </>
              )}
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

function ReportViewButton({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
        active
          ? 'bg-ops-accent text-ops-dark shadow-[0_8px_24px_rgba(40,208,168,0.16)]'
          : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'
      }`}
    >
      {children}
    </button>
  )
}

function HtmlReportPreview({
  error,
  html,
  loading,
  onDownload,
  onOpenWindow,
  onRetry,
}: {
  error: string
  html: string
  loading: boolean
  onDownload: () => void
  onOpenWindow: () => void
  onRetry: () => void
}) {
  return (
    <section className="ops-data-panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">HTML 报告预览</div>
          <div className="mt-1 text-xs text-ops-subtext">这里渲染的就是导出的本地 HTML 文件内容。</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRetry}
            disabled={loading}
            className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
          >
            重新加载
          </button>
          <button
            type="button"
            onClick={onDownload}
            disabled={loading}
            className="ops-muted-action px-3 py-1.5 text-xs text-ops-accent disabled:opacity-50"
          >
            保存 HTML
          </button>
          <button
            type="button"
            onClick={onOpenWindow}
            disabled={loading || !html}
            className="ops-primary-action px-3 py-1.5 text-xs disabled:opacity-50"
          >
            新窗口打开
          </button>
        </div>
      </div>
      {loading && (
        <div className="flex h-[62vh] items-center justify-center text-sm text-ops-subtext">
          正在生成 HTML 报告预览...
        </div>
      )}
      {!loading && error && (
        <div className="m-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
          {error}
        </div>
      )}
      {!loading && !error && html && (
        <iframe
          className="h-[62vh] w-full bg-white"
          sandbox=""
          srcDoc={html}
          title="HTML 巡检报告预览"
        />
      )}
      {!loading && !error && !html && (
        <div className="flex h-[62vh] items-center justify-center text-sm text-ops-subtext">
          暂无 HTML 报告内容。
        </div>
      )}
    </section>
  )
}

function scoreTone(score: number): 'green' | 'amber' | 'red' {
  if (score >= 80) return 'green'
  if (score >= 60) return 'amber'
  return 'red'
}

function scoreTextClass(score: number) {
  if (score >= 80) return 'text-ops-success'
  if (score >= 60) return 'text-ops-accent'
  return 'text-ops-alert'
}

function TraceCounter({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-ops-surface0 bg-ops-surface0/45 px-2 py-1">
      <div className="font-mono text-sm font-semibold text-ops-text">{value}</div>
      <div className="text-ops-overlay">{label}</div>
    </div>
  )
}

function traceStatusClass(status: string) {
  const normalized = String(status || '').toLowerCase()
  if (['completed', 'success'].includes(normalized)) return 'bg-ops-success/10 text-ops-success'
  if (['running', 'partial'].includes(normalized)) return 'bg-ops-accent/10 text-ops-accent'
  if (['failed', 'error'].includes(normalized)) return 'bg-ops-alert/10 text-ops-alert'
  if (normalized === 'cancelled') return 'bg-ops-alert/10 text-ops-alert'
  return 'bg-ops-surface0 text-ops-overlay'
}

function traceStatusLabel(status: string) {
  const normalized = String(status || '').toLowerCase()
  return {
    completed: '完成',
    success: '成功',
    running: '运行中',
    partial: '部分完成',
    failed: '失败',
    error: '失败',
    cancelled: '已取消',
    skipped: '跳过',
    pending: '等待',
  }[normalized] || status || '-'
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

function openHtmlPreview(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const win = window.open(url, '_blank')
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  if (!win) return false
  try {
    win.document.title = filename
  } catch {
    // Blob preview may be cross-origin in some browser modes.
  }
  return true
}
