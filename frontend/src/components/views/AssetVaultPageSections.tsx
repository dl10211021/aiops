import type { Asset, AssetVerificationMatrix, ProtocolVerificationOverview } from '@/types'
import { Fragment, useEffect, useMemo, useState } from 'react'
import { AssetCard } from './AssetVaultCards'
import { OverviewCard, type AssetDisplayMeta } from './AssetVaultParts'
import { assetTypeKey } from './assetVaultModel'
import type { AssetVaultGroup } from './assetVaultViewModel'

const ASSET_TABLE_PAGE_SIZE = 50
type AssetTableGroupBy = 'category' | 'type' | 'protocol' | 'none'
const ASSET_TABLE_GROUP_OPTIONS: Array<{ id: AssetTableGroupBy; label: string }> = [
  { id: 'category', label: '按分类' },
  { id: 'type', label: '按类型' },
  { id: 'protocol', label: '按主接入' },
  { id: 'none', label: '不分组' },
]

export function AssetOverviewGrid({
  overview,
  verificationOverview,
}: {
  overview: Record<string, number> | null
  verificationOverview: ProtocolVerificationOverview | null
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
    <section className="mb-3 overflow-hidden rounded-xl border border-ops-surface1/80 bg-[linear-gradient(135deg,rgba(38,207,175,0.10),rgba(10,18,32,0.96)_48%,rgba(44,88,148,0.12))] shadow-[var(--ops-panel-shadow)]">
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
  matrixByAssetId: Map<number, AssetVerificationMatrix>
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
  bulkVerifying,
  displayForAsset,
  hasActiveFilters,
  matrixByAssetId,
  onBulkVerify,
  onClearFilters,
  onConnect,
  onEdit,
  onDelete,
  onOpenVerification,
  onRefresh,
  onSearchChange,
  search,
}: {
  assets: Asset[]
  bulkVerifying: boolean
  displayForAsset: (asset: Asset) => AssetDisplayMeta
  hasActiveFilters: boolean
  matrixByAssetId: Map<number, AssetVerificationMatrix>
  onBulkVerify: (assets: Asset[]) => void
  onClearFilters: () => void
  onConnect: (asset: Asset) => void
  onEdit: (asset: Asset) => void
  onDelete: (asset: Asset) => void
  onOpenVerification: (asset: Asset) => void
  onRefresh: () => void
  onSearchChange: (value: string) => void
  search: string
}) {
  const [page, setPage] = useState(1)
  const [groupBy, setGroupBy] = useState<AssetTableGroupBy>('category')
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => new Set())
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set())
  const pageCount = Math.max(1, Math.ceil(assets.length / ASSET_TABLE_PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const pageStart = (currentPage - 1) * ASSET_TABLE_PAGE_SIZE
  const visibleAssets = useMemo(
    () => assets.slice(pageStart, pageStart + ASSET_TABLE_PAGE_SIZE),
    [assets, pageStart]
  )
  const groupCounts = useMemo(() => {
    const counts = new Map<string, number>()
    if (groupBy === 'none') return counts
    assets.forEach((asset) => {
      const label = assetTableGroupLabel(asset, displayForAsset(asset), groupBy)
      counts.set(label, (counts.get(label) || 0) + 1)
    })
    return counts
  }, [assets, displayForAsset, groupBy])
  const groupedVisibleAssets = useMemo(() => {
    if (groupBy === 'none') {
      return [{ id: 'all', label: '全部资产', count: visibleAssets.length, items: visibleAssets }]
    }
    const groups = new Map<string, { id: string; label: string; count: number; items: Asset[] }>()
    visibleAssets.forEach((asset) => {
      const label = assetTableGroupLabel(asset, displayForAsset(asset), groupBy)
      const id = `${groupBy}:${label}`
      const current = groups.get(id)
      if (current) {
        current.items.push(asset)
      } else {
        groups.set(id, {
          id,
          label,
          count: groupCounts.get(label) || 0,
          items: [asset],
        })
      }
    })
    return Array.from(groups.values())
  }, [displayForAsset, groupBy, groupCounts, visibleAssets])
  const allGroupsCollapsed = groupBy !== 'none'
    && groupedVisibleAssets.length > 0
    && groupedVisibleAssets.every((group) => collapsedGroups.has(group.id))

  useEffect(() => {
    setPage(1)
  }, [search, hasActiveFilters, assets.length])

  useEffect(() => {
    if (groupBy === 'none') {
      setCollapsedGroups(new Set())
    }
  }, [groupBy])

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

  return (
    <section className="overflow-hidden rounded-xl border border-ops-surface1/80 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
      <div className="flex min-h-[58px] flex-col gap-3 border-b border-ops-surface1/75 bg-ops-surface0/65 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="text-sm font-bold text-ops-text">资产列表</h2>
          <span className="rounded-lg border border-ops-surface1 bg-ops-panel px-2 py-0.5 text-[11px] text-ops-subtext">
            {assets.length} 条
          </span>
          {assets.length > ASSET_TABLE_PAGE_SIZE && (
            <span className="rounded-lg border border-ops-surface1 bg-ops-panel px-2 py-0.5 text-[11px] text-ops-overlay">
              每页 {ASSET_TABLE_PAGE_SIZE} 条
            </span>
          )}
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="rounded-lg border border-ops-surface1 bg-ops-panel px-2 py-0.5 text-[11px] text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
            >
              清空筛选
            </button>
          )}
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <label className="flex h-8 items-center gap-2 rounded-lg border border-ops-surface1 bg-ops-panel px-2 text-xs text-ops-overlay">
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
              className="h-8 rounded-lg border border-ops-surface1 bg-ops-panel px-3 text-xs font-semibold text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
            >
              {allGroupsCollapsed ? '全部展开' : '全部收起'}
            </button>
          )}
          <input
            type="text"
            placeholder="搜索资产、地址、账号、类型、主接入"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            className="h-8 min-w-64 rounded-lg border border-ops-surface1 bg-ops-panel px-3 text-xs text-ops-text outline-none focus:border-ops-accent"
          />
          <button
            onClick={onRefresh}
            className="h-8 rounded-lg border border-ops-surface1 bg-ops-panel px-3 text-xs font-semibold text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
          >
            刷新
          </button>
        </div>
      </div>
      {selectedIds.size > 0 && (
        <div className="flex flex-col gap-2 border-b border-ops-surface1/75 bg-ops-accent/10 px-4 py-3 text-xs text-ops-subtext lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-lg bg-ops-accent/15 px-2.5 py-1 font-semibold text-ops-accent">
              已选择 {selectedIds.size} 条资产
            </span>
            <span className="text-ops-overlay">批量动作只针对已选择资产执行，避免误操作整库。</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onBulkVerify(selectedAssets)}
              disabled={bulkVerifying}
              className="rounded-lg bg-ops-accent px-3 py-1.5 font-semibold text-ops-dark transition-colors hover:bg-ops-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {bulkVerifying ? '验证中...' : '批量验证'}
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
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-ops-surface0/55 text-[11px] uppercase tracking-normal text-ops-overlay">
            <tr className="border-b border-ops-surface1/75">
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
                        <span className="text-[11px] text-ops-overlay">
                          {ASSET_TABLE_GROUP_OPTIONS.find((option) => option.id === groupBy)?.label}
                        </span>
                      </div>
                    </td>
                  </tr>
                )}
                {!collapsedGroups.has(group.id) && group.items.map((asset) => {
                  const display = displayForAsset(asset)
                  const matrix = matrixByAssetId.get(asset.id)
                  const verification = verificationBadge(matrix)
                  const tags = asset.tags?.length ? asset.tags : [display.categoryLabel]
                  return (
                    <tr key={asset.id} className="border-b border-ops-surface1/55 hover:bg-ops-surface0/35">
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
                            className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-2.5 py-1 text-xs font-semibold text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
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
                            className="rounded-lg border border-ops-surface1 bg-ops-panel px-2.5 py-1 text-xs font-semibold text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
                          >
                            编辑
                          </button>
                          <button
                            onClick={() => onDelete(asset)}
                            className="rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-2.5 py-1 text-xs font-semibold text-ops-alert hover:bg-ops-alert/15"
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
            {assets.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-sm text-ops-subtext">
                  当前没有匹配的资产
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {assets.length > ASSET_TABLE_PAGE_SIZE && (
        <div className="flex flex-col gap-2 border-t border-ops-surface1/75 bg-ops-surface0/35 px-4 py-3 text-xs text-ops-subtext sm:flex-row sm:items-center sm:justify-between">
          <span>
            显示 {pageStart + 1}-{Math.min(pageStart + ASSET_TABLE_PAGE_SIZE, assets.length)} / {assets.length} 条
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={currentPage <= 1}
              className="rounded-lg border border-ops-surface1 px-3 py-1 disabled:cursor-not-allowed disabled:opacity-45 hover:border-ops-accent/50 hover:text-ops-text"
            >
              上一页
            </button>
            <span className="rounded-lg bg-ops-panel px-2.5 py-1 text-ops-overlay">
              {currentPage} / {pageCount}
            </span>
            <button
              onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
              disabled={currentPage >= pageCount}
              className="rounded-lg border border-ops-surface1 px-3 py-1 disabled:cursor-not-allowed disabled:opacity-45 hover:border-ops-accent/50 hover:text-ops-text"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

function verificationBadge(matrix?: AssetVerificationMatrix) {
  if (!matrix) {
    return { label: '需复验', className: 'border-amber-400/40 bg-amber-400/10 text-amber-200' }
  }
  if (matrix.status === 'ready') {
    return { label: '已验证', className: 'border-ops-success/35 bg-ops-success/10 text-ops-success' }
  }
  return { label: '需复验', className: 'border-amber-400/40 bg-amber-400/10 text-amber-200' }
}

function assetTableGroupLabel(asset: Asset, display: AssetDisplayMeta, groupBy: AssetTableGroupBy) {
  if (groupBy === 'type') return display.typeLabel || asset.asset_type || '未标记类型'
  if (groupBy === 'protocol') return display.protocolLabel || asset.protocol || '未标记主接入'
  if (groupBy === 'category') return display.categoryLabel || '未分类'
  return '全部资产'
}
