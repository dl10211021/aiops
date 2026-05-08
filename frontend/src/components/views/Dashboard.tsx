import PageHeader from '@/components/layout/PageHeader'
import { categoryLabel, protocolLabel, statusLabel, toolsetLabel } from '@/utils/assetDisplay'
import { BarList, InspectionTrendStrip, MetricCard, TrendStrip } from './DashboardParts'
import { useDashboardData } from './useDashboardData'

export default function Dashboard() {
  const {
    error,
    inspectionTrend,
    load,
    loading,
    overview,
    ranking,
    toolsets,
    trend,
  } = useDashboardData()

  const summary = overview?.summary || {}
  const alerts = overview?.alerts
  const jobs = overview?.jobs
  const inspectionRuns = overview?.inspection_runs
  const enabledTools = (toolsets?.toolsets || []).flatMap((set) => set.tools.filter((tool) => tool.enabled))
  const enabledToolsets = (toolsets?.toolsets || []).filter((set) => set.enabled)

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="AIOps 运维指挥中心"
          title="总览大屏"
          description="合并运维总览和数据中心趋势视图，资产、会话、巡检、告警和 SLA 指标在同一个入口查看。"
          actions={(
            <button
              onClick={() => void load()}
              className="ops-control rounded-lg px-4 py-2 text-sm font-semibold"
            >
              刷新
            </button>
          )}
        />

        {error && (
          <div className="mb-4 rounded-xl border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="资产总数" value={summary.asset_total || 0} hint="数据中心资产" />
          <MetricCard label="在线会话" value={summary.active_sessions || 0} hint="活跃 AI 会话" tone="green" />
          <MetricCard label="待处理告警" value={alerts?.by_status?.open || alerts?.total || 0} hint={`总告警 ${alerts?.total || 0}`} tone="red" />
          <MetricCard label="巡检任务" value={jobs?.total || 0} hint={`运行 ${jobs?.scheduled || 0} / 暂停 ${jobs?.paused || 0}`} tone="amber" />
          <MetricCard label="巡检成功率" value={inspectionRuns?.success_rate || 0} suffix="%" hint={`${inspectionRuns?.completed || 0}/${inspectionRuns?.total_runs || 0} 次运行`} tone="green" />
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <section className="ops-data-panel overflow-hidden">
            <div className="ops-data-toolbar m-3 mb-0 px-4 py-3">
              <h2 className="text-base font-bold text-ops-text">资产与协议分布</h2>
              <p className="mt-1 text-xs text-ops-subtext">用于判断当前平台是否覆盖数据中心关键对象。</p>
            </div>
            <div className="grid gap-4 p-5 lg:grid-cols-2">
              <BarList title="资产分类" data={overview?.by_category || {}} formatLabel={categoryLabel} />
              <BarList title="登录协议" data={overview?.by_protocol || {}} formatLabel={protocolLabel} />
            </div>
          </section>

          <section className="ops-data-panel overflow-hidden">
            <div className="ops-data-toolbar m-3 mb-0 px-4 py-3">
              <h2 className="text-base font-bold text-ops-text">会话与工具覆盖</h2>
              <p className="mt-1 text-xs text-ops-subtext">确认 AI 是否知道当前资产对应的协议工具。</p>
            </div>
            <div className="space-y-4 p-5">
              <BarList title="在线会话协议" data={overview?.active_by_protocol || {}} empty="暂无在线会话" formatLabel={protocolLabel} />
              <div className="ops-data-panel p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-ops-text">工具集</span>
                  <span className="font-mono text-xs text-ops-accent">{enabledToolsets.length} 组 / {enabledTools.length} 个工具</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {enabledToolsets.slice(0, 8).map((set) => (
                    <span key={set.id} className="ops-control px-2.5 py-1 text-[11px] text-ops-subtext">
                      {toolsetLabel(set.id)}
                    </span>
                  ))}
                  {enabledToolsets.length === 0 && <span className="text-xs text-ops-overlay">暂无工具集数据</span>}
                </div>
              </div>
            </div>
          </section>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-3">
          <section className="ops-data-panel p-5 xl:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <div>
              <h2 className="text-base font-bold text-ops-text">数据中心告警趋势</h2>
              <p className="mt-1 text-xs text-ops-subtext">来自原趋势大屏的核心视角，按日期聚合展示告警波动。</p>
              </div>
              <span className="ops-control px-3 py-1 text-xs text-ops-subtext">{trend.length} 天</span>
            </div>
            <TrendStrip points={trend} />
          </section>

          <section className="ops-data-panel p-5">
            <h2 className="text-base font-bold text-ops-text">风险主机排行</h2>
            <div className="mt-4 space-y-3">
              {ranking.slice(0, 8).map((item, index) => (
                <div key={item.host} className="flex items-center gap-3 rounded-lg border border-ops-surface0/80 bg-ops-surface0/35 px-3 py-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ops-accent/15 font-mono text-xs text-ops-accent">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-ops-text">{item.host}</div>
                    <div className="text-[11px] text-ops-overlay">{item.count} 条告警</div>
                  </div>
                  <span className="font-mono text-sm text-ops-alert">{item.score}</span>
                </div>
              ))}
              {ranking.length === 0 && <div className="py-8 text-center text-sm text-ops-subtext">暂无风险排行数据</div>}
            </div>
          </section>
        </div>

        <section className="ops-data-panel mt-5 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-ops-text">巡检运行健康度</h2>
              <p className="mt-1 text-xs text-ops-subtext">来自定时巡检运行记录，可直接用于后续大屏 SLA 指标。</p>
            </div>
            <span className="ops-control px-3 py-1 font-mono text-xs text-ops-accent">
              目标 {inspectionRuns?.targets_success || 0}/{inspectionRuns?.targets_total || 0}
            </span>
          </div>
          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="ops-data-panel p-4">
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
            <div className="ops-data-panel p-4">
              <div className="mb-3 text-sm font-semibold text-ops-text">最近失败/部分失败</div>
              <div className="space-y-2">
                {(inspectionRuns?.recent_failures || []).slice(0, 5).map((run) => (
                  <div key={run.id} className="flex flex-wrap items-center gap-2 rounded-lg bg-ops-surface0/60 px-3 py-2 text-xs">
                    <span className="rounded bg-ops-alert/15 px-2 py-0.5 text-ops-alert">{statusLabel(run.status)}</span>
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
            <div className="ops-data-panel p-4 lg:col-span-2">
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
