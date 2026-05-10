import { useEffect, useMemo, useState } from 'react'
import { getToolCenterCatalog } from '@/api/tools'
import PageHeader from '@/components/layout/PageHeader'
import type { ToolCenterCatalog, ToolCenterStatus, ToolCenterTool } from '@/types'

const STATUS_FILTERS: Array<{ id: ToolCenterStatus | 'all'; label: string }> = [
  { id: 'all', label: '全部' },
  { id: 'available', label: '当前可用' },
  { id: 'controlled', label: '受控未启用' },
  { id: 'not_wired', label: '未接入' },
]

function statusTone(status: ToolCenterStatus) {
  if (status === 'available') return 'border-ops-accent/35 bg-ops-accent/12 text-ops-accent'
  if (status === 'controlled') return 'border-amber-300/35 bg-amber-400/10 text-amber-200'
  if (status === 'not_wired') return 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
  return 'border-ops-surface1 bg-ops-surface0/45 text-ops-subtext'
}

function protocolText(tool: ToolCenterTool) {
  const protocols = tool.protocols || []
  const assetTypes = tool.asset_types || []
  if (protocols.length === 0 && assetTypes.length === 0) return '通用'
  return [
    protocols.length > 0 ? `协议 ${protocols.slice(0, 4).join(', ')}` : '',
    assetTypes.length > 0 ? `资产 ${assetTypes.slice(0, 4).join(', ')}` : '',
  ].filter(Boolean).join(' / ')
}

export default function ToolCenter() {
  const [catalog, setCatalog] = useState<ToolCenterCatalog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<ToolCenterStatus | 'all'>('all')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getToolCenterCatalog()
      setCatalog(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '工具中心加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visibleToolsets = useMemo(() => {
    const keyword = query.trim().toLowerCase()
    return (catalog?.toolsets || [])
      .map((toolset) => {
        const tools = toolset.tools.filter((tool) => {
          const statusMatches = status === 'all' || tool.status === status
          if (!statusMatches) return false
          if (!keyword) return true
          return [
            tool.name,
            tool.label,
            tool.toolset,
            tool.description,
            tool.safety_category,
            tool.control_reason,
          ].some((value) => String(value || '').toLowerCase().includes(keyword))
        })
        return { ...toolset, tools }
      })
      .filter((toolset) => toolset.tools.length > 0)
  }, [catalog, query, status])

  const summary = catalog?.summary || {}

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="模型工具资产"
          title="工具中心"
          description="集中查看 OpsCore 当前暴露给模型的工具、受控未启用的高危工具，以及尚未接入会话执行链路的工具。"
          actions={(
            <button
              type="button"
              onClick={() => void load()}
              className="ops-control rounded-lg px-4 py-2 text-sm font-semibold"
            >
              刷新
            </button>
          )}
        />

        <section className="mb-4 grid gap-3 md:grid-cols-4">
          <Metric label="工具总数" value={summary.total || 0} />
          <Metric label="当前可用" value={summary.available || 0} tone="green" />
          <Metric label="受控未启用" value={summary.controlled || 0} tone="amber" />
          <Metric label="未接入" value={summary.not_wired || 0} tone="red" />
        </section>

        <section className="ops-data-panel mb-4 flex flex-col gap-3 p-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setStatus(item.id)}
                className={`rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${
                  status === item.id
                    ? 'border-ops-accent/55 bg-ops-accent/15 text-ops-accent'
                    : 'border-ops-surface1/65 bg-ops-dark/30 text-ops-subtext hover:text-ops-text'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <label className="min-w-0 lg:w-[320px]">
            <span className="sr-only">搜索工具</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="ops-input h-10 w-full px-3 text-sm"
              placeholder="搜索名称、说明、工具集或安全分类"
            />
          </label>
        </section>

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        {loading ? (
          <div className="ops-data-panel p-5 text-sm text-ops-subtext">正在读取工具目录...</div>
        ) : visibleToolsets.length > 0 ? (
          <div className="space-y-3">
            {visibleToolsets.map((toolset) => (
              <section key={toolset.id} className="ops-card overflow-hidden">
                <div className="ops-card-header flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="text-[11px] font-black uppercase tracking-[0.2em] text-ops-overlay">{toolset.id}</div>
                    <h2 className="mt-1 text-lg font-black text-ops-text">{toolset.label || toolset.id}</h2>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <CountPill label="可用" value={toolset.counts.available || 0} />
                    <CountPill label="受控" value={toolset.counts.controlled || 0} />
                    <CountPill label="未接入" value={toolset.counts.not_wired || 0} />
                  </div>
                </div>
                <div className="divide-y divide-ops-surface0/80">
                  {toolset.tools.map((tool) => (
                    <ToolRow key={tool.name} tool={tool} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="ops-data-panel p-5 text-sm text-ops-subtext">没有匹配的工具。</div>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value, tone = 'slate' }: { label: string; value: number; tone?: 'green' | 'amber' | 'red' | 'slate' }) {
  const toneClass = {
    green: 'text-ops-accent',
    amber: 'text-amber-200',
    red: 'text-ops-alert',
    slate: 'text-ops-text',
  }[tone]
  return (
    <div className="ops-data-panel p-4">
      <div className="text-xs font-bold text-ops-subtext">{label}</div>
      <div className={`mt-2 text-2xl font-black ${toneClass}`}>{value}</div>
    </div>
  )
}

function CountPill({ label, value }: { label: string; value: number }) {
  return (
    <span className="rounded-full border border-ops-surface1/65 bg-ops-dark/35 px-2.5 py-1 font-bold text-ops-subtext">
      {label} {value}
    </span>
  )
}

function ToolRow({ tool }: { tool: ToolCenterTool }) {
  return (
    <article className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(220px,0.8fr)_160px] lg:items-start">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-black text-ops-text">{tool.label || tool.name}</h3>
          <code className="rounded border border-ops-surface1/65 bg-ops-dark/45 px-2 py-0.5 text-[11px] text-ops-overlay">
            {tool.name}
          </code>
        </div>
        <p className="mt-2 text-sm leading-6 text-ops-subtext">{tool.description || tool.control_reason || '暂无描述'}</p>
        {tool.control_reason && (
          <p className="mt-2 rounded-lg border border-amber-300/25 bg-amber-400/8 px-3 py-2 text-xs leading-5 text-amber-100">
            {tool.control_reason}
          </p>
        )}
      </div>
      <div className="grid gap-2 text-xs text-ops-subtext sm:grid-cols-2 lg:grid-cols-1">
        <InfoLine label="范围" value={tool.scope} />
        <InfoLine label="安全分类" value={tool.safety_category} />
        <InfoLine label="适配" value={protocolText(tool)} />
      </div>
      <div className="flex flex-wrap gap-2 lg:justify-end">
        <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${statusTone(tool.status)}`}>
          {tool.status_label}
        </span>
        <span className="rounded-full border border-ops-surface1/65 bg-ops-dark/35 px-2.5 py-1 text-xs font-bold text-ops-subtext">
          {tool.model_exposed ? '模型可见' : '模型隐藏'}
        </span>
      </div>
    </article>
  )
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-ops-surface1/55 bg-ops-dark/25 px-3 py-2">
      <div className="text-[10px] font-black uppercase tracking-[0.16em] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate font-semibold text-ops-subtext" title={value}>{value || '-'}</div>
    </div>
  )
}
