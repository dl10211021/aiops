import { useEffect, useMemo, useState } from 'react'
import InspectionReportModal from '@/components/inspection/InspectionReportModal'
import PageHeader from '@/components/layout/PageHeader'
import type { CronJob, InspectionRun } from '@/types'
import { CronActionDialog } from './CronActionDialog'
import CronJobEditorModal from './CronJobEditorModal'
import { CronEmptyState, CronJobCard } from './CronManagerParts'
import { CronReportCenter } from './CronReportCenter'
import { useCronJobActions } from './useCronJobActions'
import { useCronManagerData } from './useCronManagerData'

type CronFilter = 'all' | 'scheduled' | 'paused' | 'failed' | 'running'

function latestRunFor(job: CronJob, runsByJob: Record<string, InspectionRun[]>) {
  return runsByJob[job.id]?.[0] || null
}

function isJobRunning(job: CronJob, runsByJob: Record<string, InspectionRun[]>, busyJobId?: string | null) {
  if (busyJobId === job.id) return true
  if (job.run_state) return job.run_state.running
  return latestRunFor(job, runsByJob)?.status === 'running'
}

function CancelRunStatePanel({ job }: { job: CronJob }) {
  const runState = job.run_state
  if (!runState) {
    return (
      <div className="rounded border border-ops-alert/25 bg-ops-alert/10 px-3 py-2 text-xs leading-5 text-ops-alert">
        当前前端没有拿到运行态详情，确认后仍会向后端提交取消请求。
      </div>
    )
  }
  const total = Math.max(0, Number(runState.progress_total || 0))
  const current = Math.max(0, Number(runState.progress_current || 0))
  const percent = Math.max(0, Math.min(100, Number(runState.progress_percent || 0)))
  const target = runState.current_target
  const targetLabel = target?.host || (target?.asset_id ? `#${target.asset_id}` : '-')
  return (
    <div className="rounded border border-ops-alert/25 bg-ops-alert/10 px-3 py-2 text-xs leading-5 text-ops-subtext">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-ops-alert">{cancelStageLabel(runState.current_stage)}</span>
        <span className="font-mono text-[11px] text-ops-alert">{total > 0 ? `${current}/${total}` : '准备中'} · {percent}%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded bg-ops-dark/70">
        <div className="h-full rounded bg-ops-alert transition-all" style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-2 grid gap-1 sm:grid-cols-2">
        <span>运行编号：{runState.running_run_id || '-'}</span>
        <span>当前目标：{targetLabel}</span>
        <span>运行状态：{runState.task_status || '-'}</span>
        <span>已运行：{formatCancelDuration(runState.elapsed_ms)}</span>
      </div>
      {runState.runtime_message && (
        <div className="mt-2 rounded bg-ops-dark/30 px-2 py-1 text-ops-overlay">
          {runState.runtime_message}
        </div>
      )}
    </div>
  )
}

function cancelStageLabel(stage?: string | null) {
  return {
    starting: '准备巡检',
    resolving_targets: '解析目标',
    target_running: '目标巡检中',
    target_completed: '目标完成',
    target_failed: '目标失败',
    cancelling: '取消中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }[String(stage || '')] || stage || '运行中'
}

function formatCancelDuration(ms?: number | null) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000))
  if (totalSeconds <= 0) return '-'
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes <= 0) return `${seconds}s`
  return `${minutes}m ${seconds}s`
}

export default function CronManager() {
  const [showReportCenter, setShowReportCenter] = useState(false)
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(() => new Set())
  const {
    assets,
    jobMetrics,
    jobPage,
    jobPageSize,
    jobPagination,
    jobQuery,
    jobStatus,
    jobs,
    loadJobs,
    notificationConfig,
    runsByJob,
    setJobPage,
    setJobPageSize,
    setJobQuery,
    setJobStatus,
    setJobs,
    skills,
    templates,
  } = useCronManagerData()
  const {
    bulkBusy,
    busyJobId,
    cancelRunTarget,
    cancellingJobId,
    closeReport,
    deleteTarget,
    deletingRunId,
    form,
    handleBulkDelete,
    handleBulkPause,
    handleBulkResume,
    handleCancelRunningRun,
    handleDeleteConfirmed,
    handleDeleteReport,
    handlePauseResume,
    handleRunNowConfirmed,
    handleSave,
    openCreate,
    openEdit,
    openReport,
    reportRunId,
    runNowTarget,
    selectAsset,
    setCancelRunTarget,
    setDeleteTarget,
    setRunNowTarget,
    setShowEditor,
    setForm,
    showEditor,
    toggleSkill,
  } = useCronJobActions({ assets, loadJobs, setJobs })

  const filterItems: Array<{ id: CronFilter; label: string; count: number }> = [
    { id: 'all', label: '全部', count: jobMetrics.total },
    { id: 'running', label: '运行中', count: jobMetrics.running },
    { id: 'scheduled', label: '已调度', count: jobMetrics.scheduled },
    { id: 'paused', label: '已暂停', count: jobMetrics.paused },
    { id: 'failed', label: '异常', count: jobMetrics.failed },
  ]
  const hasAnyPlan = jobMetrics.total > 0 || Boolean(jobQuery.trim()) || jobStatus !== 'all'
  const selectedJobs = useMemo(
    () => jobs.filter((job) => selectedJobIds.has(job.id)),
    [jobs, selectedJobIds]
  )
  const selectedRunningCount = selectedJobs.filter((job) => isJobRunning(job, runsByJob, busyJobId)).length
  const allPageSelected = jobs.length > 0 && jobs.every((job) => selectedJobIds.has(job.id))

  useEffect(() => {
    const visibleIds = new Set(jobs.map((job) => job.id))
    setSelectedJobIds((current) => {
      const next = new Set([...current].filter((id) => visibleIds.has(id)))
      return next.size === current.size ? current : next
    })
  }, [jobs])

  const toggleJobSelection = (job: CronJob, selected: boolean) => {
    setSelectedJobIds((current) => {
      const next = new Set(current)
      if (selected) next.add(job.id)
      else next.delete(job.id)
      return next
    })
  }

  const togglePageSelection = () => {
    setSelectedJobIds((current) => {
      const next = new Set(current)
      if (allPageSelected) {
        jobs.forEach((job) => next.delete(job.id))
      } else {
        jobs.forEach((job) => next.add(job.id))
      }
      return next
    })
  }

  const clearSelection = () => setSelectedJobIds(new Set())

  const runBulkDelete = async () => {
    const deleted = await handleBulkDelete(selectedJobs)
    if (deleted) clearSelection()
  }

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="自动化巡检"
          title="定时巡检"
          description="面向资产中心的自动巡检计划，支持模板、通知渠道和立即执行。"
          actions={(
            <>
            <button onClick={() => void loadJobs()} className="ops-control rounded-lg px-3 py-1.5 text-sm font-semibold">
              刷新
            </button>
            <button onClick={() => setShowReportCenter(true)} className="ops-control rounded-lg px-3 py-1.5 text-sm font-semibold">
              报告中心
            </button>
            <button onClick={openCreate} className="ops-primary-action px-3 py-1.5 text-sm">
              + 新建计划
            </button>
            </>
          )}
        />

        {hasAnyPlan ? (
          <>
          <section className="ops-data-panel mb-3 p-3">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap gap-2">
                {filterItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setJobStatus(item.id)
                      setJobPage(1)
                    }}
                    className={`rounded px-3 py-1.5 text-xs font-semibold transition ${
                      jobStatus === item.id ? 'bg-ops-accent text-white' : 'ops-control text-ops-subtext hover:text-ops-text'
                    }`}
                  >
                    {item.label} {item.count}
                  </button>
                ))}
              </div>
              <input
                value={jobQuery}
                onChange={(event) => {
                  setJobQuery(event.target.value)
                  setJobPage(1)
                }}
                placeholder="搜索计划、资产、账号、模板"
                className="ops-control w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent lg:w-80"
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ops-overlay">
              <span>
                共 {jobPagination.total} 条，当前筛选 {jobPagination.filtered_total} 条；第 {jobPagination.page} / {jobPagination.page_count} 页
              </span>
              <label className="flex items-center gap-2">
                每页
                <select
                  value={jobPageSize}
                  onChange={(event) => {
                    setJobPageSize(Number(event.target.value))
                    setJobPage(1)
                  }}
                  className="ops-control px-2 py-1 text-[11px]"
                >
                  {[10, 20, 50, 100].map((size) => (
                    <option key={size} value={size}>{size}</option>
                  ))}
                </select>
              </label>
            </div>
            {jobs.length > 0 && (
              <div className="mt-3 flex flex-col gap-2 rounded border border-ops-surface0 bg-ops-dark/25 px-3 py-2 text-xs md:flex-row md:items-center md:justify-between">
                <div className="flex flex-wrap items-center gap-3 text-ops-subtext">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={allPageSelected}
                      onChange={togglePageSelection}
                      className="h-3.5 w-3.5 accent-ops-accent"
                    />
                    本页全选
                  </label>
                  <span>已选 {selectedJobs.length} 个计划{selectedRunningCount ? `，其中 ${selectedRunningCount} 个正在巡检` : ''}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={bulkBusy || selectedJobs.length === 0}
                    onClick={() => void handleBulkPause(selectedJobs)}
                    className="ops-muted-action px-3 py-1 text-xs disabled:opacity-50"
                  >
                    批量暂停
                  </button>
                  <button
                    type="button"
                    disabled={bulkBusy || selectedJobs.length === 0}
                    onClick={() => void handleBulkResume(selectedJobs)}
                    className="ops-muted-action px-3 py-1 text-xs disabled:opacity-50"
                  >
                    批量恢复
                  </button>
                  <button
                    type="button"
                    disabled={bulkBusy || selectedJobs.length === 0 || selectedRunningCount > 0}
                    onClick={() => void runBulkDelete()}
                    className="ops-danger-action px-3 py-1 text-xs disabled:opacity-50"
                    title={selectedRunningCount > 0 ? '选中计划里有正在巡检的任务，不能批量删除' : '删除选中的巡检计划'}
                  >
                    {bulkBusy ? '处理中...' : '批量删除'}
                  </button>
                  {selectedJobs.length > 0 && (
                    <button
                      type="button"
                      disabled={bulkBusy}
                      onClick={clearSelection}
                      className="ops-muted-action px-3 py-1 text-xs disabled:opacity-50"
                    >
                      清空选择
                    </button>
                  )}
                </div>
              </div>
            )}
          </section>
          <div className="grid gap-3">
            {jobs.map((job) => (
              <CronJobCard
                key={job.id}
                busy={busyJobId === job.id}
                cancelling={cancellingJobId === job.id}
                deletingRunId={deletingRunId}
                job={job}
                running={isJobRunning(job, runsByJob, busyJobId)}
                runs={runsByJob[job.id] || []}
                skills={skills}
                onCancelRun={setCancelRunTarget}
                onDelete={setDeleteTarget}
                onDeleteReport={(run) => void handleDeleteReport(run)}
                onEdit={openEdit}
                onOpenReport={openReport}
                onPauseResume={(target) => void handlePauseResume(target)}
                onRunNow={setRunNowTarget}
                onSelectChange={toggleJobSelection}
                selected={selectedJobIds.has(job.id)}
              />
            ))}
            {jobs.length === 0 && (
              <div className="ops-data-panel px-4 py-8 text-center text-sm text-ops-subtext">
                当前筛选下没有巡检计划。
              </div>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <button
              disabled={jobPage <= 1}
              onClick={() => setJobPage(Math.max(1, jobPagination.page - 1))}
              className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
            >
              上一页
            </button>
            <span className="text-xs text-ops-overlay">
              {jobPagination.page} / {jobPagination.page_count}
            </span>
            <button
              disabled={jobPage >= jobPagination.page_count}
              onClick={() => setJobPage(Math.min(jobPagination.page_count, jobPagination.page + 1))}
              className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
            >
              下一页
            </button>
          </div>
          </>
        ) : (
          <CronEmptyState onCreate={openCreate} />
        )}

        {showEditor && (
          <CronJobEditorModal
            assets={assets}
            form={form}
            notificationConfig={notificationConfig}
            skills={skills}
            templates={templates}
            onClose={() => setShowEditor(false)}
            onFormChange={setForm}
            onSave={() => void handleSave()}
            onSelectAsset={selectAsset}
            onToggleSkill={toggleSkill}
          />
        )}

        {reportRunId && <InspectionReportModal runId={reportRunId} onClose={closeReport} />}
        {showReportCenter && (
          <CronReportCenter
            onClose={() => setShowReportCenter(false)}
            onDeleted={loadJobs}
            onOpenReport={openReport}
          />
        )}
        {cancelRunTarget && (
          <CronActionDialog
            tone="alert"
            title="取消当前巡检"
            eyebrow="取消运行"
            description="取消只会停止当前正在执行的巡检运行，不会暂停该计划后续定时调度。"
            job={cancelRunTarget}
            busy={cancellingJobId === cancelRunTarget.id}
            confirmLabel="确认取消巡检"
            busyLabel="取消中..."
            onClose={() => setCancelRunTarget(null)}
            onConfirm={() => void handleCancelRunningRun(cancelRunTarget)}
          >
            <CancelRunStatePanel job={cancelRunTarget} />
          </CronActionDialog>
        )}
        {runNowTarget && (
          <CronActionDialog
            tone="accent"
            title="立即执行巡检计划"
            eyebrow="手动触发"
            description="系统会马上按该计划连接目标资产，执行巡检指令，并根据配置写入运行记录和发送通知。"
            job={runNowTarget}
            busy={busyJobId === runNowTarget.id}
            confirmLabel="确认执行"
            busyLabel="触发中..."
            onClose={() => setRunNowTarget(null)}
            onConfirm={() => void handleRunNowConfirmed()}
          />
        )}
        {deleteTarget && (
          <CronActionDialog
            tone="alert"
            title="删除巡检计划"
            eyebrow="删除计划"
            description="删除后该计划不会再定时触发，已有运行记录和报告不会自动删除。"
            job={deleteTarget}
            busy={busyJobId === deleteTarget.id}
            confirmLabel="确认删除"
            busyLabel="删除中..."
            onClose={() => setDeleteTarget(null)}
            onConfirm={() => void handleDeleteConfirmed()}
          />
        )}
      </div>
    </div>
  )
}
