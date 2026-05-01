import type { AssetVerificationMatrix, AssetVerificationRun, InspectionRun } from '@/types'
import { statusLabel, toolLabel } from '@/utils/assetDisplay'

export function VerificationMatrixSection({ matrix }: { matrix: AssetVerificationMatrix }) {
  return (
    <section className="mb-5 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold text-ops-text">验证矩阵</h3>
        <span className="font-mono text-xs text-ops-overlay">{matrix.coverage.supported}/{matrix.coverage.total}</span>
      </div>
      <div className="space-y-2">
        {matrix.steps.map((step) => (
          <div key={step.id} className="rounded-lg bg-ops-surface0/60 px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-ops-text">{step.label}</span>
              <span className={`rounded px-2 py-0.5 text-[11px] ${step.status === 'supported' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
                {statusLabel(step.status)}
              </span>
            </div>
            <p className="mt-1 text-xs text-ops-overlay">{step.description}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {matrix.active_tools.slice(0, 12).map((tool) => (
          <span key={tool} title={tool} className="rounded bg-ops-surface0 px-2 py-0.5 text-[10px] text-ops-subtext">{toolLabel(tool)}</span>
        ))}
      </div>
    </section>
  )
}

export function VerificationHistorySection({ runs }: { runs: AssetVerificationRun[] }) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      <h3 className="mb-3 text-sm font-bold text-ops-text">验证历史</h3>
      <div className="space-y-3">
        {runs.map((run) => (
          <div key={run.id} className="rounded-lg border border-ops-surface0 bg-ops-panel/70 p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className={`rounded px-2 py-0.5 text-[11px] ${run.status === 'success' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
                {statusLabel(run.status)}
              </span>
              <span className="font-mono text-[11px] text-ops-overlay">{run.id}</span>
              <span className="ml-auto text-[11px] text-ops-overlay">{run.completed_at}</span>
            </div>
            <div className="grid gap-2">
              {run.steps.map((step) => (
                <div key={`${run.id}-${step.id}`} className="rounded-lg bg-ops-dark/45 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-ops-text">{step.label}</span>
                    <span className={`text-[11px] ${step.status === 'success' ? 'text-ops-success' : step.status === 'skipped' ? 'text-ops-overlay' : 'text-ops-alert'}`}>
                      {statusLabel(step.status)}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-ops-overlay">{step.message}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
        {runs.length === 0 && (
          <div className="py-8 text-center text-sm text-ops-subtext">暂无验证历史，点击“执行只读验证”开始。</div>
        )}
      </div>
    </section>
  )
}

export function InspectionRunsSection({
  runs,
  onOpenInspectionReport,
}: {
  runs: InspectionRun[]
  onOpenInspectionReport: (runId: string) => void
}) {
  return (
    <section className="mt-5 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-ops-text">巡检运行</h3>
          <p className="mt-1 text-xs text-ops-overlay">按资产过滤的定时巡检结果，可直接打开报告详情。</p>
        </div>
        <span className="rounded-full bg-ops-surface0 px-2.5 py-1 font-mono text-[11px] text-ops-accent">
          {runs.length} 条记录
        </span>
      </div>
      <div className="space-y-3">
        {runs.map((run) => (
          <div key={run.id} className="rounded-lg border border-ops-surface0 bg-ops-panel/70 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-[11px] ${
                  run.status === 'completed'
                    ? 'bg-ops-success/15 text-ops-success'
                    : run.status === 'partial'
                      ? 'bg-ops-accent/15 text-ops-accent'
                      : 'bg-ops-alert/15 text-ops-alert'
                }`}
                >
                  {statusLabel(run.status)}
                </span>
                <span className="truncate font-mono text-[11px] text-ops-overlay">{run.id}</span>
              </div>
              <button
                onClick={() => onOpenInspectionReport(run.id)}
                className="rounded-lg bg-ops-accent/15 px-2.5 py-1 text-[11px] text-ops-accent hover:bg-ops-accent/25"
              >
                查看报告
              </button>
            </div>
            <div className="mt-2 grid gap-2 text-[11px] text-ops-subtext md:grid-cols-2">
              <span>任务：{run.job_id}</span>
              <span>范围：{run.target_scope} {run.scope_value || ''}</span>
              <span>目标：{run.target_count}</span>
              <span>完成：{run.completed_at || '-'}</span>
            </div>
            <div className="mt-2 truncate rounded-lg bg-ops-dark/45 px-3 py-2 text-xs text-ops-overlay">
              {run.message}
            </div>
          </div>
        ))}
        {runs.length === 0 && (
          <div className="py-8 text-center text-sm text-ops-subtext">暂无与该资产关联的巡检运行记录</div>
        )}
      </div>
    </section>
  )
}
