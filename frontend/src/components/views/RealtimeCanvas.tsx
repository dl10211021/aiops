import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { apiUrl } from '@/api/http'
import PageHeader from '@/components/layout/PageHeader'
import {
  deleteRealtimeCanvas,
  extendRealtimeCanvas,
  getRealtimeCanvas,
  getRealtimeCanvasOptions,
  listRealtimeCanvases,
  startRealtimeCanvas,
  stopRealtimeCanvas,
  updateRealtimeCanvas,
} from '@/api/client'
import { useStore } from '@/store'
import type { RealtimeCanvasItem, RealtimeMetricPoint } from '@/types'

type CanvasType = 'static' | 'dynamic'

const defaultStaticGoal = '把当前会话只读巡检结果整理成中文 HTML 报告。'
const defaultDynamicGoal = '生成当前资产的实时动态画板。'
const hiddenMetrics = ['cpu', 'memory', 'disk', 'load', 'top_process', 'network', 'ports', 'disk_io', 'service_status', 'db_connections', 'db_sessions', 'db_latency', 'db_qps', 'db_cache_hit']

function formatDate(value?: string) {
  if (!value) return '--'
  return value.replace('T', ' ').slice(0, 19)
}

function statusLabel(status: string) {
  if (status === 'generating') return 'AI生成中'
  if (status === 'running') return '运行中'
  if (status === 'paused') return '人工暂停'
  if (status === 'expired') return '到期暂停'
  if (status === 'replaced') return '新画板替换'
  if (status === 'stopped') return '已停止'
  if (status === 'error') return '生成失败'
  return status || '未知'
}

function statusClass(status: string) {
  if (status === 'generating') return 'border-ops-accent/45 bg-ops-accent/10 text-ops-accent'
  if (status === 'running') return 'border-ops-success/45 bg-ops-success/10 text-ops-success'
  if (status === 'expired' || status === 'replaced') return 'border-ops-warning/45 bg-ops-warning/10 text-ops-warning'
  if (status === 'error') return 'border-ops-danger/45 bg-ops-danger/10 text-ops-danger'
  return 'border-ops-surface1 bg-ops-surface0 text-ops-subtext'
}

function canvasTypeFromItem(item?: RealtimeCanvasItem | null): CanvasType {
  return item?.mode === 'static' ? 'static' : 'dynamic'
}

function canvasTypeLabel(type: CanvasType) {
  return type === 'dynamic' ? '实时画布' : '静态 HTML'
}

function formatMetric(value: unknown, suffix = '') {
  const number = Number(value)
  if (!Number.isFinite(number)) return '--'
  return `${Math.round(number * 10) / 10}${suffix}`
}

function trendPath(points: Array<RealtimeMetricPoint & Record<string, unknown>>, field: string, width = 520, height = 140) {
  const values = points.map((point) => Number(point[field])).filter((value) => Number.isFinite(value))
  if (values.length < 2) return ''
  const max = Math.max(1, ...values)
  const min = Math.min(0, ...values)
  const span = Math.max(1, max - min)
  return values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width
    const y = height - ((value - min) / span) * height
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function trendArea(path: string, width = 520, height = 140) {
  if (!path) return ''
  return `${path} L${width},${height} L0,${height} Z`
}

function trendDots(points: Array<RealtimeMetricPoint & Record<string, unknown>>, field: string, width = 520, height = 140) {
  const values = points.map((point) => Number(point[field])).filter((value) => Number.isFinite(value))
  if (values.length < 2) return []
  const max = Math.max(1, ...values)
  const min = Math.min(0, ...values)
  const span = Math.max(1, max - min)
  return values.map((value, index) => ({
    x: (index / Math.max(1, values.length - 1)) * width,
    y: height - ((value - min) / span) * height,
    value,
  }))
}

function seriesPath(samples: Array<Record<string, unknown>>, width = 260, height = 76) {
  const values = samples.map((point) => Number(point.value)).filter((value) => Number.isFinite(value))
  if (values.length < 2) return ''
  const max = Math.max(1, ...values)
  const min = Math.min(0, ...values)
  const span = Math.max(1, max - min)
  return values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width
    const y = height - ((value - min) / span) * height
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function seriesScale(samples: Array<Record<string, unknown>>) {
  const values = samples.map((point) => Number(point.value)).filter((value) => Number.isFinite(value))
  if (!values.length) return { min: 0, max: 1, span: 1 }
  const min = Math.min(0, ...values)
  const max = Math.max(1, ...values)
  return { min, max, span: Math.max(1, max - min) }
}

function seriesY(value: number, scale: { min: number; max: number; span: number }, height = 76) {
  return height - ((value - scale.min) / scale.span) * height
}

function shortTime(value: unknown) {
  const text = String(value || '')
  return text ? (text.slice(11, 19) || text.slice(0, 16)) : '--'
}

function seriesArea(path: string, width = 260, height = 76) {
  return path ? `${path} L${width},${height} L0,${height} Z` : ''
}

function canvasVisualTheme(item: RealtimeCanvasItem, isDatabaseCanvas: boolean) {
  const spec = (item.canvas_spec || {}) as Record<string, unknown>
  const goal = String(spec.goal || item.title || '').toLowerCase()
  const rawTheme = String(spec.theme || spec.visual_theme || spec.canvas_theme || '').toLowerCase()
  const assetKind = String(item.session?.asset_type || item.session?.protocol || '').toLowerCase()
  if (isDatabaseCanvas || /oracle|mysql|postgres|sql|database|db|数据库/.test(`${rawTheme} ${goal} ${assetKind}`)) {
    return {
      name: '数据库星环',
      root: 'bg-[radial-gradient(circle_at_18%_14%,rgba(251,191,36,.22),transparent_28%),radial-gradient(circle_at_86%_24%,rgba(244,63,94,.18),transparent_30%),linear-gradient(135deg,#130b05,#06111f_48%,#020617)]',
      accent: '#fbbf24',
      accent2: '#fb7185',
      border: 'rgba(251,191,36,.28)',
      soft: 'rgba(251,191,36,.1)',
    }
  }
  if (/network|topology|switch|router|firewall|拓扑|网络|链路|交换机|路由/.test(`${rawTheme} ${goal} ${assetKind}`)) {
    return {
      name: '网络霓虹拓扑',
      root: 'bg-[radial-gradient(circle_at_12%_20%,rgba(14,165,233,.24),transparent_30%),radial-gradient(circle_at_82%_16%,rgba(34,197,94,.18),transparent_28%),linear-gradient(135deg,#02131f,#030712_52%,#00140d)]',
      accent: '#38bdf8',
      accent2: '#22c55e',
      border: 'rgba(56,189,248,.3)',
      soft: 'rgba(56,189,248,.1)',
    }
  }
  if (/incident|fault|error|risk|故障|风险|告警|异常/.test(`${rawTheme} ${goal}`)) {
    return {
      name: '故障红队态势',
      root: 'bg-[radial-gradient(circle_at_18%_14%,rgba(239,68,68,.25),transparent_30%),radial-gradient(circle_at_78%_22%,rgba(245,158,11,.16),transparent_28%),linear-gradient(135deg,#16070a,#07111f_54%,#020617)]',
      accent: '#fb7185',
      accent2: '#f59e0b',
      border: 'rgba(251,113,133,.3)',
      soft: 'rgba(251,113,133,.1)',
    }
  }
  return {
    name: '赛博指挥中心',
    root: 'bg-[radial-gradient(circle_at_18%_10%,rgba(45,212,191,.2),transparent_30%),radial-gradient(circle_at_86%_20%,rgba(59,130,246,.18),transparent_28%),linear-gradient(135deg,#07111f,#020712)]',
    accent: '#2dd4bf',
    accent2: '#6ea8ff',
    border: 'rgba(45,212,191,.28)',
    soft: 'rgba(45,212,191,.1)',
  }
}

function DynamicCanvasPanel({ item }: { item: RealtimeCanvasItem }) {
  const points = (item.points || []) as Array<RealtimeMetricPoint & Record<string, unknown>>
  const latest = ((item.latest || points[points.length - 1] || {}) as RealtimeMetricPoint & Record<string, unknown>)
  const tables = Array.isArray(latest.tables) ? latest.tables as Array<Record<string, unknown>> : []
  const metricSeries = Array.isArray((item as unknown as Record<string, unknown>).metric_series)
    ? (item as unknown as { metric_series: Array<Record<string, unknown>> }).metric_series
    : []
  const evidence = Array.isArray(latest.evidence) ? latest.evidence as Array<Record<string, unknown>> : []
  const topProcess = Array.isArray(latest.top_process) ? latest.top_process : []
  const ports = Array.isArray(latest.ports) ? latest.ports as Array<Record<string, unknown>> : []
  const network = Array.isArray(latest.network) ? latest.network as Array<Record<string, unknown>> : []
  const services = Array.isArray(latest.service_status) ? latest.service_status as Array<Record<string, unknown>> : []
  const assetKind = String(item.session?.asset_type || item.session?.protocol || '').toLowerCase()
  const isDatabaseCanvas = ['oracle', 'mysql', 'postgresql', 'pg', 'mssql', 'sqlserver', 'mariadb', 'db2', 'clickhouse', 'hive', 'iotdb'].includes(assetKind)
  const visual = canvasVisualTheme(item, isDatabaseCanvas)
  const visualStyle = {
    '--canvas-accent': visual.accent,
    '--canvas-accent-2': visual.accent2,
    '--canvas-border': visual.border,
    '--canvas-soft': visual.soft,
  } as CSSProperties
  const tableRowCount = (table: Record<string, unknown> | undefined) => Array.isArray(table?.rows) ? table.rows.length : 0
  const sessionTable = tables.find((table) => /会话|session|线程|thread/i.test(String(table.name || '')))
  const lockTable = tables.find((table) => /锁|lock|wait|等待/i.test(String(table.name || '')))
  const instanceTable = tables.find((table) => /实例|instance|状态|status/i.test(String(table.name || '')))
  const primaryCards = isDatabaseCanvas
    ? [
        ['数据库类型', String(item.session?.asset_type || item.session?.protocol || '--').toUpperCase()],
        ['SQL 监控项', String(tables.length)],
        ['会话/连接采样', String(tableRowCount(sessionTable))],
        ['等待/锁采样', String(tableRowCount(lockTable))],
      ]
    : [
        ['CPU', formatMetric(latest.cpu, '%')],
        ['内存', formatMetric(latest.memory, '%')],
        ['磁盘/容量', formatMetric(latest.disk, '%')],
        ['负载/状态', latest.load !== undefined ? formatMetric(latest.load) : String(latest.status || '--')],
      ]
  const cpuPath = trendPath(points, 'cpu')
  const memoryPath = trendPath(points, 'memory')
  const cpuDots = trendDots(points, 'cpu')
  const memoryDots = trendDots(points, 'memory')
  const firstTime = points[0]?.time || '--'
  const lastTime = latest.time || points[points.length - 1]?.time || '--'

  if (item.status === 'generating' || points.length === 0) {
    return (
      <div style={visualStyle} className={`relative flex min-h-[620px] items-center justify-center overflow-hidden rounded-3xl border p-8 text-center ${visual.root}`} >
        <div className="pointer-events-none absolute inset-0 opacity-[0.08] [background-image:linear-gradient(rgba(45,212,191,.8)_1px,transparent_1px),linear-gradient(90deg,rgba(45,212,191,.8)_1px,transparent_1px)] [background-size:38px_38px]" />
        <div className="relative max-w-2xl">
          <div className="mx-auto mb-5 h-16 w-16 rounded-2xl border bg-[var(--canvas-soft)] shadow-[0_0_46px_var(--canvas-soft)]" />
          <div className="text-xs font-black uppercase tracking-[0.28em] text-[var(--canvas-accent)]">{visual.name}</div>
          <h3 className="mt-3 text-2xl font-black text-ops-text">正在识别资产和可采集指标</h3>
          <p className="mt-3 text-sm leading-7 text-ops-subtext">
            动态画板不会直接生成空模板。AI 会先根据当前资产、协议和你的目标规划只读采集项，
            OpsCore 再执行首轮真实采样。采到数据后，这里才会切换成实时画板并展示趋势。
          </p>
          <div className="mt-5 grid gap-3 text-left text-sm md:grid-cols-3">
            <div className="rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3">
              <div className="font-bold text-ops-text">1. 资产识别</div>
              <div className="mt-1 text-xs text-ops-subtext">{item.session?.host || item.session_id} · {item.session?.asset_type || item.session?.protocol || '--'}</div>
            </div>
            <div className="rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3">
              <div className="font-bold text-ops-text">2. 采集规划</div>
              <div className="mt-1 text-xs text-ops-subtext">只读命令 / SQL / 网络 CLI</div>
            </div>
            <div className="rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3">
              <div className="font-bold text-ops-text">3. 首轮采样</div>
              <div className="mt-1 text-xs text-ops-subtext">拿到真实 points 后生成趋势视图</div>
            </div>
          </div>
          {item.last_error && (
            <div className="mt-4 rounded-xl border border-ops-warning/40 bg-ops-warning/10 p-3 text-sm text-ops-warning">
              {item.last_error}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div style={visualStyle} className={`relative min-h-[620px] overflow-hidden rounded-3xl border p-5 shadow-[0_26px_90px_rgba(0,0,0,.42)] ${visual.root}`}>
      <div className="pointer-events-none absolute inset-0 opacity-[0.08] [background-image:linear-gradient(rgba(45,212,191,.8)_1px,transparent_1px),linear-gradient(90deg,rgba(45,212,191,.8)_1px,transparent_1px)] [background-size:38px_38px]" />
      <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-ops-accent/10 blur-3xl" />
      <div className="relative">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-black uppercase tracking-[0.26em] text-[var(--canvas-accent)]">OpsCore · {visual.name}</div>
          <h3 className="mt-2 text-2xl font-black text-ops-text">{item.title}</h3>
          <p className="mt-1 text-sm text-ops-subtext">
            数据来自 OpsCore 当前会话采样，不依赖 AI 生成 HTML。采样点：{points.length} · 时间窗口：{firstTime} 至 {lastTime}
          </p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-bold ${statusClass(item.status)}`}>{statusLabel(item.status)}</span>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {primaryCards.map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-[var(--canvas-border)] bg-[#06111f]/75 p-4 shadow-[inset_0_0_34px_var(--canvas-soft),0_18px_50px_rgba(0,0,0,.22)]">
            <div className="text-xs text-ops-subtext">{label}</div>
            <div className="mt-2 font-mono text-4xl font-black text-[var(--canvas-accent)] drop-shadow-[0_0_14px_var(--canvas-soft)]">{value}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,.7fr)]">
        <section className="rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4 shadow-[inset_0_0_34px_rgba(45,212,191,.04)]">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="font-black text-ops-text">{isDatabaseCanvas ? '数据库采样时间线' : '趋势曲线'}</h4>
            <span className="text-xs text-ops-subtext">{isDatabaseCanvas ? 'SQL 只读监控 · 按采样时间排序' : 'CPU / 内存 · 按采样时间排序'}</span>
          </div>
          {isDatabaseCanvas ? (
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl bg-ops-surface0 p-4">
                <div className="text-xs text-ops-subtext">实例/状态采样</div>
                <div className="mt-2 text-2xl font-black text-ops-accent">{tableRowCount(instanceTable)}</div>
              </div>
              <div className="rounded-xl bg-ops-surface0 p-4">
                <div className="text-xs text-ops-subtext">会话/连接行数</div>
                <div className="mt-2 text-2xl font-black text-ops-accent">{tableRowCount(sessionTable)}</div>
              </div>
              <div className="rounded-xl bg-ops-surface0 p-4">
                <div className="text-xs text-ops-subtext">等待/锁行数</div>
                <div className="mt-2 text-2xl font-black text-ops-warning">{tableRowCount(lockTable)}</div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl bg-[#06111f] p-3">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ops-subtext">
                <span>Y 轴：使用率百分比 / 负载归一化</span>
                <span>X 轴：采样时间，左旧右新</span>
                <span className="inline-flex items-center gap-3">
                  <i className="h-2 w-5 rounded-full bg-[var(--canvas-accent)]" />
                  CPU
                  <i className="h-2 w-5 rounded-full bg-[#f7b955]" />
                  内存
                </span>
              </div>
              <svg viewBox="0 0 520 170" className="h-56 w-full overflow-visible">
              <defs>
                <linearGradient id="cpuLine" x1="0" x2="1">
                  <stop offset="0%" stopColor="var(--canvas-accent)" />
                  <stop offset="100%" stopColor="var(--canvas-accent-2)" />
                </linearGradient>
                <linearGradient id="cpuArea" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="var(--canvas-accent)" stopOpacity=".32" />
                  <stop offset="100%" stopColor="var(--canvas-accent)" stopOpacity="0" />
                </linearGradient>
                <filter id="chartGlow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>
              {[0, 35, 70, 105, 140].map((y) => <line key={y} x1="0" x2="520" y1={y} y2={y} stroke="rgba(148,163,184,.13)" />)}
              {[0, 130, 260, 390, 520].map((x) => <line key={x} x1={x} x2={x} y1="0" y2="140" stroke="rgba(148,163,184,.07)" />)}
              {[100, 75, 50, 25, 0].map((label, index) => (
                <text key={label} x="0" y={8 + index * 35} fill="#8ba4c7" fontSize="10">{label}%</text>
              ))}
              <text x="0" y="164" fill="#8ba4c7" fontSize="10">{shortTime(firstTime)}</text>
              <text x="260" y="164" fill="#8ba4c7" fontSize="10" textAnchor="middle">采样时间</text>
              <text x="520" y="164" fill="#8ba4c7" fontSize="10" textAnchor="end">{shortTime(lastTime)}</text>
              {cpuPath && <path d={trendArea(cpuPath)} fill="url(#cpuArea)" opacity=".9" />}
              {cpuPath && <path d={cpuPath} fill="none" stroke="url(#cpuLine)" strokeWidth="4" strokeLinecap="round" filter="url(#chartGlow)" />}
              {memoryPath && <path d={memoryPath} fill="none" stroke="#f7b955" strokeWidth="3" strokeLinecap="round" opacity=".9" />}
              {cpuDots.slice(-12).map((dot, index) => <circle key={`cpu-${index}`} cx={dot.x} cy={dot.y} r={index === cpuDots.slice(-12).length - 1 ? 4.8 : 2.8} fill="var(--canvas-accent)" opacity=".95" />)}
              {memoryDots.slice(-12).map((dot, index) => <circle key={`mem-${index}`} cx={dot.x} cy={dot.y} r="2.4" fill="#f7b955" opacity={index === memoryDots.slice(-12).length - 1 ? 1 : .65} />)}
              {!cpuPath && !memoryPath && <text x="260" y="74" textAnchor="middle" fill="#8ba4c7">等待至少两个真实采样点</text>}
              </svg>
            </div>
          )}
          <div className="mt-3 grid gap-2 text-xs text-ops-subtext md:grid-cols-3">
            <div className="rounded-lg bg-ops-surface0 px-3 py-2">起始：{firstTime}</div>
            <div className="rounded-lg bg-ops-surface0 px-3 py-2">最近：{lastTime}</div>
            <div className="rounded-lg bg-ops-surface0 px-3 py-2">间隔：{item.interval_seconds || '--'} 秒 · 保留 {points.length} 点</div>
          </div>
        </section>

        <section className="rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4">
          <h4 className="font-black text-ops-text">证据与状态</h4>
          <div className="mt-3 space-y-2 text-xs text-ops-subtext">
            <div className="rounded-xl bg-ops-surface0 p-3">状态：{latest.status || item.status}</div>
            {latest.error && <div className="rounded-xl border border-ops-danger/40 bg-ops-danger/10 p-3 text-ops-danger">{String(latest.error)}</div>}
            {evidence.slice(0, 3).map((entry, index) => (
              <div key={index} className="rounded-xl bg-ops-surface0 p-3">
                <div className="font-bold text-ops-text">{String(entry.source || '采集证据')}</div>
                <div className="mt-1 line-clamp-3">{String(entry.summary || '')}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {topProcess.length > 0 && (
        <section className="mt-4 rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4">
          <h4 className="font-black text-ops-text">Top 进程</h4>
          <div className="mt-3 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-ops-subtext"><tr><th className="py-2">PID</th><th>名称</th><th>CPU</th><th>内存</th></tr></thead>
              <tbody>
                {topProcess.map((proc, index) => (
                  <tr key={index} className="border-t border-ops-surface1 text-ops-text">
                    <td className="py-2 font-mono">{String(proc.pid ?? '')}</td>
                    <td>{String(proc.name ?? '')}</td>
                    <td>{formatMetric(proc.cpu, '%')}</td>
                    <td>{formatMetric(proc.memory, '%')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {metricSeries.length > 0 && (
        <section className="mt-4 rounded-2xl border border-[var(--canvas-border)] bg-[#06111f]/75 p-4">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div>
              <h4 className="font-black text-ops-text">指标趋势矩阵</h4>
              <p className="mt-1 text-xs text-ops-subtext">
                Grafana 式时间序列：当前值、最小、最大、平均、采样数、状态和时间窗口。
              </p>
            </div>
            <span className="rounded-full border border-[var(--canvas-border)] bg-[var(--canvas-soft)] px-3 py-1 text-xs font-bold text-[var(--canvas-accent)]">
              {metricSeries.length} 条指标序列
            </span>
          </div>
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {metricSeries.slice(0, 12).map((series, index) => {
              const samples = Array.isArray(series.points) ? series.points as Array<Record<string, unknown>> : []
              const path = seriesPath(samples)
              const area = seriesArea(path)
              const status = String(series.status || 'ok')
              const unit = String(series.unit || '')
              const first = samples[0]?.time ? String(samples[0].time) : '--'
              const last = samples[samples.length - 1]?.time ? String(samples[samples.length - 1].time) : '--'
              const scale = seriesScale(samples)
              const thresholds = (series.thresholds && typeof series.thresholds === 'object') ? series.thresholds as Record<string, unknown> : {}
              const warning = Number(thresholds.warning)
              const critical = Number(thresholds.critical)
              const warningY = Number.isFinite(warning) ? seriesY(warning, scale) : null
              const criticalY = Number.isFinite(critical) ? seriesY(critical, scale) : null
              return (
                <div key={String(series.key || index)} className="rounded-2xl border border-ops-surface1 bg-ops-bg/70 p-4 shadow-[inset_0_0_30px_rgba(255,255,255,.025)]">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-black text-ops-text">{String(series.label || series.key || `指标 ${index + 1}`)}</div>
                      <div className="mt-1 text-[11px] text-ops-subtext">{first} 至 {last}</div>
                    </div>
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${
                      status === 'critical'
                        ? 'border-ops-danger/45 bg-ops-danger/10 text-ops-danger'
                        : status === 'warning'
                          ? 'border-ops-warning/45 bg-ops-warning/10 text-ops-warning'
                          : 'border-ops-success/35 bg-ops-success/10 text-ops-success'
                    }`}>
                      {status === 'critical' ? '严重' : status === 'warning' ? '关注' : '正常'}
                    </span>
                  </div>
                  <div className="mt-3 flex items-end justify-between gap-3">
                    <div className="font-mono text-3xl font-black text-[var(--canvas-accent)]">
                      {formatMetric(series.current)}<span className="ml-1 text-base text-ops-subtext">{unit}</span>
                    </div>
                    <div className="text-right text-[11px] text-ops-subtext">
                      <div>样本 {String(series.samples || samples.length)}</div>
                      <div>源：{String(series.source || 'OpsCore')}</div>
                    </div>
                  </div>
                  <svg viewBox="0 0 300 112" className="mt-3 h-32 w-full rounded-xl bg-[#050c17] p-2">
                    <defs>
                      <linearGradient id={`seriesLine-${index}`} x1="0" x2="1">
                        <stop offset="0%" stopColor="var(--canvas-accent)" />
                        <stop offset="100%" stopColor="var(--canvas-accent-2)" />
                      </linearGradient>
                      <linearGradient id={`seriesArea-${index}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--canvas-accent)" stopOpacity=".28" />
                        <stop offset="100%" stopColor="var(--canvas-accent)" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <g transform="translate(32,10)">
                      {[0, 19, 38, 57, 76].map((y, yIndex) => (
                        <g key={y}>
                          <line x1="0" x2="260" y1={y} y2={y} stroke="rgba(148,163,184,.12)" />
                          <text x="-8" y={y + 3} textAnchor="end" fill="#8ba4c7" fontSize="9">
                            {formatMetric(scale.max - (scale.span * yIndex / 4))}
                          </text>
                        </g>
                      ))}
                      {[0, 65, 130, 195, 260].map((x) => <line key={x} x1={x} x2={x} y1="0" y2="76" stroke="rgba(148,163,184,.06)" />)}
                      {warningY !== null && warningY >= 0 && warningY <= 76 && (
                        <line x1="0" x2="260" y1={warningY} y2={warningY} stroke="#f7b955" strokeDasharray="5 5" opacity=".8" />
                      )}
                      {criticalY !== null && criticalY >= 0 && criticalY <= 76 && (
                        <line x1="0" x2="260" y1={criticalY} y2={criticalY} stroke="#ff5c8a" strokeDasharray="5 5" opacity=".85" />
                      )}
                      {area && <path d={area} fill={`url(#seriesArea-${index})`} />}
                      {path ? <path d={path} fill="none" stroke={`url(#seriesLine-${index})`} strokeWidth="3" strokeLinecap="round" /> : <text x="130" y="42" textAnchor="middle" fill="#8ba4c7">等待更多采样</text>}
                      <line x1="0" x2="260" y1="76" y2="76" stroke="rgba(148,163,184,.28)" />
                      <line x1="0" x2="0" y1="0" y2="76" stroke="rgba(148,163,184,.28)" />
                    </g>
                    <text x="32" y="104" fill="#8ba4c7" fontSize="10">{shortTime(first)}</text>
                    <text x="292" y="104" textAnchor="end" fill="#8ba4c7" fontSize="10">{shortTime(last)}</text>
                    <text x="292" y="10" textAnchor="end" fill="#8ba4c7" fontSize="10">{unit || 'value'}</text>
                    {(warningY !== null || criticalY !== null) && (
                      <text x="292" y="24" textAnchor="end" fill="#f7b955" fontSize="9">
                        {warningY !== null ? `W ${warning}${unit}` : ''}{criticalY !== null ? ` C ${critical}${unit}` : ''}
                      </text>
                    )}
                  </svg>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-ops-subtext">
                    <div className="rounded-lg bg-ops-surface0 px-2 py-1">最小 {formatMetric(series.min)}{unit}</div>
                    <div className="rounded-lg bg-ops-surface0 px-2 py-1">平均 {formatMetric(series.avg)}{unit}</div>
                    <div className="rounded-lg bg-ops-surface0 px-2 py-1">最大 {formatMetric(series.max)}{unit}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {(ports.length > 0 || network.length > 0 || services.length > 0 || Boolean(latest.disk_io)) && (
        <section className="mt-4 grid gap-4 xl:grid-cols-3">
          <div className="rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4">
            <h4 className="font-black text-ops-text">网络连接状态</h4>
            <div className="mt-3 space-y-2 text-sm">
              {network.length === 0 && <div className="text-ops-subtext">暂无网络状态数据</div>}
              {network.slice(0, 8).map((row, index) => (
                <div key={index} className="flex justify-between rounded-xl bg-ops-surface0 px-3 py-2">
                  <span className="text-ops-subtext">{String(row.name || '--')}</span>
                  <span className="font-mono text-ops-accent">{String(row.value || '--')}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4">
            <h4 className="font-black text-ops-text">监听端口</h4>
            <div className="mt-3 max-h-56 space-y-2 overflow-auto text-xs">
              {ports.length === 0 && <div className="text-ops-subtext">暂无端口数据</div>}
              {ports.slice(0, 12).map((row, index) => (
                <div key={index} className="rounded-xl bg-ops-surface0 px-3 py-2 text-ops-subtext">
                  <span className="font-mono text-ops-text">{String(row.name || '--')}</span>
                  <span className="mx-2 text-ops-accent">{String(row.value || '')}</span>
                  <span>{String(row.extra || '')}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4">
            <h4 className="font-black text-ops-text">磁盘 IO / 服务状态</h4>
            <div className="mt-3 rounded-xl bg-ops-surface0 px-3 py-2 font-mono text-sm text-ops-accent">{String(latest.disk_io || '暂无 IO 数据')}</div>
            <div className="mt-3 max-h-36 space-y-2 overflow-auto text-xs">
              {services.length === 0 && <div className="text-ops-subtext">暂无异常服务</div>}
              {services.map((row, index) => (
                <div key={index} className="rounded-xl bg-ops-surface0 px-3 py-2 text-ops-subtext">
                  <span className="text-ops-text">{String(row.name || '--')}</span>
                  <span className="ml-2 text-ops-warning">{String(row.value || '')}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {tables.length > 0 && (
        <section className="mt-4 grid gap-4 xl:grid-cols-2">
          {tables.map((table, index) => {
            const rows = Array.isArray(table.rows) ? table.rows as Array<Record<string, unknown>> : []
            const columns = rows[0] ? Object.keys(rows[0]).slice(0, 8) : []
            return (
              <div key={index} className="rounded-2xl border border-ops-accent/15 bg-[#06111f]/75 p-4">
                <h4 className="font-black text-ops-text">{String(table.name || `数据表 ${index + 1}`)}</h4>
                <div className="mt-3 max-h-72 overflow-auto">
                  {rows.length === 0 ? (
                    <div className="rounded-xl bg-ops-surface0 p-3 text-sm text-ops-subtext">{String(table.error || '暂无数据行')}</div>
                  ) : (
                    <table className="w-full text-left text-xs">
                      <thead className="text-ops-subtext"><tr>{columns.map((column) => <th key={column} className="whitespace-nowrap px-2 py-2">{column}</th>)}</tr></thead>
                      <tbody>{rows.slice(0, 30).map((row, rowIndex) => (
                        <tr key={rowIndex} className="border-t border-ops-surface1 text-ops-text">
                          {columns.map((column) => <td key={column} className="whitespace-nowrap px-2 py-2">{String(row[column] ?? '')}</td>)}
                        </tr>
                      ))}</tbody>
                    </table>
                  )}
                </div>
              </div>
            )
          })}
        </section>
      )}
      </div>
    </div>
  )
}

function buildAiPrompt(basePrompt: string, type: CanvasType, goal: string) {
  const modeText = type === 'dynamic'
    ? '动态画板：先识别资产类型和用户目标，再规划实时采集项。系统资产可以输出 scripts.linux/scripts.windows 一次性只读采集脚本；数据库输出 canvas_spec.monitor_queries；网络设备输出 canvas_spec.monitor_commands/topology_plan。OpsCore 负责执行、超时、暂停和回收。动态模式禁止生成 html/css/script/iframe。'
    : '静态 HTML：参考当前会话里的“只读巡检”指令和真实巡检结果，只把 inspection/checks/evidence 整理成中文 HTML 巡检报告。不要重新设计采集流程，不要伪造未采集数据。'
  return `${basePrompt}

本次用户目标：
${goal}

生成模式：
${modeText}

产品约束：
- 所有页面可见内容必须使用简体中文。技术字段名、命令、SQL、协议名可以保留原文，但报告标题、结论、建议、风险、模块名、空状态和错误提示都必须中文。
- 页面不要暴露复杂工程配置给用户，复杂采集策略由模型自己决定。
- 静态不是指标面板，静态要做分析报告；动态才主要做指标数据、曲线、刷新态和实时视图。
- 如果用户目标是巡检/故障/风险分析，优先生成静态分析报告，不要强行生成资源监控面板。
- 静态场景输出 html 字段，必须来自当前会话只读巡检内容；动态场景禁止输出 html，只输出 canvas_spec、widgets、monitor_queries、monitor_commands、thresholds、data_schema 等平台采集和渲染配置。

真实数据硬约束：
- 严禁伪造实时数据、随机指标、演示曲线、看起来真实但没有证据的拓扑。
- AI 可以写只读采集脚本，但不直接执行脚本；真实执行由 OpsCore 平台通过当前在线会话、已有工具和安全策略完成。
- scripts.linux/scripts.windows 必须是字符串，或者数组里每项包含 command 字段；不要把 JSON、Markdown、解释文字混进脚本字符串。
- Linux/Windows 脚本必须一次执行即退出，不常驻、不写文件、不修改系统状态。
- 系统指标脚本输出统一 key=value，例如 cpu=... memory=... disk=... load=... top_process=pid:name:cpu:mem; ports=proto:addr:proc; network=state:count; disk_io=... service_status=name:status;
- 动态场景不是 HTML 生成任务，不要生成 HTML、CSS、iframe、script。动态只规划平台实时画布配置和只读采集项。
- 如果用户要求监控某个 SQL 或数据库指标，AI 只生成 canvas_spec.monitor_queries 监控配置，不执行 SQL。每项包含 name、sql、chart、description，平台会校验只读并通过当前数据库会话执行。
- 动态默认要覆盖更完整的持续监控指标，并且必须带时间维度：采样时间、最近值、时间窗口、趋势、异常点。系统资产默认关注 CPU、内存、磁盘容量、负载、Top 进程、网络连接/端口、磁盘 IO、关键服务状态；数据库资产默认关注连接数、活跃会话、等待/锁、QPS/吞吐、缓存命中率、慢查询摘要。
- 静态场景必须把真实只读巡检结果转成分析文字：资产概况、检查项、发现问题、证据链、风险等级、原因分析、建议动作和复查项要清晰。
- 看板可以华丽：指挥中心大屏、赛博朋克拓扑、玻璃拟态卡片、风险热力、时间轴、流光链路、趋势曲线、异常脉冲、证据抽屉都可以用。
- 华丽效果必须绑定真实字段：每个数字、曲线、节点、边、状态灯和风险颜色都必须来自 latest、points、topology、events 或 evidence。
- 如果没有真实采样，HTML 必须显示“等待真实采样”或“采集失败”，不能展示假数据。
- 每个风险、结论、节点、链路都要带 evidence 来源，至少包含采集时间、工具/SQL/命令摘要和结果摘要。
- 输出必须是严格 JSON，不要 Markdown。`.trim()
}

export default function RealtimeCanvas() {
  const sessions = useStore((s) => s.sessions)
  const currentSessionId = useStore((s) => s.currentSessionId)
  const addToast = useStore((s) => s.addToast)
  const [items, setItems] = useState<RealtimeCanvasItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [defaultPrompt, setDefaultPrompt] = useState('')
  const [editId, setEditId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    session_id: currentSessionId || '',
    title: '',
    canvas_type: 'static' as CanvasType,
    goal: defaultStaticGoal,
  })

  const sessionsList = Object.values(sessions)
  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) || items[0] || null,
    [items, selectedId],
  )
  const selectedGoal = typeof selected?.canvas_spec?.goal === 'string' ? selected.canvas_spec.goal : ''
  const selectedType = canvasTypeFromItem(selected)

  const load = async () => {
    const res = await listRealtimeCanvases()
    const nextItems = res.data.items || []
    setItems(nextItems)
    if (!selectedId && nextItems[0]) setSelectedId(nextItems[0].id)
  }

  useEffect(() => {
    getRealtimeCanvasOptions()
      .then((res) => setDefaultPrompt(res.data.default_ai_prompt || ''))
      .catch(() => setDefaultPrompt(''))
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        if (!selectedId) {
          await load()
          return
        }
        const res = await getRealtimeCanvas(selectedId)
        setItems((current) => current.map((item) => item.id === selectedId ? res.data.item : item))
      } catch {
        await load()
      }
    }, 3000)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  useEffect(() => {
    if (currentSessionId && !form.session_id) {
      setForm((current) => ({ ...current, session_id: currentSessionId }))
    }
  }, [currentSessionId, form.session_id])

  const switchType = (canvasType: CanvasType) => {
    setForm((current) => ({
      ...current,
      canvas_type: canvasType,
      goal: current.goal === defaultStaticGoal || current.goal === defaultDynamicGoal
        ? (canvasType === 'dynamic' ? defaultDynamicGoal : defaultStaticGoal)
        : current.goal,
    }))
  }

  const handleGenerate = async () => {
    if (!form.session_id) {
      addToast('请先选择一个在线资产会话', 'error')
      return
    }
    if (!form.goal.trim()) {
      addToast('请先写一句你想让 AI 生成什么画板', 'error')
      return
    }
    setBusy(true)
    try {
      const session = sessions[form.session_id]
      const type = form.canvas_type
      const title = form.title.trim() || `${session?.host || '资产'} ${canvasTypeLabel(type)}`
      const prompt = buildAiPrompt(defaultPrompt, type, form.goal.trim())
      const payload = {
        session_id: form.session_id,
        title,
        kind: type === 'dynamic' ? 'metrics' : 'custom_html',
        mode: type === 'dynamic' ? 'realtime' : 'static',
        metrics: type === 'dynamic' ? hiddenMetrics : [],
        interval_seconds: type === 'dynamic' ? 10 : 60,
        duration_seconds: type === 'dynamic' ? 30 * 60 : 5 * 60,
        stop_existing: true,
        canvas_spec: {
          goal: form.goal.trim(),
          canvas_type: type,
          generation: type === 'dynamic' ? 'platform_realtime_canvas' : 'ai_static_html_report',
        },
        ai_prompt_template: prompt || undefined,
      }
      const res = editId
        ? await updateRealtimeCanvas(editId, payload)
        : await startRealtimeCanvas(payload)
      setSelectedId(res.data.item.id)
      await load()
      addToast(editId ? '画板已更新，AI 正在重新生成' : 'AI 已开始生成画板，请稍等刷新结果', 'success')
      if (editId) setEditId(null)
    } catch (error) {
      addToast(error instanceof Error ? error.message : '生成画板失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleEdit = (item: RealtimeCanvasItem) => {
    const type = canvasTypeFromItem(item)
    setEditId(item.id)
    setSelectedId(item.id)
    setForm({
      session_id: item.session_id,
      title: item.title || '',
      canvas_type: type,
      goal: typeof item.canvas_spec?.goal === 'string'
        ? item.canvas_spec.goal
        : (type === 'dynamic' ? defaultDynamicGoal : defaultStaticGoal),
    })
  }

  const resetForm = () => {
    setEditId(null)
    setForm((current) => ({
      ...current,
      title: '',
      canvas_type: 'static',
      goal: defaultStaticGoal,
    }))
  }

  const handleStop = async (id: string) => {
    setBusy(true)
    try {
      const res = await stopRealtimeCanvas(id)
      setItems((current) => current.map((item) => item.id === id ? res.data.item : item))
      addToast('画板已暂停', 'success')
    } catch (error) {
      addToast(error instanceof Error ? error.message : '暂停失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleRun = async (id: string) => {
    setBusy(true)
    try {
      const res = await extendRealtimeCanvas(id, 30 * 60)
      setItems((current) => current.map((item) => item.id === id ? res.data.item : item))
      addToast('画板已继续运行，采集窗口已延长 30 分钟', 'success')
    } catch (error) {
      addToast(error instanceof Error ? error.message : '继续运行失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (id: string) => {
    setBusy(true)
    try {
      await deleteRealtimeCanvas(id)
      setItems((current) => current.filter((item) => item.id !== id))
      if (selectedId === id) setSelectedId(null)
      if (editId === id) resetForm()
      addToast('画板已删除', 'success')
    } catch (error) {
      addToast(error instanceof Error ? error.message : '删除失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <PageHeader
        eyebrow="AI Canvas Studio"
        title="AI 画板"
          description="静态用于巡检、故障、风险等分析报告；动态用于指标数据、趋势曲线、实时状态和拓扑刷新。"
        actions={(
          <button onClick={() => void load()} className="ops-muted-action px-3 py-1.5 text-sm">
            刷新
          </button>
        )}
      />

      <section className="grid items-start gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <section className="ops-data-panel p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-black text-ops-text">{editId ? '编辑画板' : '生成画板'}</h2>
                <p className="text-xs text-ops-subtext">采集走平台已有会话和脚本，AI 只负责把真实数据变成画板。</p>
              </div>
              {editId && (
                <button onClick={resetForm} className="ops-muted-action px-2.5 py-1 text-xs">
                  取消
                </button>
              )}
            </div>

            <label className="text-xs font-bold text-ops-subtext">在线资产会话</label>
            <select
              value={form.session_id}
              onChange={(event) => setForm((current) => ({ ...current, session_id: event.target.value }))}
              className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="">选择一个会话资产</option>
              {sessionsList.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.host} · {session.protocol || session.asset_type}
                </option>
              ))}
            </select>

            <div className="ops-control mt-4 grid grid-cols-2 gap-2 p-1">
              {(['static', 'dynamic'] as CanvasType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => switchType(type)}
                  className={`rounded-lg px-3 py-2 text-sm font-bold transition ${
                    form.canvas_type === type
                      ? 'bg-ops-accent text-ops-bg shadow-[0_0_24px_rgba(45,212,191,.22)]'
                      : 'text-ops-subtext hover:bg-ops-surface2 hover:text-ops-text'
                  }`}
                >
                  {canvasTypeLabel(type)}
                </button>
              ))}
            </div>

            <label className="mt-4 block text-xs font-bold text-ops-subtext">你想让 AI 做什么</label>
            <textarea
              value={form.goal}
              onChange={(event) => setForm((current) => ({ ...current, goal: event.target.value }))}
              rows={7}
              className="ops-control mt-1 w-full resize-none px-3 py-2 text-sm leading-6 text-ops-text outline-none focus:border-ops-accent"
              placeholder="例如：帮我巡检这个 Oracle，生成数据库连接拓扑、慢查询风险和处理建议。"
            />

            <label className="mt-3 block text-xs font-bold text-ops-subtext">画板标题，可选</label>
            <input
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder="不填则自动命名"
            />

            <button
              onClick={() => void handleGenerate()}
              disabled={busy}
              className="ops-primary-action mt-4 w-full px-4 py-3 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? '处理中...' : editId ? '保存并继续打磨' : '让 AI 生成画板'}
            </button>
          </section>

          <section className="ops-data-panel p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-black text-ops-text">画板列表</h2>
              <span className="text-xs text-ops-subtext">{items.length} 个</span>
            </div>
            <div className="space-y-2">
              {items.length === 0 && (
                <div className="ops-data-panel border-dashed p-4 text-sm text-ops-subtext">
                  暂无画板。先输入一个巡检或故障目标，让 AI 生成第一张。
                </div>
              )}
              {items.map((item) => {
                const type = canvasTypeFromItem(item)
                return (
                  <button
                    key={item.id}
                    onClick={() => setSelectedId(item.id)}
                    className={`w-full rounded-xl border p-3 text-left transition ${
                      selected?.id === item.id
                        ? 'border-ops-accent bg-ops-accent/10'
                        : 'border-ops-surface1 bg-ops-surface2/60 hover:border-ops-accent/60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="line-clamp-1 text-sm font-black text-ops-text">{item.title}</span>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${statusClass(item.status)}`}>
                        {statusLabel(item.status)}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center gap-2 text-xs text-ops-subtext">
                      <span>{canvasTypeLabel(type)}</span>
                      <span>·</span>
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                  </button>
                )
              })}
            </div>
          </section>
        </div>

        <section className="ops-card min-h-[640px] overflow-hidden">
          {!selected ? (
            <div className="flex h-full min-h-[640px] items-center justify-center p-8 text-center text-ops-subtext">
              选择左侧画板后查看预览、导出和编辑。
            </div>
          ) : (
            <div className="flex h-full flex-col">
              <div className="border-b border-ops-surface1 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-[0.24em] text-ops-accent">{canvasTypeLabel(selectedType)}</div>
                    <h2 className="mt-1 text-2xl font-black text-ops-text">{selected.title}</h2>
                    <p className="mt-1 text-sm text-ops-subtext">
                      {selected.session?.host || selected.session_id} · {formatDate(selected.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <a
                      href={apiUrl(`/realtime-canvas/${selected.id}/export.html`)}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-lg border border-ops-accent/45 px-3 py-2 text-sm font-bold text-ops-accent hover:bg-ops-accent/10"
                    >
                      导出 HTML
                    </a>
                    <button onClick={() => handleEdit(selected)} className="rounded-lg border border-ops-surface1 px-3 py-2 text-sm font-bold text-ops-text hover:border-ops-accent">
                      编辑
                    </button>
                    {selected.status === 'running' && (
                      <button onClick={() => void handleStop(selected.id)} disabled={busy} className="rounded-lg border border-ops-warning/45 px-3 py-2 text-sm font-bold text-ops-warning hover:bg-ops-warning/10">
                        暂停
                      </button>
                    )}
                    {canvasTypeFromItem(selected) === 'dynamic' && ['paused', 'expired', 'stopped'].includes(selected.status) && (
                      <button onClick={() => void handleRun(selected.id)} disabled={busy} className="rounded-lg border border-ops-accent/45 px-3 py-2 text-sm font-bold text-ops-accent hover:bg-ops-accent/10">
                        继续运行
                      </button>
                    )}
                    <button onClick={() => void handleDelete(selected.id)} disabled={busy} className="rounded-lg border border-ops-danger/45 px-3 py-2 text-sm font-bold text-ops-danger hover:bg-ops-danger/10">
                      删除
                    </button>
                  </div>
                </div>
                {selectedGoal && (
                  <div className="mt-3 rounded-xl border border-ops-surface1 bg-ops-bg p-3 text-sm leading-6 text-ops-subtext">
                    <span className="font-bold text-ops-text">目标：</span>{selectedGoal}
                  </div>
                )}
              </div>

              <div className="min-h-0 flex-1 bg-[#04101d] p-4">
                {selectedType === 'dynamic' ? (
                  <DynamicCanvasPanel item={selected} />
                ) : selected.status === 'generating' ? (
                  <div className="flex h-[620px] items-center justify-center rounded-xl border border-dashed border-ops-surface1 bg-[radial-gradient(circle_at_20%_10%,rgba(45,212,191,.18),transparent_28%),linear-gradient(135deg,#07111f,#020712)] p-8 text-center">
                    <div className="max-w-2xl">
                      <div className="mx-auto mb-4 h-16 w-16 rounded-2xl border border-ops-accent/50 bg-ops-accent/10 shadow-[0_0_40px_rgba(45,212,191,.22)]" />
                      <div className="text-xs font-black uppercase tracking-[0.26em] text-ops-accent">AI Static Report Pipeline</div>
                      <h3 className="mt-3 text-xl font-black text-ops-text">AI 正在基于本次完整只读巡检生成 HTML 报告</h3>
                      <p className="mt-3 text-sm leading-7 text-ops-subtext">
                        当前不会展示临时兜底页。平台已完成或正在执行本次只读巡检，AI 会根据真实命令输出、证据链、异常项和风险等级生成最终 HTML 画板。
                      </p>
                      <div className="mt-5 grid gap-3 text-left text-sm md:grid-cols-3">
                        <div className="rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3">
                          <div className="font-bold text-ops-text">1. 只读巡检</div>
                          <div className="mt-1 text-xs text-ops-subtext">原生协议工具采集证据</div>
                        </div>
                        <div className="rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3">
                          <div className="font-bold text-ops-text">2. AI 分析</div>
                          <div className="mt-1 text-xs text-ops-subtext">健康、异常、风险、建议</div>
                        </div>
                        <div className="rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3">
                          <div className="font-bold text-ops-text">3. HTML 画板</div>
                          <div className="mt-1 text-xs text-ops-subtext">完成后展示最终报告</div>
                        </div>
                      </div>
                      {selected.stop_reason && <div className="mt-4 rounded-xl border border-ops-surface1 bg-ops-bg/70 p-3 text-sm text-ops-subtext">{selected.stop_reason}</div>}
                    </div>
                  </div>
                ) : selected.html ? (
                  <iframe
                    key={`${selected.id}-${selected.points?.length || 0}-${selected.generated_at || selected.last_collect_at || ''}`}
                    title={selected.title}
                    sandbox="allow-scripts"
                    srcDoc={selected.html}
                    className="h-[620px] w-full rounded-xl border border-ops-surface1 bg-white"
                  />
                ) : (
                  <div className="flex h-[620px] items-center justify-center rounded-xl border border-dashed border-ops-surface1 bg-[radial-gradient(circle_at_20%_10%,rgba(45,212,191,.18),transparent_28%),linear-gradient(135deg,#07111f,#020712)] p-8 text-center">
                    <div className="max-w-xl">
                      <div className="mx-auto mb-4 h-16 w-16 rounded-2xl border border-ops-accent/50 bg-ops-accent/10 shadow-[0_0_40px_rgba(45,212,191,.22)]" />
                      <h3 className="text-xl font-black text-ops-text">等待 AI 生成 HTML 画板</h3>
                      <p className="mt-2 text-sm leading-6 text-ops-subtext">
                        当前已保存生成目标和模式。静态会生成分析报告，动态会持续刷新真实指标采样点。
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </section>
    </div>
  )
}
