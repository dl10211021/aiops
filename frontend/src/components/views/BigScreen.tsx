import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  getDashboardAlertTrend,
  getDashboardInspectionRunTrend,
  getDashboardOverview,
  getDashboardRiskRanking,
} from '@/api/client'
import type { AlertTrendPoint, DashboardOverview, InspectionTrendPoint, RiskRankingItem } from '@/types'

export default function BigScreen() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [alerts, setAlerts] = useState<AlertTrendPoint[]>([])
  const [inspection, setInspection] = useState<InspectionTrendPoint[]>([])
  const [ranking, setRanking] = useState<RiskRankingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [updatedAt, setUpdatedAt] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [overviewRes, alertRes, inspectionRes, rankingRes] = await Promise.all([
        getDashboardOverview(),
        getDashboardAlertTrend(),
        getDashboardInspectionRunTrend(),
        getDashboardRiskRanking(),
      ])
      setOverview(overviewRes.data)
      setAlerts(alertRes.data.points || [])
      setInspection(inspectionRes.data.points || [])
      setRanking(rankingRes.data.ranking || [])
      setUpdatedAt(new Date().toLocaleString())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 60_000)
    return () => window.clearInterval(timer)
  }, [load])

  const summary = overview?.summary || {}
  const latestInspection = inspection[inspection.length - 1]
  const maxAlertTotal = useMemo(
    () => Math.max(1, ...alerts.map((item) => item.total || 0)),
    [alerts]
  )

  return (
    <div className="min-h-0 flex-1 overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(243,177,90,0.16),transparent_32%),linear-gradient(135deg,#0b1117_0%,#101922_55%,#11160f_100%)] p-6 text-ops-text">
      <div className="flex h-full flex-col">
        <header className="mb-5 flex items-start justify-between gap-5">
          <div>
            <p className="text-[12px] uppercase tracking-[0.34em] text-ops-accent">AIOps Datacenter Wallboard</p>
            <h1 className="mt-2 text-5xl font-black tracking-tight">数据中心态势大屏</h1>
            <p className="mt-2 text-sm text-ops-subtext">资产、巡检、告警、风险的 60 秒自动刷新视图。</p>
          </div>
          <div className="rounded-3xl border border-ops-accent/30 bg-ops-dark/50 px-5 py-4 text-right shadow-[0_0_50px_rgba(243,177,90,0.08)]">
            <div className="text-xs text-ops-subtext">Last refresh</div>
            <div className="mt-1 font-mono text-lg text-ops-accent">{updatedAt || '-'}</div>
            <button onClick={() => void load()} className="mt-3 rounded-full bg-ops-accent px-4 py-1.5 text-xs font-bold text-ops-dark">
              手动刷新
            </button>
          </div>
        </header>

        {loading && !overview ? (
          <div className="grid flex-1 place-items-center text-ops-subtext">正在加载大屏数据...</div>
        ) : (
          <main className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[1.1fr_1fr_0.9fr]">
            <section className="grid gap-5">
              <div className="grid grid-cols-2 gap-4">
                <BigMetric label="资产总数" value={summary.asset_total || 0} hint="Assets" />
                <BigMetric label="在线会话" value={summary.active_sessions || 0} hint="Sessions" tone="green" />
                <BigMetric label="巡检成功率" value={overview?.inspection_runs?.success_rate || 0} suffix="%" hint="Inspection SLA" tone="green" />
                <BigMetric label="待处理告警" value={overview?.alerts?.by_status?.open || overview?.alerts?.total || 0} hint="Open alerts" tone="red" />
              </div>
              <Panel title="资产分类覆盖">
                <Distribution data={overview?.by_category || {}} />
              </Panel>
              <Panel title="登录协议覆盖">
                <Distribution data={overview?.by_protocol || {}} />
              </Panel>
            </section>

            <section className="grid min-h-0 gap-5">
              <Panel title="告警趋势">
                <div className="flex h-72 items-end gap-3">
                  {alerts.slice(-14).map((point) => (
                    <div key={point.date} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                      <div
                        className="w-full rounded-t-xl bg-gradient-to-t from-ops-alert to-ops-accent"
                        style={{ height: `${Math.max(10, ((point.total || 0) / maxAlertTotal) * 240)}px` }}
                        title={`${point.date}: ${point.total}`}
                      />
                      <span className="max-w-full truncate text-[10px] text-ops-overlay">{point.date.slice(5)}</span>
                    </div>
                  ))}
                  {alerts.length === 0 && <Empty text="暂无告警趋势" />}
                </div>
              </Panel>
              <Panel title="巡检健康度">
                <div className="grid grid-cols-3 gap-4">
                  <SmallMetric label="目标成功" value={overview?.inspection_runs?.targets_success || 0} />
                  <SmallMetric label="目标总数" value={overview?.inspection_runs?.targets_total || 0} />
                  <SmallMetric label="平均耗时" value={latestInspection?.avg_duration_ms || 0} suffix="ms" />
                </div>
                <div className="mt-5 space-y-2">
                  {inspection.slice(-8).map((point) => (
                    <div key={point.date} className="flex items-center gap-3">
                      <span className="w-16 font-mono text-xs text-ops-overlay">{point.date.slice(5)}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-ops-surface0">
                        <div className="h-full rounded-full bg-ops-success" style={{ width: `${Math.min(100, point.success_rate || 0)}%` }} />
                      </div>
                      <span className="w-12 text-right font-mono text-xs text-ops-success">{point.success_rate || 0}%</span>
                    </div>
                  ))}
                  {inspection.length === 0 && <Empty text="暂无巡检趋势" />}
                </div>
              </Panel>
            </section>

            <section className="min-h-0">
              <Panel title="风险主机排行" fill>
                <div className="space-y-3 overflow-y-auto pr-1">
                  {ranking.slice(0, 12).map((item, index) => (
                    <div key={item.host} className="rounded-2xl border border-ops-surface0 bg-ops-dark/45 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-3">
                          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ops-accent/15 font-mono text-sm text-ops-accent">{index + 1}</span>
                          <div className="min-w-0">
                            <div className="truncate text-base font-bold">{item.host}</div>
                            <div className="text-xs text-ops-overlay">{item.count} alerts</div>
                          </div>
                        </div>
                        <span className="font-mono text-2xl font-black text-ops-alert">{item.score}</span>
                      </div>
                    </div>
                  ))}
                  {ranking.length === 0 && <Empty text="暂无风险排行" />}
                </div>
              </Panel>
            </section>
          </main>
        )}
      </div>
    </div>
  )
}

function BigMetric({ label, value, hint, suffix = '', tone = 'amber' }: { label: string; value: number; hint: string; suffix?: string; tone?: 'amber' | 'green' | 'red' }) {
  const color = tone === 'green' ? 'text-ops-success' : tone === 'red' ? 'text-ops-alert' : 'text-ops-accent'
  return (
    <div className="rounded-3xl border border-ops-surface0 bg-ops-dark/55 p-5">
      <div className="text-xs uppercase tracking-[0.18em] text-ops-overlay">{hint}</div>
      <div className={`mt-3 font-mono text-5xl font-black ${color}`}>{value}{suffix}</div>
      <div className="mt-2 text-sm text-ops-subtext">{label}</div>
    </div>
  )
}

function Panel({ title, children, fill = false }: { title: string; children: ReactNode; fill?: boolean }) {
  return (
    <section className={`rounded-3xl border border-ops-surface0 bg-ops-dark/50 p-5 ${fill ? 'flex h-full min-h-0 flex-col' : ''}`}>
      <h2 className="mb-4 text-lg font-black tracking-tight text-ops-text">{title}</h2>
      <div className={fill ? 'min-h-0 flex-1' : ''}>{children}</div>
    </section>
  )
}

function Distribution({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 8)
  const max = Math.max(1, ...entries.map(([, value]) => value))
  if (!entries.length) return <Empty text="暂无分布数据" />
  return (
    <div className="space-y-3">
      {entries.map(([key, value]) => (
        <div key={key}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="text-ops-subtext">{key}</span>
            <span className="font-mono text-ops-accent">{value}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-ops-surface0">
            <div className="h-full rounded-full bg-ops-accent" style={{ width: `${(value / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function SmallMetric({ label, value, suffix = '' }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="rounded-2xl bg-ops-surface0 p-4">
      <div className="text-xs text-ops-overlay">{label}</div>
      <div className="mt-2 font-mono text-2xl font-bold text-ops-text">{value}{suffix}</div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="grid min-h-24 flex-1 place-items-center text-sm text-ops-overlay">{text}</div>
}
