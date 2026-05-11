import type { Asset, ProtocolVerificationStatusOverview } from '@/types'
import { Fragment, useEffect, useMemo, useRef, useState, useTransition } from 'react'
import {
  DEFAULT_SESSION_GROUP,
  normalizeSessionGroupName,
  uniqueSessionGroups,
} from '@/features/sessions/sessionGroups'
import { AssetCard } from './AssetVaultCards'
import { OverviewCard, type AssetDisplayMeta } from './AssetVaultParts'
import { assetTypeKey } from './assetVaultModel'
import type { AssetVaultGroup } from './assetVaultViewModel'

const ASSET_TABLE_PAGE_SIZE = 50
const ASSET_GROUP_OVERVIEW_LIMIT = 24
type AssetTableGroupBy = 'assetGroup' | 'category' | 'type' | 'protocol' | 'none'
const ASSET_TABLE_GROUP_OPTIONS: Array<{ id: AssetTableGroupBy; label: string }> = [
  { id: 'assetGroup', label: '按资产组' },
  { id: 'category', label: '按分类' },
  { id: 'type', label: '按类型' },
  { id: 'protocol', label: '按主接入' },
  { id: 'none', label: '不分组' },
]
type AssetGroupSummary = {
  name: string
  count: number
  ready: number
  assets: Asset[]
}
type AssetVerificationStatusMatrix = ProtocolVerificationStatusOverview['matrix'][number]

export function AssetOverviewGrid({
  overview,
  verificationOverview,
}: {
  overview: Record<string, number> | null
  verificationOverview: ProtocolVerificationStatusOverview | null
}) {
  if (!overview) return null
  return (
    <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-5">
      <OverviewCard label="资产总数" value={overview.asset_total || 0} />
      <OverviewCard label="在线会话" value={overview.active_sessions || 0} />
      <OverviewCard label="资产分类" value={overview.asset_categories || 0} />
      <OverviewCard label="连接方式" value={overview.protocols || 0} />
      <OverviewCard label="验证就绪" value={verificationOverview?.summary.ready_assets || 0} />
    </div>
  )
}

export function AssetEnterpriseCommandPanel({
  assetCount,
  catalogTypeCount,
  filteredCount,
  readyCount,
}: {
  assetCount: number
  catalogTypeCount: number
  filteredCount: number
  readyCount: number
}) {
  const stats = [
    { label: '资产总数', value: assetCount, hint: '已纳管对象' },
    { label: '当前结果', value: filteredCount, hint: '筛选后数量' },
    { label: '验证就绪', value: readyCount, hint: '可进入会话' },
    { label: '类型目录', value: catalogTypeCount, hint: '可接入类型' },
  ]

  return (
    <section className="mb-3 ops-data-panel">
      <div className="flex flex-col gap-3 px-4 py-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-ops-accent/35 bg-ops-accent/10 px-2.5 py-1 text-[11px] font-semibold text-ops-accent">
              资产总览
            </span>
            <h2 className="text-base font-bold tracking-tight text-ops-text">数据中心资产统一入口</h2>
          </div>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-ops-subtext">
            查看规模、验证状态和筛选结果；资产维护在下方列表完成。
          </p>
        </div>

        <div className="grid min-w-0 grid-cols-2 gap-2 xl:min-w-[540px] xl:grid-cols-4">
          {stats.map((item) => (
            <div
              key={item.label}
              title={item.hint}
              className="flex min-h-9 items-center justify-between gap-3 rounded-lg border border-ops-surface1/80 bg-ops-dark/35 px-3 py-2"
            >
              <div className="min-w-0 truncate text-[11px] text-ops-overlay">{item.label}</div>
              <div className="shrink-0 font-mono text-lg font-bold leading-none text-ops-text">{item.value}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function AssetGroupSections({
  assetGroups,
  assetTypeLabels,
  categoryForAsset,
  categoryLabels,
  connectorForAsset,
  connectorLabels,
  matrixByAssetId,
  protocolLabelForAsset,
  onConnect,
  onEdit,
  onDelete,
  onOpenVerification,
}: {
  assetGroups: AssetVaultGroup[]
  assetTypeLabels: Record<string, string>
  categoryForAsset: (asset: Asset) => string
  categoryLabels: Record<string, string>
  connectorForAsset: (asset: Asset) => string
  connectorLabels: Record<string, string>
  matrixByAssetId: Map<number, AssetVerificationStatusMatrix>
  protocolLabelForAsset: (asset: Asset, connector: string) => string
  onConnect: (asset: Asset) => void
  onEdit: (asset: Asset) => void
  onDelete: (asset: Asset) => void
  onOpenVerification: (asset: Asset) => void
}) {
  return (
    <>
      {assetGroups.map((group) => (
        <div key={group.id} className="mb-5">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ops-subtext">{group.label} ({group.items.length})</h2>
            <span className="rounded bg-ops-surface0 px-1.5 py-0.5 text-[10px] text-ops-overlay">{group.group}</span>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-5">
            {group.items.map((asset) => {
              const category = categoryForAsset(asset)
              const connector = connectorForAsset(asset)
              return (
                <AssetCard
                  key={asset.id}
                  asset={asset}
                  categoryLabel={categoryLabels[category] || category.toUpperCase()}
                  connectorLabel={connectorLabels[connector] || connector}
                  matrix={matrixByAssetId.get(asset.id)}
                  protocolLabel={protocolLabelForAsset(asset, connector)}
                  typeLabel={assetTypeLabels[assetTypeKey(asset)] || asset.asset_type || '资产'}
                  onConnect={onConnect}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onOpenVerification={onOpenVerification}
                />
              )
            })}
          </div>
        </div>
      ))}
    </>
  )
}

export function AssetTablePanel({
  assets,
  bulkDeleting,
  bulkVerifying,
  connectingGroup,
  connectingSelected,
  displayForAsset,
  hasActiveFilters,
  matrixByAssetId,
  mutatingGroup,
  sessionGroups,
  onAssignGroup,
  onBulkDelete,
  onBulkVerify,
  onClearFilters,
  onConnect,
  onConnectGroup,
  onConnectSelected,
  onCreateGroup,
  onDeleteGroup,
  onEdit,
  onDelete,
  onOpenVerification,
  onRenameGroup,
  onRefresh,
  onSearchChange,
  search,
}: {
  assets: Asset[]
  bulkDeleting: boolean
  bulkVerifying: boolean
  connectingGroup: string | null
  connectingSelected: boolean
  displayForAsset: (asset: Asset) => AssetDisplayMeta
  hasActiveFilters: boolean
  matrixByAssetId: Map<number, AssetVerificationStatusMatrix>
  mutatingGroup: string | null
  sessionGroups: string[]
  onAssignGroup: (assets: Asset[], groupName: string) => void
  onBulkDelete: (assets: Asset[]) => void
  onBulkVerify: (assets: Asset[]) => void
  onClearFilters: () => void
  onConnect: (asset: Asset) => void
  onConnectGroup: (assets: Asset[], groupName: string) => void
  onConnectSelected: (assets: Asset[]) => void
  onCreateGroup: (groupName: string) => void
  onDeleteGroup: (groupName: string) => void
  onEdit: (asset: Asset) => void
  onDelete: (asset: Asset) => void
  onOpenVerification: (asset: Asset) => void
  onRenameGroup: (groupName: string, nextGroupName: string) => void
  onRefresh: () => void
  onSearchChange: (value: string) => void
  search: string
}) {
  const [page, setPage] = useState(1)
  const [groupBy, setGroupBy] = useState<AssetTableGroupBy>('assetGroup')
  const [assetGroupDraft, setAssetGroupDraft] = useState('')
  const [assignGroup, setAssignGroup] = useState(DEFAULT_SESSION_GROUP)
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => new Set())
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set())
  const [activeAssetGroup, setActiveAssetGroup] = useState<string | null>(null)
  const [showAllAssetGroups, setShowAllAssetGroups] = useState(false)
  const assetGroupSummaries = useMemo(() => {
    const groups = new Map<string, AssetGroupSummary>()
    assets.forEach((asset) => {
      const name = normalizeSessionGroupName(asset.tags?.[0]) || DEFAULT_SESSION_GROUP
      const current = groups.get(name) || { name, count: 0, ready: 0, assets: [] }
      current.count += 1
      current.assets.push(asset)
      if (matrixByAssetId.get(asset.id)?.status === 'ready') current.ready += 1
      groups.set(name, current)
    })
    return Array.from(groups.values()).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  }, [assets, matrixByAssetId])
  const visibleAssetGroupSummaries = useMemo(() => {
    if (showAllAssetGroups || assetGroupSummaries.length <= ASSET_GROUP_OVERVIEW_LIMIT) {
      return assetGroupSummaries
    }
    const visible = assetGroupSummaries.slice(0, ASSET_GROUP_OVERVIEW_LIMIT)
    if (activeAssetGroup && !visible.some((group) => group.name === activeAssetGroup)) {
      const activeGroup = assetGroupSummaries.find((group) => group.name === activeAssetGroup)
      if (activeGroup) return [...visible, activeGroup]
    }
    return visible
  }, [activeAssetGroup, assetGroupSummaries, showAllAssetGroups])
  const hiddenAssetGroupCount = Math.max(0, assetGroupSummaries.length - visibleAssetGroupSummaries.length)
  const panelAssets = useMemo(() => {
    if (!activeAssetGroup) return assets
    return assets.filter((asset) => (normalizeSessionGroupName(asset.tags?.[0]) || DEFAULT_SESSION_GROUP) === activeAssetGroup)
  }, [activeAssetGroup, assets])
  const pageCount = Math.max(1, Math.ceil(panelAssets.length / ASSET_TABLE_PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const pageStart = (currentPage - 1) * ASSET_TABLE_PAGE_SIZE
  const visibleAssets = useMemo(
    () => panelAssets.slice(pageStart, pageStart + ASSET_TABLE_PAGE_SIZE),
    [panelAssets, pageStart]
  )
  const displayMetaByAssetId = useMemo(() => {
    const rows = new Map<number, AssetDisplayMeta>()
    panelAssets.forEach((asset) => rows.set(asset.id, displayForAsset(asset)))
    return rows
  }, [displayForAsset, panelAssets])
  const displayMetaForAsset = (asset: Asset) => displayMetaByAssetId.get(asset.id) || displayForAsset(asset)
  const assetGroupOptions = useMemo(() => uniqueSessionGroups([
    ...sessionGroups,
    ...assets.flatMap((asset) => asset.tags || []),
  ]), [assets, sessionGroups])
  const groupCounts = useMemo(() => {
    const counts = new Map<string, number>()
    if (groupBy === 'none') return counts
    panelAssets.forEach((asset) => {
      const label = assetTableGroupLabel(asset, displayMetaForAsset(asset), groupBy)
      counts.set(label, (counts.get(label) || 0) + 1)
    })
    return counts
  }, [displayMetaByAssetId, groupBy, panelAssets])
  const groupAssetsByLabel = useMemo(() => {
    const grouped = new Map<string, Asset[]>()
    if (groupBy === 'none') return grouped
    panelAssets.forEach((asset) => {
      const label = assetTableGroupLabel(asset, displayMetaForAsset(asset), groupBy)
      const current = grouped.get(label)
      if (current) {
        current.push(asset)
      } else {
        grouped.set(label, [asset])
      }
    })
    return grouped
  }, [displayMetaByAssetId, groupBy, panelAssets])
  const groupedVisibleAssets = useMemo(() => {
    if (groupBy === 'none') {
      return [{ id: 'all', label: '全部资产', count: visibleAssets.length, allItems: visibleAssets, items: visibleAssets }]
    }
    const groups = new Map<string, { id: string; label: string; count: number; allItems: Asset[]; items: Asset[] }>()
    visibleAssets.forEach((asset) => {
      const label = assetTableGroupLabel(asset, displayMetaForAsset(asset), groupBy)
      const id = `${groupBy}:${label}`
      const current = groups.get(id)
      if (current) {
        current.items.push(asset)
      } else {
        groups.set(id, {
          id,
          label,
          count: groupCounts.get(label) || 0,
          allItems: groupAssetsByLabel.get(label) || [],
          items: [asset],
        })
      }
    })
    return Array.from(groups.values())
  }, [displayMetaByAssetId, groupAssetsByLabel, groupBy, groupCounts, visibleAssets])
  const allGroupsCollapsed = groupBy !== 'none'
    && groupedVisibleAssets.length > 0
    && groupedVisibleAssets.every((group) => collapsedGroups.has(group.id))
  const panelSelectedCount = panelAssets.reduce((count, asset) => count + (selectedIds.has(asset.id) ? 1 : 0), 0)
  const allPanelSelected = panelAssets.length > 0 && panelSelectedCount === panelAssets.length

  useEffect(() => {
    setPage(1)
  }, [activeAssetGroup, search, hasActiveFilters, assets.length])

  useEffect(() => {
    if (!activeAssetGroup) return
    if (assetGroupSummaries.some((group) => group.name === activeAssetGroup)) return
    setActiveAssetGroup(null)
  }, [activeAssetGroup, assetGroupSummaries])

  useEffect(() => {
    if (assetGroupSummaries.length <= ASSET_GROUP_OVERVIEW_LIMIT) {
      setShowAllAssetGroups(false)
    }
  }, [assetGroupSummaries.length])

  useEffect(() => {
    if (groupBy === 'none') {
      setCollapsedGroups(new Set())
    }
  }, [groupBy])

  useEffect(() => {
    if (!assetGroupOptions.includes(assignGroup)) {
      setAssignGroup(assetGroupOptions[0] || DEFAULT_SESSION_GROUP)
    }
  }, [assetGroupOptions, assignGroup])

  useEffect(() => {
    setCollapsedGroups((current) => {
      const visibleGroupIds = new Set(groupedVisibleAssets.map((group) => group.id))
      const next = new Set(Array.from(current).filter((id) => visibleGroupIds.has(id)))
      return next.size === current.size ? current : next
    })
  }, [groupedVisibleAssets])

  useEffect(() => {
    setSelectedIds((current) => {
      const availableIds = new Set(assets.map((asset) => asset.id))
      const next = new Set(Array.from(current).filter((id) => availableIds.has(id)))
      return next.size === current.size ? current : next
    })
  }, [assets])

  const visibleIds = visibleAssets.map((asset) => asset.id)
  const selectedAssets = assets.filter((asset) => selectedIds.has(asset.id))
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id))
  const someVisibleSelected = visibleIds.some((id) => selectedIds.has(id))
  const toggleVisibleSelection = () => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (allVisibleSelected) {
        visibleIds.forEach((id) => next.delete(id))
      } else {
        visibleIds.forEach((id) => next.add(id))
      }
      return next
    })
  }
  const selectPanelAssets = () => {
    setSelectedIds((current) => {
      const next = new Set(current)
      panelAssets.forEach((asset) => next.add(asset.id))
      return next
    })
  }
  const clearPanelSelection = () => {
    setSelectedIds((current) => {
      const next = new Set(current)
      panelAssets.forEach((asset) => next.delete(asset.id))
      return next
    })
  }
  const toggleAssetSelection = (assetId: number) => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(assetId)) {
        next.delete(assetId)
      } else {
        next.add(assetId)
      }
      return next
    })
  }
  const toggleGroupCollapse = (groupId: string) => {
    setCollapsedGroups((current) => {
      const next = new Set(current)
      if (next.has(groupId)) {
        next.delete(groupId)
      } else {
        next.add(groupId)
      }
      return next
    })
  }
  const toggleAllGroups = () => {
    setCollapsedGroups(() => {
      if (allGroupsCollapsed) return new Set()
      return new Set(groupedVisibleAssets.map((group) => group.id))
    })
  }
  const createAssetGroup = () => {
    const normalized = normalizeSessionGroupName(assetGroupDraft)
    if (!normalized) {
      onCreateGroup(assetGroupDraft)
      return
    }
    onCreateGroup(normalized)
    setAssignGroup(normalized)
    setAssetGroupDraft('')
    setGroupBy('assetGroup')
  }
  const assignSelectedToGroup = () => {
    onAssignGroup(selectedAssets, assignGroup)
    setGroupBy('assetGroup')
  }
  const exportCurrentAssets = () => {
    exportAssetsCsv(panelAssets, displayForAsset, `opscore-assets-${formatExportDate()}.csv`)
  }
  const exportSelectedAssets = () => {
    exportAssetsCsv(selectedAssets, displayForAsset, `opscore-selected-assets-${formatExportDate()}.csv`)
  }
  const renameCurrentGroup = (groupName: string) => {
    const next = window.prompt('请输入新的资产组名称', groupName)?.trim()
    if (!next) return
    onRenameGroup(groupName, next)
    setGroupBy('assetGroup')
  }
  const deleteCurrentGroup = (groupName: string) => {
    if (groupName === DEFAULT_SESSION_GROUP) return
    if (!window.confirm(`删除资产组「${groupName}」？组内资产会移动到「${DEFAULT_SESSION_GROUP}」。`)) return
    onDeleteGroup(groupName)
    setGroupBy('assetGroup')
  }

  return (
    <section className="ops-data-panel">
      <div className="ops-data-toolbar flex min-h-[58px] flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="text-sm font-bold text-ops-text">资产列表</h2>
          <span className="rounded-lg border border-ops-surface1 bg-ops-panel px-2 py-0.5 text-[11px] text-ops-subtext">
            {panelAssets.length} 条{activeAssetGroup ? ` / ${assets.length}` : ''}
          </span>
          {activeAssetGroup && (
            <span className="rounded-lg border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent">
              {activeAssetGroup}
            </span>
          )}
          {assets.length > ASSET_TABLE_PAGE_SIZE && (
            <span className="rounded-lg border border-ops-surface1 bg-ops-panel px-2 py-0.5 text-[11px] text-ops-overlay">
              每页 {ASSET_TABLE_PAGE_SIZE} 条
            </span>
          )}
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="ops-muted-action px-2 py-0.5 text-[11px]"
            >
              清空筛选
            </button>
          )}
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <div className="ops-control flex h-8 items-center gap-1 rounded-lg px-2">
            <input
              value={assetGroupDraft}
              onChange={(event) => setAssetGroupDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') createAssetGroup()
              }}
              placeholder="新建资产组"
              className="h-6 w-24 bg-transparent text-xs text-ops-text outline-none placeholder:text-ops-overlay"
            />
            <button
              onClick={createAssetGroup}
              className="rounded-md border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent hover:bg-ops-accent/18"
            >
              创建
            </button>
          </div>
          <label className="ops-control flex h-8 items-center gap-2 rounded-lg px-2 text-xs">
            加入
            <select
              value={assignGroup}
              onChange={(event) => setAssignGroup(event.target.value)}
              className="h-6 max-w-32 rounded-md border border-ops-surface1 bg-ops-dark px-2 text-xs text-ops-text outline-none focus:border-ops-accent"
            >
              {assetGroupOptions.map((group) => (
                <option key={group} value={group}>{group}</option>
              ))}
            </select>
            <button
              onClick={assignSelectedToGroup}
              disabled={selectedAssets.length === 0}
              className="rounded-md bg-ops-surface0 px-2 py-0.5 text-[11px] font-semibold text-ops-subtext hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-45"
            >
              选中资产
            </button>
          </label>
          <label className="ops-control flex h-8 items-center gap-2 rounded-lg px-2 text-xs">
            分组
            <select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value as AssetTableGroupBy)}
              className="h-6 rounded-md border border-ops-surface1 bg-ops-dark px-2 text-xs text-ops-text outline-none focus:border-ops-accent"
            >
              {ASSET_TABLE_GROUP_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
          </label>
          {groupBy !== 'none' && groupedVisibleAssets.length > 0 && (
            <button
              onClick={toggleAllGroups}
              className="ops-muted-action h-8 px-3 text-xs"
            >
              {allGroupsCollapsed ? '全部展开' : '全部收起'}
            </button>
          )}
          <AssetSearchBox value={search} onChange={onSearchChange} />
          <button
            onClick={onRefresh}
            className="ops-muted-action h-8 px-3 text-xs"
          >
            刷新
          </button>
          <button
            onClick={exportCurrentAssets}
            disabled={panelAssets.length === 0}
            className="ops-muted-action h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-45"
          >
            导出结果
          </button>
          <button
            onClick={selectPanelAssets}
            disabled={panelAssets.length === 0 || allPanelSelected}
            className="ops-muted-action h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-45"
          >
            选择结果
          </button>
          <button
            onClick={clearPanelSelection}
            disabled={panelSelectedCount === 0}
            className="ops-muted-action h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-45"
          >
            取消结果
          </button>
        </div>
      </div>
      {assetGroupSummaries.length > 0 && (
        <div className=" bg-[radial-gradient(circle_at_top_left,rgba(38,207,175,0.11),transparent_34%),rgba(10,18,32,0.42)] px-4 py-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-xs font-bold text-ops-text">资产组概览</div>
              <div className="mt-0.5 text-[11px] text-ops-overlay">点击组名快速过滤；需要批量进入时直接拉起组会话。</div>
            </div>
            <button
              onClick={() => setActiveAssetGroup(null)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                !activeAssetGroup
                  ? 'border-ops-accent/45 bg-ops-accent/15 text-ops-accent'
                  : 'border-ops-surface1 bg-ops-panel text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text'
              }`}
            >
              全部资产
            </button>
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-5">
            {visibleAssetGroupSummaries.map((group) => (
              <div
                key={group.name}
                className={`rounded-xl border p-3 transition-colors ${
                  activeAssetGroup === group.name
                    ? 'border-ops-accent/55 bg-ops-accent/15'
                    : 'border-ops-surface1 bg-ops-panel/80 hover:border-ops-accent/35'
                }`}
              >
                <button
                  onClick={() => {
                    setActiveAssetGroup((current) => current === group.name ? null : group.name)
                    setGroupBy('assetGroup')
                  }}
                  className="flex w-full items-start justify-between gap-3 text-left"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-bold text-ops-text" title={group.name}>{group.name}</div>
                    <div className="mt-1 text-[11px] text-ops-overlay">已验证 {group.ready}/{group.count}</div>
                  </div>
                  <div className="shrink-0 font-mono text-xl font-bold leading-none text-ops-accent">{group.count}</div>
                </button>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-ops-surface0">
                    <span
                      className="block h-full rounded-full bg-ops-accent"
                      style={{ width: `${Math.round((group.ready / Math.max(1, group.count)) * 100)}%` }}
                    />
                  </span>
                  <button
                    onClick={() => onConnectGroup(group.assets, group.name)}
                    disabled={connectingGroup === group.name}
                    className="shrink-0 rounded-lg border border-ops-accent/35 bg-ops-accent/10 px-2 py-1 text-[11px] font-semibold text-ops-accent hover:bg-ops-accent/18 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {connectingGroup === group.name ? '拉起中' : '会话'}
                  </button>
                </div>
              </div>
            ))}
          </div>
          {assetGroupSummaries.length > ASSET_GROUP_OVERVIEW_LIMIT && (
            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={() => setShowAllAssetGroups((current) => !current)}
                className="ops-muted-action px-3 py-1.5 text-xs"
              >
                {showAllAssetGroups ? '收起资产组' : `还有 ${hiddenAssetGroupCount} 个资产组，点击显示`}
              </button>
            </div>
          )}
        </div>
      )}
      {selectedIds.size > 0 && (
        <div className="flex flex-col gap-2  bg-ops-accent/10 px-4 py-3 text-xs text-ops-subtext lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-lg bg-ops-accent/15 px-2.5 py-1 font-semibold text-ops-accent">
              已选择 {selectedIds.size} 条资产
            </span>
            <span className="rounded-lg border border-ops-surface1 bg-ops-panel px-2.5 py-1 text-ops-overlay">
              当前结果 {panelSelectedCount}/{panelAssets.length}
            </span>
            <span className="text-ops-overlay">批量动作只针对已选择资产执行，避免误操作整库。</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onBulkVerify(selectedAssets)}
              disabled={bulkVerifying || bulkDeleting || connectingSelected}
              className="ops-primary-action px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
            >
              {bulkVerifying ? '验证中...' : '批量验证'}
            </button>
            <button
              onClick={() => onConnectSelected(selectedAssets)}
              disabled={connectingSelected || bulkVerifying || bulkDeleting}
              className="ops-muted-action px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
            >
              {connectingSelected ? '拉起中...' : '批量会话'}
            </button>
            <button
              onClick={exportSelectedAssets}
              disabled={connectingSelected || bulkVerifying || bulkDeleting}
              className="ops-muted-action px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
            >
              导出选中
            </button>
            <button
              onClick={() => onBulkDelete(selectedAssets)}
              disabled={bulkDeleting || bulkVerifying || connectingSelected}
              className="ops-danger-action px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
            >
              {bulkDeleting ? '删除中...' : '批量删除'}
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="rounded-lg border border-ops-surface1 bg-ops-panel px-3 py-1.5 text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
            >
              清空选择
            </button>
          </div>
        </div>
      )}
      <div className="overflow-auto">
        <table className="ops-data-table">
          <thead className="">
            <tr className="">
              <th className="w-10 px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  ref={(node) => {
                    if (node) node.indeterminate = !allVisibleSelected && someVisibleSelected
                  }}
                  onChange={toggleVisibleSelection}
                  aria-label="选择当前页资产"
                  className="h-4 w-4 rounded border-ops-surface1 bg-ops-dark text-ops-accent"
                />
              </th>
              <th className="px-4 py-3 font-semibold">名称</th>
              <th className="px-4 py-3 font-semibold">地址</th>
              <th className="px-4 py-3 font-semibold">类型</th>
              <th className="px-4 py-3 font-semibold">主接入</th>
              <th className="px-4 py-3 font-semibold">标签</th>
              <th className="px-4 py-3 font-semibold">状态</th>
              <th className="px-4 py-3 text-right font-semibold">操作</th>
            </tr>
          </thead>
          <tbody>
            {groupedVisibleAssets.map((group) => (
              <Fragment key={group.id}>
                {groupBy !== 'none' && (
                  <tr className="border-b border-ops-surface1/70 bg-ops-dark/45">
                    <td colSpan={8} className="px-4 py-2">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                        <button
                          onClick={() => toggleGroupCollapse(group.id)}
                          className="flex min-w-0 items-center gap-2 text-left"
                        >
                          <span className="font-mono text-[11px] text-ops-overlay">
                            {collapsedGroups.has(group.id) ? '+' : '-'}
                          </span>
                          <span className="rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-2 py-0.5 font-semibold text-ops-accent">
                            {group.label}
                          </span>
                          <span className="text-ops-overlay">
                            本页 {group.items.length} 条 / 共 {group.count} 条
                          </span>
                        </button>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-ops-overlay">
                            {ASSET_TABLE_GROUP_OPTIONS.find((option) => option.id === groupBy)?.label}
                          </span>
                          {groupBy === 'assetGroup' && (
                            <>
                              <button
                                onClick={() => renameCurrentGroup(group.label)}
                                disabled={mutatingGroup === group.label}
                                className="ops-muted-action px-2.5 py-1 text-[11px] disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                改名
                              </button>
                              {group.label !== DEFAULT_SESSION_GROUP && (
                                <button
                                  onClick={() => deleteCurrentGroup(group.label)}
                                  disabled={mutatingGroup === group.label}
                                  className="ops-danger-action px-2.5 py-1 text-[11px] disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {mutatingGroup === group.label ? '处理中...' : '删除组'}
                                </button>
                              )}
                              <button
                                onClick={() => onConnectGroup(group.allItems, group.label)}
                                disabled={connectingGroup === group.label}
                                className="ops-muted-action px-2.5 py-1 text-[11px] disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {connectingGroup === group.label ? '拉起中...' : '拉起组会话'}
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                {!collapsedGroups.has(group.id) && group.items.map((asset) => {
                  const display = displayMetaForAsset(asset)
                  const matrix = matrixByAssetId.get(asset.id)
                  const verification = verificationBadge(matrix)
                  const tags = asset.tags?.length ? asset.tags : [display.categoryLabel]
                  return (
                    <tr key={asset.id} className="">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(asset.id)}
                          onChange={() => toggleAssetSelection(asset.id)}
                          aria-label={`选择资产 ${asset.remark || asset.host}`}
                          className="h-4 w-4 rounded border-ops-surface1 bg-ops-dark text-ops-accent"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-[18rem] truncate font-semibold text-ops-text" title={asset.remark || asset.host}>
                          {asset.remark || asset.host}
                        </div>
                        <div className="mt-1 truncate font-mono text-[11px] text-ops-overlay">{asset.username || '-'}</div>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-ops-subtext">{asset.host}:{asset.port}</td>
                      <td className="px-4 py-3 text-ops-subtext">{display.typeLabel}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-2 py-1 text-[11px] font-semibold text-ops-subtext">
                          {display.protocolLabel}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex max-w-[16rem] flex-wrap gap-1.5">
                          {tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="rounded-lg bg-ops-surface0 px-2 py-0.5 text-[11px] text-ops-subtext">{tag}</span>
                          ))}
                          {tags.length > 3 && <span className="text-[11px] text-ops-overlay">+{tags.length - 3}</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-lg border px-2 py-1 text-[11px] font-semibold ${verification.className}`}>
                          {verification.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1.5 whitespace-nowrap">
                          <button
                            onClick={() => onConnect(asset)}
                            className="ops-muted-action px-2.5 py-1 text-xs"
                          >
                            连接
                          </button>
                          <button
                            onClick={() => onOpenVerification(asset)}
                            className="rounded-lg border border-ops-success/35 bg-ops-success/10 px-2.5 py-1 text-xs font-semibold text-ops-success hover:bg-ops-success/18"
                          >
                            验证
                          </button>
                          <button
                            onClick={() => onEdit(asset)}
                            className="ops-muted-action px-2.5 py-1 text-xs"
                          >
                            编辑
                          </button>
                          <button
                            onClick={() => onDelete(asset)}
                            className="ops-danger-action px-2.5 py-1 text-xs"
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </Fragment>
            ))}
            {panelAssets.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-sm text-ops-subtext">
                  当前没有匹配的资产
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {panelAssets.length > ASSET_TABLE_PAGE_SIZE && (
        <div className="flex flex-col gap-2 border-t border-ops-surface1/75 bg-ops-surface0/35 px-4 py-3 text-xs text-ops-subtext sm:flex-row sm:items-center sm:justify-between">
          <span>
            显示 {pageStart + 1}-{Math.min(pageStart + ASSET_TABLE_PAGE_SIZE, panelAssets.length)} / {panelAssets.length} 条
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={currentPage <= 1}
              className="ops-muted-action px-3 py-1 disabled:cursor-not-allowed disabled:opacity-45"
            >
              上一页
            </button>
            <span className="rounded-lg bg-ops-panel px-2.5 py-1 text-ops-overlay">
              {currentPage} / {pageCount}
            </span>
            <button
              onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
              disabled={currentPage >= pageCount}
              className="ops-muted-action px-3 py-1 disabled:cursor-not-allowed disabled:opacity-45"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

function AssetSearchBox({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  const [draft, setDraft] = useState(value)
  const [, startTransition] = useTransition()
  const onChangeRef = useRef(onChange)

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    setDraft(value)
  }, [value])

  useEffect(() => {
    if (draft === value) return
    const timer = window.setTimeout(() => {
      startTransition(() => onChangeRef.current(draft))
    }, 180)
    return () => window.clearTimeout(timer)
  }, [draft, startTransition, value])

  return (
    <input
      type="text"
      placeholder="搜索资产、地址、账号、类型、主接入"
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        if (draft !== value) startTransition(() => onChangeRef.current(draft))
      }}
      className="h-8 min-w-64 rounded-lg border border-ops-surface1 bg-ops-panel px-3 text-xs text-ops-text outline-none focus:border-ops-accent"
    />
  )
}

function verificationBadge(matrix?: AssetVerificationStatusMatrix) {
  if (!matrix) {
    return { label: '需复验', className: 'border-amber-400/40 bg-amber-400/10 text-amber-200' }
  }
  if (matrix.status === 'ready') {
    return { label: '已验证', className: 'border-ops-success/35 bg-ops-success/10 text-ops-success' }
  }
  return { label: '需复验', className: 'border-amber-400/40 bg-amber-400/10 text-amber-200' }
}

function assetTableGroupLabel(asset: Asset, display: AssetDisplayMeta, groupBy: AssetTableGroupBy) {
  if (groupBy === 'assetGroup') return normalizeSessionGroupName(asset.tags?.[0]) || DEFAULT_SESSION_GROUP
  if (groupBy === 'type') return display.typeLabel || asset.asset_type || '未标记类型'
  if (groupBy === 'protocol') return display.protocolLabel || asset.protocol || '未标记主接入'
  if (groupBy === 'category') return display.categoryLabel || '未分类'
  return '全部资产'
}

function exportAssetsCsv(
  assets: Asset[],
  displayForAsset: (asset: Asset) => AssetDisplayMeta,
  filename: string
) {
  if (!assets.length) {
    window.alert('没有可导出的资产')
    return
  }
  const headers = ['名称', '主机', '端口', '账号', '类型', '主接入', '资产组', '标签']
  const rows = assets.map((asset) => {
    const display = displayForAsset(asset)
    const tags = asset.tags || []
    return [
      asset.remark || asset.host,
      asset.host,
      String(asset.port ?? ''),
      asset.username || '',
      display.typeLabel || asset.asset_type || '',
      display.protocolLabel || asset.protocol || '',
      normalizeSessionGroupName(tags[0]) || DEFAULT_SESSION_GROUP,
      tags.join('|'),
    ]
  })
  const csv = [headers, ...rows]
    .map((row) => row.map(csvCell).join(','))
    .join('\r\n')
  const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function csvCell(value: string) {
  return `"${value.replace(/"/g, '""')}"`
}

function formatExportDate() {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`
}
