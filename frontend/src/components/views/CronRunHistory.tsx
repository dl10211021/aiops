import { useState } from 'react'
import type { CronJob, InspectionRun } from '@/types'
import { assetTypeLabel, protocolLabel, statusLabel } from '@/utils/assetDisplay'

export function RunHistory({
  deletingRunId,
  job,
  runs,
  onDeleteReport,
  onOpenReport,
}: {
  deletingRunId?: string | null
  job: CronJob
  runs: InspectionRun[]
  onDeleteReport: (run: InspectionRun) => void
  onOpenReport: (run: InspectionRun) => void
}) {
  const [open, setOpen] = useState(false)
  const latest = runs[0]
  if (!latest) {
    return (
      <div className="ops-data-panel mt-4 px-3 py-2 text-xs text-ops-overlay">
        暂无运行记录。手动执行或等待定时触发后会显示目标结果。
      </div>
    )
  }
  const latestStatus = effectiveRunStatus(job, latest)
  const tone = runStatusTone(latestStatus)
  const latestEvent = latestStatus === 'orphaned'
    ? { message: '后端未发现对应运行任务，已按运行中断处理。' }
    : latest.events?.[latest.events.length - 1]
  const visibleRuns = runs
  return (
    <div className="ops-data-panel mt-4 p-3">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="mb-2 flex w-full flex-wrap items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-[11px] ${tone}`}>{runStatusLabel(latestStatus)}</span>
          <span className="font-mono text-[11px] text-ops-overlay">最近 {visibleRuns.length} 次报告</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-ops-overlay">{latest.completed_at || latest.started_at}</span>
          <span className="ops-muted-action px-2.5 py-1 text-[11px] text-ops-accent">
            {open ? '收起报告列表' : '展开报告列表'}
          </span>
        </div>
      </button>
      {latestEvent && (
        <div className="mb-2 rounded border border-ops-surface0 bg-ops-dark/25 px-3 py-2 text-[11px] leading-5 text-ops-overlay">
          {latestEvent.message}
        </div>
      )}
      {open && (
        <>
      <div className="mb-3 grid max-h-72 gap-2 overflow-auto pr-1 lg:grid-cols-3">
        {visibleRuns.map((run) => {
          const displayStatus = effectiveRunStatus(job, run)
          const isActuallyRunning = displayStatus === 'running'
          return (
          <div
            key={run.id}
            className="ops-control min-w-0 px-2.5 py-2 transition hover:border-ops-accent/50"
          >
            <button
              type="button"
              onClick={() => onOpenReport(run)}
              className="block w-full text-left"
            >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-mono text-[11px] text-ops-text">{run.id}</span>
              <span className={runStatusTextClass(displayStatus)}>
                {runStatusLabel(displayStatus)}
              </span>
            </div>
            <div className="mt-1 truncate text-[11px] text-ops-overlay">
              {run.completed_at || run.started_at} · {run.target_count} 个目标
            </div>
            {displayStatus === 'orphaned' && (
              <div className="mt-1 truncate text-[11px] text-ops-alert">
                运行任务已中断，可查看或删除该报告
              </div>
            )}
            {run.notification && (
              <div className="mt-1 truncate text-[11px] text-ops-overlay">
                通知：{run.notification.message || run.notification.status || '-'}
              </div>
            )}
            </button>
            <div className="mt-2 flex items-center gap-2">
              <button
                type="button"
                onClick={() => onOpenReport(run)}
                className="ops-muted-action px-2 py-0.5 text-[11px] text-ops-accent"
              >
                查看
              </button>
              <button
                type="button"
                disabled={deletingRunId === run.id || isActuallyRunning}
                onClick={() => onDeleteReport(run)}
                className="ops-danger-action px-2 py-0.5 text-[11px] disabled:opacity-50"
                title={isActuallyRunning ? '运行中的巡检不能删除' : '删除该报告'}
              >
                {deletingRunId === run.id ? '删除中...' : '删除'}
              </button>
            </div>
          </div>
          )
        })}
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {latest.targets.slice(0, 6).map((target) => {
          const targetStatus = latestStatus === 'orphaned' && target.status === 'running' ? 'orphaned' : target.status
          return (
            <div key={`${target.asset_id || target.host}-${target.host}`} className="ops-data-panel px-2.5 py-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-ops-text">{target.host}</span>
                <span className={runStatusTextClass(targetStatus)}>{runStatusLabel(targetStatus)}</span>
              </div>
              <div className="mt-1 truncate text-[11px] text-ops-overlay">
                #{target.asset_id || '-'} {assetTypeLabel(target.asset_type || '')} / {protocolLabel(target.protocol || '')}
              </div>
            </div>
          )
        })}
      </div>
      {latest.targets.length > 6 && (
        <div className="mt-2 text-[11px] text-ops-overlay">还有 {latest.targets.length - 6} 个目标未展开显示</div>
      )}
        </>
      )}
    </div>
  )
}

function effectiveRunStatus(job: CronJob, run: InspectionRun) {
  const runState = job.run_state
  if (!runState) return run.status
  if (runState.running && runState.running_run_id === run.id) return 'running'
  if (runState.latest_run_id === run.id && runState.effective_status) return runState.effective_status
  if (run.status === 'running') return 'orphaned'
  return run.status
}

function runStatusLabel(status?: string | null) {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'orphaned') return '运行中断'
  return statusLabel(normalized || 'unknown')
}

function runStatusTone(status?: string | null) {
  const normalized = String(status || '').toLowerCase()
  return normalized === 'completed'
    ? 'text-ops-success bg-ops-success/10'
    : normalized === 'partial'
      ? 'text-ops-accent bg-ops-accent/10'
      : normalized === 'running'
        ? 'text-ops-accent bg-ops-accent/10'
      : 'text-ops-alert bg-ops-alert/10'
}

function runStatusTextClass(status?: string | null) {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'completed') return 'text-ops-success'
  if (normalized === 'partial' || normalized === 'running') return 'text-ops-accent'
  return 'text-ops-alert'
}
