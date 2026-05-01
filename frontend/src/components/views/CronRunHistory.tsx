import type { InspectionRun } from '@/types'
import { assetTypeLabel, protocolLabel, statusLabel } from '@/utils/assetDisplay'

export function RunHistory({
  runs,
  onOpenReport,
}: {
  runs: InspectionRun[]
  onOpenReport: (run: InspectionRun) => void
}) {
  const latest = runs[0]
  if (!latest) {
    return (
      <div className="mt-4 rounded-lg border border-ops-surface0 bg-ops-dark/25 px-3 py-2 text-xs text-ops-overlay">
        暂无运行记录。手动执行或等待定时触发后会显示目标结果。
      </div>
    )
  }
  const tone = latest.status === 'completed'
    ? 'text-ops-success bg-ops-success/10'
    : latest.status === 'partial'
      ? 'text-ops-accent bg-ops-accent/10'
      : 'text-ops-alert bg-ops-alert/10'
  return (
    <div className="mt-4 rounded-lg border border-ops-surface0 bg-ops-dark/25 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-[11px] ${tone}`}>{statusLabel(latest.status)}</span>
          <span className="font-mono text-[11px] text-ops-overlay">运行 {latest.id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-ops-overlay">{latest.completed_at}</span>
          <button
            onClick={() => onOpenReport(latest)}
            className="rounded-lg bg-ops-accent/15 px-2.5 py-1 text-[11px] text-ops-accent hover:bg-ops-accent/25"
          >
            查看报告
          </button>
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {latest.targets.slice(0, 6).map((target) => (
          <div key={`${target.asset_id || target.host}-${target.host}`} className="rounded-lg bg-ops-surface0/60 px-2.5 py-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-ops-text">{target.host}</span>
              <span className={target.status === 'success' ? 'text-ops-success' : 'text-ops-alert'}>{statusLabel(target.status)}</span>
            </div>
            <div className="mt-1 truncate text-[11px] text-ops-overlay">
              #{target.asset_id || '-'} {assetTypeLabel(target.asset_type || '')} / {protocolLabel(target.protocol || '')}
            </div>
          </div>
        ))}
      </div>
      {latest.targets.length > 6 && (
        <div className="mt-2 text-[11px] text-ops-overlay">还有 {latest.targets.length - 6} 个目标未展开显示</div>
      )}
    </div>
  )
}
