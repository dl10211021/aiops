import { useCallback, useEffect, useState } from 'react'
import {
  getDashboardAlertTrend,
  getDashboardInspectionRunTrend,
  getDashboardOverview,
  getDashboardRiskRanking,
  getDashboardToolsets,
} from '@/api/client'
import type { AlertTrendPoint, DashboardOverview, InspectionTrendPoint, RiskRankingItem, SessionToolCatalog } from '@/types'

export default function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [trend, setTrend] = useState<AlertTrendPoint[]>([])
  const [inspectionTrend, setInspectionTrend] = useState<InspectionTrendPoint[]>([])
  const [ranking, setRanking] = useState<RiskRankingItem[]>([])
  const [toolsets, setToolsets] = useState<SessionToolCatalog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [overviewRes, trendRes, inspectionTrendRes, rankingRes, toolsetRes] = await Promise.all([
        getDashboardOverview(),
        getDashboardAlertTrend(),
        getDashboardInspectionRunTrend(),
        getDashboardRiskRanking(),
        getDashboardToolsets(),
      ])
      setOverview(overviewRes.data)
      setTrend(trendRes.data.points || [])
      setInspectionTrend(inspectionTrendRes.data.points || [])
      setRanking(rankingRes.data.ranking || [])
      setToolsets(toolsetRes.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载总览失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const summary = overview?.summary || {}
  const alerts = overview?.alerts
  const jobs = overview?.jobs
  const inspectionRuns = overview?.inspection_runs
  const enabledTools = (toolsets?.toolsets || []).flatMap((set) => set.tools.filter((tool) => tool.enabled))
  const enabledToolsets = (toolsets?.toolsets || []).filter((set) => set.enabled)

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.24em] text-ops-accent">AIOps Command Center</p>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-ops-text">运维总览</h1>
            <p className="mt-1 text-sm text-ops-subtext">资产、会话、巡检、告警和工具覆盖的统一入口，后续大屏可直接复用这些接口。</p>
          </div>
          <button
            onClick={() => void load()}
            className="rounded-xl border border-ops-surface1 bg-ops-surface0 px-4 py-2 text-sm text-ops-text transition-colors hover:border-ops-accent/60"
          >
            刷新
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="资产总数" value={summary.asset_total || 0} hint="Data center assets" />
          <MetricCard label="在线会话" value={summary.active_sessions || 0} hint="Active AI sessions" tone="green" />
          <MetricCard label="待处理告警" value={alerts?.by_status?.open || alerts?.total || 0} hint={`总告警 ${alerts?.total || 0}`} tone="red" />
          <MetricCard label="巡检任务" value={jobs?.total || 0} hint={`运行 ${jobs?.scheduled || 0} / 暂停 ${jobs?.paused || 0}`} tone="amber" />
          <MetricCard label="巡检成功率" value={inspectionRuns?.success_rate || 0} suffix="%" hint={`${inspectionRuns?.completed || 0}/${inspectionRuns?.total_runs || 0} runs`} tone="green" />
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <section className="ops-glass overflow-hidden rounded-3xl border">
            <div className="border-b border-ops-surface0 px-5 py-4">
              <h2 className="text-base font-bold text-ops-text">资产与协议分布</h2>
              <p className="mt-1 text-xs text-ops-subtext">用于判断当前平台是否覆盖数据中心关键对象。</p>
            </div>
            <div className="grid gap-4 p-5 lg:grid-cols-2">
              <BarList title="资产分类" data={overview?.by_category || {}} />
              <BarList title="登录协议" data={overview?.by_protocol || {}} />
            </div>
          </section>

          <section className="ops-glass overflow-hidden rounded-3xl border">
            <div className="border-b border-ops-surface0 px-5 py-4">
              <h2 className="text-base font-bold text-ops-text">会话与工具覆盖</h2>
              <p className="mt-1 text-xs text-ops-subtext">确认 AI 是否知道当前资产对应的协议工具。</p>
            </div>
            <div className="space-y-4 p-5">
              <BarList title="在线会话协议" data={overview?.active_by_protocol || {}} empty="暂无在线会话" />
              <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/35 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-ops-text">工具集</span>
                  <span className="font-mono text-xs text-ops-accent">{enabledToolsets.length} sets / {enabledTools.length} tools</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {enabledToolsets.slice(0, 8).map((set) => (
                    <span key={set.id} className="rounded-full bg-ops-surface0 px-2.5 py-1 text-[11px] text-ops-subtext">
                      {set.id}
                    </span>
                  ))}
                  {enabledToolsets.length === 0 && <span className="text-xs text-ops-overlay">暂无工具集数据</span>}
                </div>
              </div>
            </div>
          </section>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-3">
          <section className="ops-glass rounded-3xl border p-5 xl:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-ops-text">告警趋势</h2>
                <p className="mt-1 text-xs text-ops-subtext">按日期聚合，后续大屏可替换为实时图表。</p>
              </div>
              <span className="rounded-full bg-ops-surface0 px-3 py-1 text-xs text-ops-subtext">{trend.length} days</span>
            </div>
            <TrendStrip points={trend} />
          </section>

          <section className="ops-glass rounded-3xl border p-5">
            <h2 className="text-base font-bold text-ops-text">风险主机排行</h2>
            <div className="mt-4 space-y-3">
              {ranking.slice(0, 8).map((item, index) => (
                <div key={item.host} className="flex items-center gap-3 rounded-2xl border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ops-accent/15 font-mono text-xs text-ops-accent">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-ops-text">{item.host}</div>
                    <div className="text-[11px] text-ops-overlay">{item.count} alerts</div>
                  </div>
                  <span className="font-mono text-sm text-ops-alert">{item.score}</span>
                </div>
              ))}
              {ranking.length === 0 && <div className="py-8 text-center text-sm text-ops-subtext">暂无风险排行数据</div>}
            </div>
          </section>
        </div>

        <section className="ops-glass mt-5 rounded-3xl border p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-ops-text">巡检运行健康度</h2>
              <p className="mt-1 text-xs text-ops-subtext">来自定时巡检运行记录，可直接用于后续大屏 SLA 指标。</p>
            </div>
            <span className="rounded-full bg-ops-surface0 px-3 py-1 font-mono text-xs text-ops-accent">
              targets {inspectionRuns?.targets_success || 0}/{inspectionRuns?.targets_total || 0}
            </span>
          </div>
          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
              <BarList
                title="运行状态"
                data={{
                  completed: inspectionRuns?.completed || 0,
                  partial: inspectionRuns?.partial || 0,
                  failed: inspectionRuns?.failed || 0,
                  empty: inspectionRuns?.empty || 0,
                }}
              />
            </div>
            <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
              <div className="mb-3 text-sm font-semibold text-ops-text">最近失败/部分失败</div>
              <div className="space-y-2">
                {(inspectionRuns?.recent_failures || []).slice(0, 5).map((run) => (
                  <div key={run.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-ops-surface0/60 px-3 py-2 text-xs">
                    <span className="rounded bg-ops-alert/15 px-2 py-0.5 text-ops-alert">{run.status}</span>
                    <span className="font-mono text-ops-overlay">{run.job_id}</span>
                    <span className="text-ops-subtext">{run.target_scope}:{run.scope_value || '-'}</span>
                    <span className="ml-auto text-ops-overlay">{run.completed_at}</span>
                  </div>
                ))}
                {(inspectionRuns?.recent_failures || []).length === 0 && (
                  <div className="py-8 text-center text-sm text-ops-subtext">暂无失败巡检记录</div>
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4 lg:col-span-2">
              <div className="mb-3 text-sm font-semibold text-ops-text">巡检成功率与耗时趋势</div>
              <InspectionTrendStrip points={inspectionTrend} />
            </div>
          </div>
        </section>

        {loading && <div className="mt-4 text-xs text-ops-overlay">正在刷新总览数据...</div>}
      </div>
    </div>
  )
}

function InspectionTrendStrip({ points }: { points: InspectionTrendPoint[] }) {
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
            <span>{point.total_runs} runs</span>
            <span>{Math.round(point.avg_duration_ms)} ms avg</span>
          </div>
          <div className="mt-1 h-1 overflow-hidden rounded-full bg-ops-dark">
            <div className="h-full rounded-full bg-ops-accent" style={{ width: `${Math.max(4, Math.min((point.avg_duration_ms / maxDuration) * 100, 100))}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function MetricCard({ label, value, hint, tone = 'default', suffix = '' }: { label: string; value: number; hint: string; tone?: 'default' | 'green' | 'red' | 'amber'; suffix?: string }) {
  const toneClass = {
    default: 'text-ops-text',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    amber: 'text-ops-accent',
  }[tone]
  return (
    <div className="ops-glass rounded-3xl border p-5">
      <div className="text-[10px] uppercase tracking-[0.2em] text-ops-overlay">{label}</div>
      <div className={`mt-3 font-mono text-4xl font-black ${toneClass}`}>{value}{suffix}</div>
      <div className="mt-2 text-xs text-ops-subtext">{hint}</div>
    </div>
  )
}

function BarList({ title, data, empty = '暂无数据' }: { title: string; data: Record<string, number>; empty?: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 10)
  const max = Math.max(...entries.map(([, value]) => value), 1)
  return (
    <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
      <div className="mb-3 text-sm font-semibold text-ops-text">{title}</div>
      <div className="space-y-2.5">
        {entries.map(([key, value]) => (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="truncate text-ops-subtext">{key}</span>
              <span className="font-mono text-ops-text">{value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ops-surface0">
              <div className="h-full rounded-full bg-gradient-to-r from-ops-accent to-ops-success" style={{ width: `${Math.max(8, (value / max) * 100)}%` }} />
            </div>
          </div>
        ))}
        {entries.length === 0 && <div className="py-6 text-center text-xs text-ops-overlay">{empty}</div>}
      </div>
    </div>
  )
}

function TrendStrip({ points }: { points: AlertTrendPoint[] }) {
  const recent = points.slice(-14)
  const max = Math.max(...recent.map((p) => Number(p.total || 0)), 1)
  if (recent.length === 0) {
    return <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 py-12 text-center text-sm text-ops-subtext">暂无告警趋势数据</div>
  }
  return (
    <div className="flex h-52 items-end gap-2 rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
      {recent.map((point) => {
        const total = Number(point.total || 0)
        return (
          <div key={point.date} className="flex h-full min-w-0 flex-1 flex-col justify-end gap-2">
            <div
              className="min-h-2 rounded-t-xl bg-gradient-to-t from-ops-alert via-ops-accent to-ops-success shadow-[0_0_24px_rgba(243,177,90,0.18)]"
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
