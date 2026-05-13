import { useState } from 'react'
import InspectionReportModal from '@/components/inspection/InspectionReportModal'
import PageHeader from '@/components/layout/PageHeader'
import type { CronJob, InspectionRun } from '@/types'
import { CronActionDialog } from './CronActionDialog'
import CronJobEditorModal from './CronJobEditorModal'
import { CronEmptyState, CronJobCard } from './CronManagerParts'
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

export default function CronManager() {
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
    busyJobId,
    cancellingJobId,
    closeReport,
    deleteTarget,
    deletingRunId,
    form,
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
                onCancelRun={(target) => void handleCancelRunningRun(target)}
                onDelete={setDeleteTarget}
                onDeleteReport={(run) => void handleDeleteReport(run)}
                onEdit={openEdit}
                onOpenReport={openReport}
                onPauseResume={(target) => void handlePauseResume(target)}
                onRunNow={setRunNowTarget}
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
