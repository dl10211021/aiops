import type { AssetVerificationMatrix, AssetVerificationRun, InspectionRun } from '@/types'
import { statusLabel, toolLabel } from '@/utils/assetDisplay'

export function VerificationMatrixSection({ matrix }: { matrix: AssetVerificationMatrix }) {
  const supportedProtocols = matrix.supported_protocols || []
  const operationProtocols = supportedProtocols.filter((item) => item.purpose === 'operation')
  const auxiliaryProtocols = supportedProtocols.filter((item) => item.purpose === 'monitoring' || item.purpose === 'probe')
  const currentProtocol = supportedProtocols.find((item) => item.is_current)

  const protocolChipClass = (item: (typeof supportedProtocols)[number]) => {
    if (item.is_current) return 'border-ops-accent/50 bg-ops-accent/12 text-ops-accent'
    if (item.security === 'not_recommended') return 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
    return 'border-ops-surface1 bg-ops-surface0 text-ops-subtext'
  }

  return (
    <section className="mb-5 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold text-ops-text">资产能力检查</h3>
        <span className="font-mono text-xs text-ops-overlay">
          {matrix.coverage.supported}/{matrix.coverage.total} 项可用
        </span>
      </div>
      {supportedProtocols.length > 0 && (
        <div className="mb-3 rounded-lg border border-ops-surface0 bg-ops-panel/55 px-3 py-2">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="text-[11px] font-semibold text-ops-subtext">接入协议</div>
            {currentProtocol && (
              <span className="rounded-full bg-ops-accent/10 px-2 py-0.5 text-[10px] text-ops-accent">
                当前：{currentProtocol.label}
              </span>
            )}
          </div>
          <div className="mb-2 text-[11px] text-ops-overlay">运维接入</div>
          <div className="flex flex-wrap gap-1.5">
            {operationProtocols.map((item) => (
              <span
                key={`${item.source}-${item.protocol}-${item.purpose || 'access'}`}
                className={`rounded-lg border px-2 py-1 text-[11px] ${protocolChipClass(item)}`}
                title={[item.source, item.description].filter(Boolean).join(' · ')}
              >
                {item.label}
                <span className="ml-1 font-mono opacity-70">{item.protocol}</span>
                {item.is_default && <span className="ml-1 opacity-75">默认</span>}
                {item.is_current && <span className="ml-1">当前</span>}
                {item.security === 'not_recommended' && <span className="ml-1">不推荐</span>}
              </span>
            ))}
          </div>
          {auxiliaryProtocols.length > 0 && (
            <details className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
              <summary className="cursor-pointer text-[11px] font-semibold text-ops-subtext">
                辅助采集/探测 {auxiliaryProtocols.length} 项
              </summary>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {auxiliaryProtocols.map((item) => (
                  <span
                    key={`${item.source}-${item.protocol}-${item.purpose || 'aux'}`}
                    className={`rounded-lg border px-2 py-1 text-[11px] ${protocolChipClass(item)}`}
                    title={[item.source, item.description].filter(Boolean).join(' · ')}
                  >
                    {item.label}
                    <span className="ml-1 font-mono opacity-70">{item.protocol}</span>
                    {item.purpose_label && <span className="ml-1 opacity-75">{item.purpose_label}</span>}
                  </span>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
      <div className="space-y-2">
        {matrix.steps.map((step) => (
          <div key={step.id} title={step.description} className="rounded-lg bg-ops-surface0/60 px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-ops-text">{step.label}</span>
              <span className={`rounded px-2 py-0.5 text-[11px] ${step.status === 'supported' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
                {statusLabel(step.status)}
              </span>
            </div>
            {step.status !== 'supported' && <p className="mt-1 text-xs text-ops-overlay">{step.description}</p>}
          </div>
        ))}
      </div>
      {matrix.active_tools.length > 0 && (
        <details className="mt-3 rounded-lg border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
          <summary className="cursor-pointer text-[11px] font-semibold text-ops-subtext">
            可用工具 {matrix.active_tools.length} 个
          </summary>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {matrix.active_tools.map((tool) => (
              <span key={tool} title={tool} className="rounded bg-ops-surface0 px-2 py-0.5 text-[10px] text-ops-subtext">{toolLabel(tool)}</span>
            ))}
          </div>
        </details>
      )}
    </section>
  )
}

function VerificationRunCard({ run, isLatest = false }: { run: AssetVerificationRun; isLatest?: boolean }) {
  const abnormalSteps = run.steps.filter((step) => step.status !== 'success')
  const shouldOpen = run.status !== 'success' || abnormalSteps.length > 0

  return (
    <div className="rounded-lg border border-ops-surface0 bg-ops-panel/70 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-[11px] ${run.status === 'success' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
          {statusLabel(run.status)}
        </span>
        {isLatest && <span className="rounded bg-ops-accent/10 px-2 py-0.5 text-[10px] text-ops-accent">最新</span>}
        <span className="font-mono text-[11px] text-ops-overlay">{run.id}</span>
        <span className="ml-auto text-[11px] text-ops-overlay">{run.completed_at}</span>
      </div>
      <details className="mt-2" open={shouldOpen}>
        <summary className="cursor-pointer rounded-lg bg-ops-dark/45 px-3 py-2 text-[11px] text-ops-subtext">
          {abnormalSteps.length > 0 ? `查看 ${abnormalSteps.length} 个异常项` : `查看 ${run.steps.length} 项验证详情`}
        </summary>
        <div className="mt-2 grid gap-2">
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
      </details>
    </div>
  )
}

export function VerificationHistorySection({ runs }: { runs: AssetVerificationRun[] }) {
  const latestRun = runs[0]
  const olderRuns = runs.slice(1)

  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-bold text-ops-text">验证历史</h3>
        <span className="rounded-full bg-ops-surface0 px-2.5 py-1 font-mono text-[11px] text-ops-overlay">
          {runs.length} 次
        </span>
      </div>
      <div className="space-y-3">
        {latestRun && <VerificationRunCard run={latestRun} isLatest />}
        {olderRuns.length > 0 && (
          <details className="rounded-lg border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
            <summary className="cursor-pointer text-[11px] font-semibold text-ops-subtext">
              更早历史 {olderRuns.length} 次
            </summary>
            <div className="mt-3 space-y-3">
              {olderRuns.map((run) => (
                <VerificationRunCard key={run.id} run={run} />
              ))}
            </div>
          </details>
        )}
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
