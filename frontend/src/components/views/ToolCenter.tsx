import { useEffect, useMemo, useState } from 'react'
import { getToolCenterCatalog } from '@/api/tools'
import PageHeader from '@/components/layout/PageHeader'
import type { ToolCenterCatalog, ToolCenterTool } from '@/types'

const STATUS_FILTERS = [
  ['all', '全部状态'],
  ['available', '当前可用'],
  ['controlled', '受控未启用'],
  ['not_wired', '未接入'],
] as const

const OPERATION_FILTERS = [
  ['all', '全部模式'],
  ['read', '只读'],
  ['read_write', '读写受控'],
  ['write', '写入'],
  ['destructive', '破坏性'],
  ['external_effect', '外发'],
  ['interactive', '人工交互'],
] as const

const APPROVAL_FILTERS = [
  ['all', '全部审批'],
  ['none', '无需审批'],
  ['guarded_write', '写入受控'],
  ['always_required', '强制审批'],
] as const

function protocolText(tool: ToolCenterTool) {
  const protocols = tool.protocols || []
  const assetTypes = tool.asset_types || []
  if (protocols.length === 0 && assetTypes.length === 0) return '通用'
  return [
    protocols.length > 0 ? `协议 ${protocols.slice(0, 4).join(', ')}` : '',
    assetTypes.length > 0 ? `资产 ${assetTypes.slice(0, 4).join(', ')}` : '',
  ].filter(Boolean).join(' / ')
}

function scopeText(scope: string) {
  return {
    asset: '资产会话',
    base: '通用能力',
    global: '全局编排',
    group: '批量范围',
  }[scope] || scope || '通用能力'
}

function operationText(mode?: string) {
  return {
    read: '只读',
    write: '写入',
    read_write: '读写受控',
    destructive: '破坏性',
    external_effect: '外发',
    interactive: '人工交互',
  }[mode || ''] || mode || '未知'
}

function approvalText(policy?: string) {
  return {
    none: '无需审批',
    guarded_write: '写入受控',
    always_required: '强制审批',
  }[policy || ''] || policy || '未知'
}

function evidenceText(family?: string) {
  return {
    database: '数据库',
    host_cli: '主机命令',
    http_api: 'HTTP/API',
    observability: '可观测',
    network: '网络',
    storage: '存储',
    virtualization: '虚拟化',
    container: '容器',
    knowledge: '知识库',
    notification: '通知',
    memory: '记忆',
    human_interaction: '人工输入',
    local_runtime: '本地运行时',
    platform: '平台',
  }[family || ''] || family || '未知'
}

function sourceText(source?: string) {
  return {
    opscore: '平台内置',
    builtin: '内置工具',
  }[source || ''] || source || '未知来源'
}

export default function ToolCenter() {
  const [catalog, setCatalog] = useState<ToolCenterCatalog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [operationFilter, setOperationFilter] = useState('all')
  const [approvalFilter, setApprovalFilter] = useState('all')

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
          const matchesKeyword = !keyword || [
            tool.name,
            tool.label,
            tool.description,
            tool.operation_mode,
            tool.approval_policy,
            tool.evidence_family,
          ].some((value) => String(value || '').toLowerCase().includes(keyword))
          const matchesStatus = statusFilter === 'all' || tool.status === statusFilter
          const matchesOperation = operationFilter === 'all' || tool.operation_mode === operationFilter
          const matchesApproval = approvalFilter === 'all' || tool.approval_policy === approvalFilter
          return matchesKeyword && matchesStatus && matchesOperation && matchesApproval
        })
        return { ...toolset, tools }
      })
      .filter((toolset) => toolset.tools.length > 0)
  }, [approvalFilter, catalog, operationFilter, query, statusFilter])

  const summary = catalog?.summary || {}

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="工具目录"
          title="工具中心"
          description="按运维场景查看当前可用工具。"
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

        <section className="ops-data-panel mb-4 p-3">
          <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_180px_180px_180px]">
            <label className="block">
              <span className="sr-only">搜索工具</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="ops-input h-10 w-full px-3 text-sm"
                placeholder="搜索工具名称、说明或策略"
              />
            </label>
            <FilterSelect
              label="状态"
              value={statusFilter}
              options={STATUS_FILTERS}
              onChange={setStatusFilter}
            />
            <FilterSelect
              label="模式"
              value={operationFilter}
              options={OPERATION_FILTERS}
              onChange={setOperationFilter}
            />
            <FilterSelect
              label="审批"
              value={approvalFilter}
              options={APPROVAL_FILTERS}
              onChange={setApprovalFilter}
            />
          </div>
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
                    <h2 className="mt-1 text-lg font-black text-ops-text">{toolset.label || toolset.id}</h2>
                  </div>
                  <CountPill label="工具" value={toolset.tools.length} />
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

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: readonly (readonly [string, string])[]
  onChange: (value: string) => void
}) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="ops-input h-10 w-full px-3 text-sm"
        aria-label={label}
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  )
}

function ToolRow({ tool }: { tool: ToolCenterTool }) {
  const operationTone = tool.destructive
    ? 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
    : tool.operation_mode === 'read'
      ? 'border-ops-accent/25 bg-ops-accent/10 text-ops-accent'
      : 'border-amber-300/30 bg-amber-300/10 text-amber-100'

  return (
    <article className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-start">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-black text-ops-text">{tool.label || tool.name}</h3>
          <code className="rounded border border-ops-surface1/65 bg-ops-dark/45 px-2 py-0.5 text-[11px] text-ops-overlay">
            {tool.name}
          </code>
          <span className={`rounded border px-2 py-0.5 text-[11px] font-bold ${operationTone}`}>
            {operationText(tool.operation_mode)}
          </span>
          <span className="rounded border border-ops-surface1/65 bg-ops-dark/35 px-2 py-0.5 text-[11px] font-bold text-ops-subtext">
            {tool.status_label || tool.status}
          </span>
          {tool.concurrency_safe && (
            <span className="rounded border border-ops-accent/25 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-bold text-ops-accent">
              可并发
            </span>
          )}
          {!tool.model_exposed && (
            <span className="rounded border border-ops-surface1/65 bg-ops-dark/35 px-2 py-0.5 text-[11px] font-bold text-ops-overlay">
              不暴露给模型
            </span>
          )}
        </div>
        <p className="mt-2 text-sm leading-6 text-ops-subtext">{tool.description || tool.control_reason || '暂无描述'}</p>
      </div>
      <div className="grid gap-2 text-xs text-ops-subtext">
        <InfoLine label="来源" value={sourceText(tool.source)} />
        <InfoLine label="范围" value={scopeText(tool.scope)} />
        <InfoLine label="审批" value={approvalText(tool.approval_policy)} />
        <InfoLine label="证据" value={evidenceText(tool.evidence_family)} />
        <InfoLine label="结果" value={tool.ui_renderer || '-'} />
        <InfoLine label="适配" value={protocolText(tool)} />
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
