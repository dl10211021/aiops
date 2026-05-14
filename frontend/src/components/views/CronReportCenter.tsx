import { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react'
import {
  deleteInspectionRun,
  listInspectionRuns,
  previewInspectionRunRetention,
  type InspectionRetentionPreview,
  type InspectionRunsMetrics,
  type InspectionRunsPagination,
} from '@/api/cron'
import { useStore } from '@/store'
import type { InspectionRun } from '@/types'
import { assetTypeLabel, protocolLabel, statusLabel } from '@/utils/assetDisplay'

type ReportStatusFilter = 'all' | 'completed' | 'failed' | 'partial' | 'running' | 'cancelled' | 'empty'

export function CronReportCenter({
  onClose,
  onDeleted,
  onOpenReport,
}: {
  onClose: () => void
  onDeleted: () => Promise<void>
  onOpenReport: (run: InspectionRun) => void
}) {
  const addToast = useStore((s) => s.addToast)
  const [runs, setRuns] = useState<InspectionRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [pagination, setPagination] = useState<InspectionRunsPagination>({
    page: 1,
    page_size: 25,
    total: 0,
    filtered_total: 0,
    page_count: 1,
  })
  const [query, setQuery] = useState('')
  const [retentionKeepLatest, setRetentionKeepLatest] = useState(20)
  const [retentionOlderThanDays, setRetentionOlderThanDays] = useState(90)
  const [retentionLoading, setRetentionLoading] = useState(false)
  const [retentionPreview, setRetentionPreview] = useState<InspectionRetentionPreview | null>(null)
  const [status, setStatus] = useState<ReportStatusFilter>('all')
  const [metrics, setMetrics] = useState<InspectionRunsMetrics>({
    total: 0,
    completed: 0,
    failed: 0,
    partial: 0,
    running: 0,
    cancelled: 0,
    empty: 0,
  })
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null)
  const [selectedRunIds, setSelectedRunIds] = useState<Set<string>>(() => new Set())
  const deferredQuery = useDeferredValue(query)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await listInspectionRuns({
        page,
        pageSize,
        query: deferredQuery.trim(),
        status,
      })
      setRuns(res.data.runs || [])
      setPagination(res.data.pagination || {
        page,
        page_size: pageSize,
        total: res.data.runs?.length || 0,
        filtered_total: res.data.runs?.length || 0,
        page_count: 1,
      })
      setMetrics(res.data.metrics || {
        total: res.data.runs?.length || 0,
        completed: 0,
        failed: 0,
        partial: 0,
        running: 0,
        cancelled: 0,
        empty: 0,
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载巡检报告失败')
    } finally {
      setLoading(false)
    }
  }, [deferredQuery, page, pageSize, status])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    const visibleIds = new Set(runs.map((run) => run.id))
    setSelectedRunIds((current) => {
      const next = new Set([...current].filter((id) => visibleIds.has(id)))
      return next.size === current.size ? current : next
    })
  }, [runs])

  const deletableRuns = useMemo(
    () => runs.filter((run) => String(run.status || '').toLowerCase() !== 'running'),
    [runs]
  )
  const selectedRuns = useMemo(
    () => runs.filter((run) => selectedRunIds.has(run.id)),
    [runs, selectedRunIds]
  )
  const allPageSelected = deletableRuns.length > 0 && deletableRuns.every((run) => selectedRunIds.has(run.id))

  const clearSelection = () => setSelectedRunIds(new Set())

  const toggleRunSelection = (run: InspectionRun, selected: boolean) => {
    if (String(run.status || '').toLowerCase() === 'running') return
    setSelectedRunIds((current) => {
      const next = new Set(current)
      if (selected) next.add(run.id)
      else next.delete(run.id)
      return next
    })
  }

  const togglePageSelection = () => {
    setSelectedRunIds((current) => {
      const next = new Set(current)
      if (allPageSelected) {
        deletableRuns.forEach((run) => next.delete(run.id))
      } else {
        deletableRuns.forEach((run) => next.add(run.id))
      }
      return next
    })
  }

  const handleDelete = async (run: InspectionRun) => {
    if (String(run.status || '').toLowerCase() === 'running') {
      addToast('运行中的巡检报告不能删除，请先取消或等待结束', 'error')
      return
    }
    const ok = window.confirm(`确认删除巡检报告 ${run.id}？删除后不会影响巡检计划。`)
    if (!ok) return
    setDeletingRunId(run.id)
    try {
      await deleteInspectionRun(run.id)
      setRuns((current) => current.filter((item) => item.id !== run.id))
      setSelectedRunIds((current) => {
        const next = new Set(current)
        next.delete(run.id)
        return next
      })
      setPagination((current) => ({
        ...current,
        total: Math.max(0, current.total - 1),
        filtered_total: Math.max(0, current.filtered_total - 1),
      }))
      await onDeleted()
      await load()
      addToast('巡检报告已删除', 'success')
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '删除巡检报告失败', 'error')
    } finally {
      setDeletingRunId(null)
    }
  }

  const handleBulkDelete = async () => {
    const running = selectedRuns.filter((run) => String(run.status || '').toLowerCase() === 'running')
    if (running.length > 0) {
      addToast('选中报告里有运行中记录，请等待结束后再删除', 'error')
      return
    }
    if (selectedRuns.length === 0) return
    const ok = window.confirm(`确认删除选中的 ${selectedRuns.length} 份巡检报告？删除后不会影响巡检计划。`)
    if (!ok) return
    setBulkDeleting(true)
    try {
      const results = await Promise.allSettled(selectedRuns.map((run) => deleteInspectionRun(run.id)))
      const failed = results.filter((result) => result.status === 'rejected').length
      const deletedIds = new Set(
        selectedRuns
          .filter((_, index) => results[index]?.status === 'fulfilled')
          .map((run) => run.id)
      )
      setRuns((current) => current.filter((run) => !deletedIds.has(run.id)))
      setSelectedRunIds((current) => {
        const next = new Set(current)
        deletedIds.forEach((id) => next.delete(id))
        return next
      })
      setPagination((current) => ({
        ...current,
        total: Math.max(0, current.total - deletedIds.size),
        filtered_total: Math.max(0, current.filtered_total - deletedIds.size),
      }))
      await onDeleted()
      await load()
      addToast(failed ? `已删除 ${deletedIds.size} 份报告，${failed} 份失败` : `已删除 ${deletedIds.size} 份报告`, failed ? 'error' : 'success')
    } finally {
      setBulkDeleting(false)
    }
  }

  const handleRetentionPreview = async () => {
    setRetentionLoading(true)
    try {
      const res = await previewInspectionRunRetention({
        keepLatestPerJob: retentionKeepLatest,
        olderThanDays: retentionOlderThanDays,
        limit: 8,
      })
      setRetentionPreview(res.data.preview)
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '生成归档预览失败', 'error')
    } finally {
      setRetentionLoading(false)
    }
  }

  return (
    <div className="ops-modal-backdrop" onClick={onClose}>
      <div
        className="ops-modal-surface max-h-[92vh] w-full max-w-6xl overflow-hidden"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="ops-modal-header">
          <div>
            <p className="text-[11px] font-semibold text-ops-accent">巡检报告</p>
            <h2 className="mt-1 text-lg font-bold text-ops-text">报告中心</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => void load()} className="ops-muted-action px-3 py-1.5 text-xs" disabled={loading}>
              {loading ? '刷新中...' : '刷新'}
            </button>
            <button onClick={onClose} className="ops-muted-action px-3 py-1.5 text-xs">
              关闭
            </button>
          </div>
        </div>

        <div className="ops-modal-body max-h-[calc(92vh-76px)] p-5">
          <section className="ops-data-panel mb-4 p-3">
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
              <input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value)
                  setPage(1)
                }}
                placeholder="搜索报告编号、计划、主机、账号、通知结果"
                className="ops-control w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              />
              <select
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value as ReportStatusFilter)
                  setPage(1)
                }}
                className="ops-control px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              >
                <option value="all">全部状态</option>
                <option value="completed">完成</option>
                <option value="partial">部分完成</option>
                <option value="failed">失败</option>
                <option value="running">运行中</option>
                <option value="cancelled">已取消</option>
                <option value="empty">无目标</option>
              </select>
            </div>
            <div className="mt-3 grid gap-2 text-center text-[11px] text-ops-subtext md:grid-cols-6">
              <ReportCenterMetric label="总数" value={metrics.total} />
              <ReportCenterMetric label="完成" value={metrics.completed} tone="success" />
              <ReportCenterMetric label="部分" value={metrics.partial} tone="accent" />
              <ReportCenterMetric label="失败" value={metrics.failed} tone="alert" />
              <ReportCenterMetric label="运行中" value={metrics.running} tone="accent" />
              <ReportCenterMetric label="已取消" value={metrics.cancelled} tone="alert" />
            </div>
            <div className="mt-3 rounded border border-ops-surface0 bg-ops-dark/25 p-3">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
                <div>
                  <div className="text-xs font-semibold text-ops-text">归档策略预览</div>
                  <div className="mt-1 text-[11px] text-ops-overlay">只预览建议清理项，不会自动删除报告。</div>
                </div>
                <div className="grid gap-2 sm:grid-cols-[150px_150px_auto]">
                  <label className="text-[11px] text-ops-subtext">
                    每计划保留
                    <input
                      type="number"
                      min={1}
                      max={500}
                      value={retentionKeepLatest}
                      onChange={(event) => setRetentionKeepLatest(Number(event.target.value || 20))}
                      className="ops-control mt-1 w-full px-2 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  <label className="text-[11px] text-ops-subtext">
                    早于天数
                    <input
                      type="number"
                      min={1}
                      max={3650}
                      value={retentionOlderThanDays}
                      onChange={(event) => setRetentionOlderThanDays(Number(event.target.value || 90))}
                      className="ops-control mt-1 w-full px-2 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={retentionLoading}
                    onClick={() => void handleRetentionPreview()}
                    className="ops-muted-action self-end px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    {retentionLoading ? '预览中...' : '生成预览'}
                  </button>
                </div>
              </div>
              {retentionPreview && (
                <div className="mt-3 rounded border border-ops-surface0 bg-ops-dark/30 p-3 text-xs">
                  <div className="flex flex-wrap items-center gap-3 text-ops-subtext">
                    <span>建议清理 {retentionPreview.summary.candidate_count_total} 份</span>
                    <span>本次展示 {retentionPreview.candidates.length} 份</span>
                    <span>跳过运行中 {retentionPreview.summary.skipped_running} 份</span>
                    <span>估算释放 {formatBytes(retentionPreview.summary.estimated_reclaimable_bytes)}</span>
                  </div>
                  {retentionPreview.candidates.length > 0 && (
                    <div className="mt-2 max-h-40 overflow-auto rounded border border-ops-surface0">
                      {retentionPreview.candidates.map((candidate) => (
                        <div key={candidate.id} className="grid gap-2 border-b border-ops-surface0 px-2 py-1.5 last:border-b-0 md:grid-cols-[minmax(0,1fr)_120px_minmax(0,1fr)]">
                          <span className="truncate font-mono text-ops-text">{candidate.id}</span>
                          <span className="text-ops-overlay">{candidate.completed_at || candidate.started_at || '-'}</span>
                          <span className="truncate text-ops-subtext">{candidate.reason}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {error && (
            <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
              {error}
            </div>
          )}
          {loading && <div className="py-16 text-center text-sm text-ops-subtext">正在加载巡检报告...</div>}
          {!loading && !error && (
            <section className="ops-data-panel overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ops-surface0 px-4 py-3">
                <div className="text-sm font-semibold text-ops-text">最近报告</div>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-ops-overlay">
                  <span>当前显示 {runs.length} / {pagination.filtered_total} 份；共 {pagination.total} 份</span>
                  <label className="flex items-center gap-2">
                    每页
                    <select
                      value={pageSize}
                      onChange={(event) => {
                        setPageSize(Number(event.target.value))
                        setPage(1)
                      }}
                      className="ops-control px-2 py-1 text-[11px]"
                    >
                      {[25, 50, 100, 200].map((size) => (
                        <option key={size} value={size}>{size}</option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
              {runs.length === 0 ? (
                <div className="px-4 py-12 text-center text-sm text-ops-subtext">当前筛选下没有巡检报告。</div>
              ) : (
                <>
                <div className="flex flex-col gap-2 border-b border-ops-surface0 bg-ops-dark/20 px-4 py-2 text-xs md:flex-row md:items-center md:justify-between">
                  <div className="flex flex-wrap items-center gap-3 text-ops-subtext">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={allPageSelected}
                        disabled={deletableRuns.length === 0}
                        onChange={togglePageSelection}
                        className="h-3.5 w-3.5 accent-ops-accent disabled:opacity-40"
                      />
                      本页全选
                    </label>
                    <span>已选 {selectedRuns.length} 份报告{runs.length - deletableRuns.length ? `，${runs.length - deletableRuns.length} 份运行中不可删除` : ''}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={bulkDeleting || selectedRuns.length === 0}
                      onClick={() => void handleBulkDelete()}
                      className="ops-danger-action px-3 py-1 text-xs disabled:opacity-50"
                    >
                      {bulkDeleting ? '删除中...' : '批量删除'}
                    </button>
                    {selectedRuns.length > 0 && (
                      <button
                        type="button"
                        disabled={bulkDeleting}
                        onClick={clearSelection}
                        className="ops-muted-action px-3 py-1 text-xs disabled:opacity-50"
                      >
                        清空选择
                      </button>
                    )}
                  </div>
                </div>
                <div className="max-h-[58vh] overflow-auto">
                  {runs.map((run) => {
                    const normalizedStatus = String(run.status || '').toLowerCase()
                    const running = normalizedStatus === 'running'
                    return (
                      <div key={run.id} className="grid gap-3 border-b border-ops-surface0 px-4 py-3 text-xs last:border-b-0 lg:grid-cols-[28px_minmax(0,1.15fr)_minmax(0,1fr)_120px_150px]">
                        <div className="flex items-start pt-0.5">
                          <input
                            type="checkbox"
                            checked={selectedRunIds.has(run.id)}
                            disabled={running}
                            onChange={(event) => toggleRunSelection(run, event.target.checked)}
                            className="h-3.5 w-3.5 accent-ops-accent disabled:opacity-40"
                            aria-label={`选择巡检报告 ${run.id}`}
                            title={running ? '运行中的巡检报告不能删除' : '选择该报告'}
                          />
                        </div>
                        <button type="button" onClick={() => onOpenReport(run)} className="min-w-0 text-left">
                          <div className="flex items-center gap-2">
                            <span className={`rounded px-2 py-0.5 text-[11px] ${reportStatusTone(normalizedStatus)}`}>
                              {statusLabel(normalizedStatus)}
                            </span>
                            <span className="truncate font-mono text-ops-text">{run.id}</span>
                          </div>
                          <div className="mt-1 truncate text-ops-overlay">
                            计划 {run.job_id} · {run.completed_at || run.started_at || '-'}
                          </div>
                        </button>
                        <div className="min-w-0">
                          <div className="truncate text-ops-text">{run.message || '-'}</div>
                          <div className="mt-1 truncate text-ops-overlay">{reportTargetSummary(run)}</div>
                        </div>
                        <div>
                          <div className="font-mono text-ops-text">{run.target_count} 个目标</div>
                          <div className="mt-1 text-ops-overlay">{reportResultSummary(run)}</div>
                        </div>
                        <div className="flex items-center justify-start gap-2 lg:justify-end">
                          <button
                            type="button"
                            onClick={() => onOpenReport(run)}
                            className="ops-muted-action px-2.5 py-1 text-[11px] text-ops-accent"
                          >
                            查看
                          </button>
                          <button
                            type="button"
                            disabled={deletingRunId === run.id || running}
                            onClick={() => void handleDelete(run)}
                            className="ops-danger-action px-2.5 py-1 text-[11px] disabled:opacity-50"
                            title={running ? '运行中的巡检不能删除' : '删除该报告'}
                          >
                            {deletingRunId === run.id ? '删除中...' : '删除'}
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
                </>
              )}
              {pagination.page_count > 1 && (
                <div className="flex items-center justify-between gap-2 border-t border-ops-surface0 px-4 py-3">
                  <button
                    type="button"
                    disabled={pagination.page <= 1 || loading}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    上一页
                  </button>
                  <span className="text-xs text-ops-overlay">
                    {pagination.page} / {pagination.page_count}
                  </span>
                  <button
                    type="button"
                    disabled={pagination.page >= pagination.page_count || loading}
                    onClick={() => setPage((current) => Math.min(pagination.page_count, current + 1))}
                    className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    下一页
                  </button>
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function ReportCenterMetric({
  label,
  tone = 'default',
  value,
}: {
  label: string
  tone?: 'default' | 'success' | 'alert' | 'accent'
  value: number
}) {
  const toneClass = {
    default: 'text-ops-text',
    success: 'text-ops-success',
    alert: 'text-ops-alert',
    accent: 'text-ops-accent',
  }[tone]
  return (
    <div className="rounded border border-ops-surface0 bg-ops-dark/25 px-3 py-2">
      <div className={`font-mono text-lg font-semibold ${toneClass}`}>{value}</div>
      <div>{label}</div>
    </div>
  )
}

function reportTargetSummary(run: InspectionRun) {
  const first = run.targets?.[0]
  if (!first) return `${run.target_scope} / ${run.scope_value || '-'}`
  const suffix = run.targets.length > 1 ? ` 等 ${run.targets.length} 个目标` : ''
  return `${first.host || '-'} · ${assetTypeLabel(first.asset_type || '')} / ${protocolLabel(first.protocol || '')}${suffix}`
}

function reportResultSummary(run: InspectionRun) {
  const success = run.targets?.filter((target) => target.status === 'success').length || 0
  const error = run.targets?.filter((target) => target.status === 'error').length || 0
  return `${success} 成功 / ${error} 失败`
}

function formatBytes(bytes: number) {
  const value = Math.max(0, Number(bytes || 0))
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function reportStatusTone(status: string) {
  if (status === 'completed') return 'bg-ops-success/10 text-ops-success'
  if (status === 'partial' || status === 'running') return 'bg-ops-accent/10 text-ops-accent'
  return 'bg-ops-alert/10 text-ops-alert'
}
