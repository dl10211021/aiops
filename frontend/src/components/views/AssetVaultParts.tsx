import { useState } from 'react'

const CATEGORY_GROUP_ORDER = ['基础设施', '数据服务', '应用支撑', '平台工具', '其它']

export type FilterOption = {
  id: string
  label: string
  group?: string
  order?: number
  description?: string
}

export type AssetDisplayMeta = {
  typeLabel: string
  categoryLabel: string
  connectorLabel: string
  protocolLabel: string
}

function orderIndex(order: string[], id: string) {
  const idx = order.indexOf(id)
  return idx >= 0 ? idx : order.length
}

function groupFilterOptions(options: FilterOption[]) {
  const groups: Array<{ group: string; options: FilterOption[] }> = []
  options.forEach((option) => {
    const group = option.group || '其它'
    const existing = groups.find((item) => item.group === group)
    if (existing) {
      existing.options.push(option)
    } else {
      groups.push({ group, options: [option] })
    }
  })
  return groups.sort((a, b) => orderIndex(CATEGORY_GROUP_ORDER, a.group) - orderIndex(CATEGORY_GROUP_ORDER, b.group) || a.group.localeCompare(b.group))
}

export function AssetMetaLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-2">
      <span className="shrink-0 text-ops-overlay">{label}</span>
      <span className="min-w-0 truncate text-right text-ops-subtext" title={value}>{value}</span>
    </div>
  )
}

export function CategoryFilterRow({
  value,
  options,
  onChange,
}: {
  value: string
  options: FilterOption[]
  onChange: (value: string) => void
}) {
  const groups = groupFilterOptions(options)
  const [expanded, setExpanded] = useState(false)
  const compactOptions = options.slice(0, 6)
  const selectedOption = options.find((option) => option.id === value)
  const visibleCompactOptions = selectedOption && value !== 'all' && !compactOptions.some((option) => option.id === value)
    ? [selectedOption, ...compactOptions]
    : compactOptions
  return (
    <div className="mb-3 grid gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-16 shrink-0 text-xs text-ops-overlay">分类</span>
        <button
          onClick={() => onChange('all')}
          className={`shrink-0 rounded-lg px-2.5 py-1 text-[11px] transition-colors ${value === 'all' ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
        >
          全部
        </button>
        <div className="flex min-w-0 flex-1 flex-wrap gap-1.5">
          {!expanded && visibleCompactOptions.length > 0 && (
            <span className="flex shrink-0 items-center rounded-lg border border-ops-surface1/70 px-2 py-1 text-[10px] text-ops-overlay">
              常用
            </span>
          )}
          {!expanded && visibleCompactOptions.map((option) => (
            <button
              key={option.id}
              onClick={() => onChange(option.id)}
              title={option.description || option.label}
              className={`shrink-0 rounded-lg px-2.5 py-1 text-[11px] transition-colors ${value === option.id ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {options.length > compactOptions.length && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-16 shrink-0 rounded-lg bg-ops-dark px-2.5 py-1 text-[11px] text-ops-overlay hover:text-ops-text md:ml-0"
          >
            {expanded ? '收起分类' : `更多分类 ${options.length}`}
          </button>
        )}
      </div>
      {expanded && (
        <div className="ml-16 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {groups.map((group) => (
            <div key={group.group} className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-2">
              <div className="mb-1.5 flex items-center justify-between gap-2 text-[10px] font-semibold text-ops-overlay">
                <span>{group.group}</span>
                <span>{group.options.length} 类</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {group.options.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => onChange(option.id)}
                    title={option.description || option.label}
                    className={`rounded-lg px-2.5 py-1 text-[11px] transition-colors ${value === option.id ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function OverviewCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="ops-glass rounded-lg border p-4">
      <div className="text-xs font-medium text-ops-overlay">{label}</div>
      <div className="mt-2 font-mono text-2xl font-semibold text-ops-text">{value}</div>
    </div>
  )
}

export function FilterRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: Array<{ id: string; label: string }>
  onChange: (value: string) => void
}) {
  const useSelect = options.length > 18
  const [optionSearch, setOptionSearch] = useState('')
  const query = optionSearch.trim().toLowerCase()
  const matchedOptions = query
    ? options.filter((option) => option.id.toLowerCase().includes(query) || option.label.toLowerCase().includes(query))
    : options
  const selectedOption = options.find((option) => option.id === value)
  const visibleOptions = selectedOption && value !== 'all' && !matchedOptions.some((option) => option.id === value)
    ? [selectedOption, ...matchedOptions]
    : matchedOptions

  return (
    <div className="mb-2 flex items-start gap-2 last:mb-0">
      <span className="w-16 shrink-0 text-xs text-ops-overlay">{label}</span>
      {useSelect ? (
        <div className="grid min-w-0 flex-1 gap-2 md:grid-cols-[minmax(9rem,14rem)_1fr_auto]">
          <input
            value={optionSearch}
            onChange={(event) => setOptionSearch(event.target.value)}
            placeholder={`搜索${label}`}
            className="rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
          />
          <select
            value={value}
            onChange={(event) => onChange(event.target.value)}
            className="min-w-0 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
          >
            <option value="all">全部</option>
            {visibleOptions.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
            {visibleOptions.length === 0 && <option value="__empty" disabled>未找到匹配项</option>}
          </select>
          <span className="flex shrink-0 items-center text-[11px] text-ops-overlay">
            {query ? `${matchedOptions.length}/${options.length} 项` : `${options.length} 项`}
          </span>
        </div>
      ) : (
        <div className="flex min-w-0 flex-1 flex-wrap gap-2">
          <button
            onClick={() => onChange('all')}
            className={`rounded-lg px-2.5 py-1 text-[11px] transition-colors ${value === 'all' ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
          >
            全部
          </button>
          {options.map((option) => (
            <button
              key={option.id}
              onClick={() => onChange(option.id)}
              className={`rounded-lg px-2.5 py-1 text-[11px] transition-colors ${value === option.id ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
