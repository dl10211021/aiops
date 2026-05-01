import type { AlertTrendPoint, InspectionTrendPoint } from '@/types'

export function MetricCard({
  label,
  value,
  hint,
  tone = 'default',
  suffix = '',
}: {
  label: string
  value: number
  hint: string
  tone?: 'default' | 'green' | 'red' | 'amber'
  suffix?: string
}) {
  const toneClass = {
    default: 'text-ops-text',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    amber: 'text-ops-accent',
  }[tone]
  return (
    <div className="ops-glass rounded-lg border p-5">
      <div className="text-xs font-medium text-ops-overlay">{label}</div>
      <div className={`mt-3 font-mono text-3xl font-black ${toneClass}`}>{value}{suffix}</div>
      <div className="mt-2 text-xs text-ops-subtext">{hint}</div>
    </div>
  )
}

export function BarList({
  title,
  data,
  empty = '暂无数据',
  formatLabel = (value: string) => value,
}: {
  title: string
  data: Record<string, number>
  empty?: string
  formatLabel?: (value: string) => string
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 10)
  const max = Math.max(...entries.map(([, value]) => value), 1)
  return (
    <div className="rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      <div className="mb-3 text-sm font-semibold text-ops-text">{title}</div>
      <div className="space-y-2.5">
        {entries.map(([key, value]) => (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="min-w-0 truncate text-ops-subtext" title={key}>{formatLabel(key)}</span>
              <span className="font-mono text-ops-text">{value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ops-surface0">
              <div className="h-full rounded-full bg-ops-success" style={{ width: `${Math.max(8, (value / max) * 100)}%` }} />
            </div>
          </div>
        ))}
        {entries.length === 0 && <div className="py-6 text-center text-xs text-ops-overlay">{empty}</div>}
      </div>
    </div>
  )
}

export function TrendStrip({ points }: { points: AlertTrendPoint[] }) {
  const recent = points.slice(-14)
  const max = Math.max(...recent.map((p) => Number(p.total || 0)), 1)
  if (recent.length === 0) {
    return <div className="rounded-lg border border-ops-surface0 bg-ops-dark/30 py-12 text-center text-sm text-ops-subtext">暂无告警趋势数据</div>
  }
  return (
    <div className="flex h-52 items-end gap-2 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-4">
      {recent.map((point) => {
        const total = Number(point.total || 0)
        return (
          <div key={point.date} className="flex h-full min-w-0 flex-1 flex-col justify-end gap-2">
            <div
              className="min-h-2 rounded-t-lg bg-ops-accent"
              style={{ height: `${Math.max(8, (total / max) * 100)}%` }}
              title={`${point.date}: ${total}`}
            />
            <div className="truncate text-center text-[10px] text-ops-overlay">{point.date.slice(5)}</div>
          </div>
        )
      })}
    </div>
  )
}

export function InspectionTrendStrip({ points }: { points: InspectionTrendPoint[] }) {
  const recent = points.slice(-14)
  const maxDuration = Math.max(...recent.map((p) => Number(p.avg_duration_ms || 0)), 1)
  if (recent.length === 0) {
    return <div className="rounded-xl border border-ops-surface0 bg-ops-dark/30 py-10 text-center text-sm text-ops-subtext">暂无巡检趋势数据</div>
  }
  return (
    <div className="grid gap-2 md:grid-cols-2">
      {recent.map((point) => (
        <div key={point.date} className="rounded-xl bg-ops-surface0/50 px-3 py-2">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-mono text-ops-text">{point.date}</span>
            <span className="text-ops-success">{point.success_rate}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-ops-dark">
            <div className="h-full rounded-full bg-ops-success" style={{ width: `${Math.max(4, Math.min(point.success_rate, 100))}%` }} />
          </div>
          <div className="mt-2 flex justify-between text-[11px] text-ops-overlay">
            <span>{point.total_runs} 次运行</span>
            <span>平均 {Math.round(point.avg_duration_ms)} ms</span>
          </div>
          <div className="mt-1 h-1 overflow-hidden rounded-full bg-ops-dark">
            <div className="h-full rounded-full bg-ops-accent" style={{ width: `${Math.max(4, Math.min((point.avg_duration_ms / maxDuration) * 100, 100))}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}
