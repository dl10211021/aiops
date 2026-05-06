import type { Asset, AssetVerificationMatrix, ProtocolVerificationOverview } from '@/types'
import { useEffect, useMemo, useState } from 'react'
import { AssetCard } from './AssetVaultCards'
import { OverviewCard, type AssetDisplayMeta } from './AssetVaultParts'
import { assetTypeKey } from './assetVaultModel'
import type { AssetVaultGroup } from './assetVaultViewModel'

const ASSET_TABLE_PAGE_SIZE = 50

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
  savedCategoryCount,
  protocolCount,
}: {
  assetCount: number
  catalogTypeCount: number
  filteredCount: number
  readyCount: number
  savedCategoryCount: number
  protocolCount: number
}) {
  const items = [
    { title: '主机系统', detail: 'Linux/Unix SSH、Windows WinRM' },
    { title: '数据服务', detail: '数据库、缓存、大数据使用原生协议或 API' },
    { title: '平台设备', detail: '虚拟化、容器、监控、安全平台走 API' },
    { title: '网络存储', detail: '交换机、防火墙、存储按 SSH/SNMP/API 建档' },
  ]
  const stats = [
    { label: '已入库资产', value: assetCount, hint: '支持上千资产台账' },
    { label: '当前筛选', value: filteredCount, hint: '搜索和筛选结果' },
    { label: '验证就绪', value: readyCount, hint: '可直接进入会话' },
    { label: '资产类型目录', value: catalogTypeCount, hint: '覆盖数据中心常规设备' },
  ]

  return (
    <section className="mb-4 overflow-hidden rounded-xl border border-ops-surface1/80 bg-[linear-gradient(135deg,rgba(38,207,175,0.12),rgba(10,18,32,0.98)_42%,rgba(44,88,148,0.14))] shadow-[var(--ops-panel-shadow)]">
      <div className="grid gap-4 p-4 xl:grid-cols-[1.25fr_1fr]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-ops-accent/35 bg-ops-accent/10 px-2.5 py-1 text-[11px] font-semibold text-ops-accent">
              企业资产台账
            </span>
            <span className="rounded-full border border-ops-surface1 bg-ops-dark/45 px-2.5 py-1 text-[11px] text-ops-subtext">
              分类 {savedCategoryCount} 类 · 主接入 {protocolCount} 种
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-ops-text md:text-2xl">
            数据中心资产接入、凭据、验证和会话入口统一管理
          </h2>
          <p className="mt-2 max-w-3xl text-xs leading-6 text-ops-subtext">
            这里不是监控清单，而是 AI 运维的资产台账。每台设备都能保存主接入、凭据、标签和验证状态，后续会话、巡检、审批和技能执行都从这里进入。
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((item) => (
              <div key={item.label} className="rounded-lg border border-ops-surface1/80 bg-ops-dark/35 p-3">
                <div className="text-[11px] text-ops-overlay">{item.label}</div>
                <div className="mt-1 font-mono text-2xl font-bold text-ops-text">{item.value}</div>
                <div className="mt-1 text-[10px] text-ops-subtext">{item.hint}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-ops-surface1/80 bg-ops-panel/70 p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-bold text-ops-text">接入治理原则</div>
              <div className="mt-0.5 text-[11px] text-ops-overlay">支持多类型，但每类只突出最清晰的主入口。</div>
            </div>
            <span className="rounded-full bg-ops-accent/10 px-2.5 py-1 text-[11px] text-ops-accent">多类型 · 简单接入</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {items.map((item) => (
              <div key={item.title} className="rounded-lg border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
                <div className="text-xs font-semibold text-ops-text">{item.title}</div>
                <div className="mt-1 text-[11px] leading-5 text-ops-subtext">{item.detail}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/30 px-3 py-2 text-[11px] leading-5 text-ops-overlay">
            企业化边界：资产负责建档、连接、验证、批量维护；具体巡检和操作进入会话后由协议工具和安全审批控制。
          </div>
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
  displayForAsset,
  hasActiveFilters,
  matrixByAssetId,
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
  displayForAsset: (asset: Asset) => AssetDisplayMeta
  hasActiveFilters: boolean
  matrixByAssetId: Map<number, AssetVerificationMatrix>
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
  const pageCount = Math.max(1, Math.ceil(assets.length / ASSET_TABLE_PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const pageStart = (currentPage - 1) * ASSET_TABLE_PAGE_SIZE
  const visibleAssets = useMemo(
    () => assets.slice(pageStart, pageStart + ASSET_TABLE_PAGE_SIZE),
    [assets, pageStart]
  )

  useEffect(() => {
    setPage(1)
  }, [search, hasActiveFilters, assets.length])

  return (
    <section className="overflow-hidden rounded-xl border border-ops-surface1/80 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
      <div className="flex min-h-[58px] flex-col gap-3 border-b border-ops-surface1/75 bg-ops-surface0/65 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="text-sm font-bold text-ops-text">企业资产台账</h2>
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
            刷新台账
          </button>
        </div>
      </div>
      <div className="overflow-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-ops-surface0/55 text-[11px] uppercase tracking-normal text-ops-overlay">
            <tr className="border-b border-ops-surface1/75">
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
            {visibleAssets.map((asset) => {
              const display = displayForAsset(asset)
              const matrix = matrixByAssetId.get(asset.id)
              const verification = verificationBadge(matrix)
              const tags = asset.tags?.length ? asset.tags : [display.categoryLabel]
              return (
                <tr key={asset.id} className="border-b border-ops-surface1/55 hover:bg-ops-surface0/35">
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
                    <div className="flex justify-end gap-1.5">
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
                      <details className="relative">
                        <summary className="list-none rounded-lg border border-ops-surface1 px-2.5 py-1 text-xs text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text">
                          维护
                        </summary>
                        <div className="absolute right-0 z-20 mt-2 w-24 overflow-hidden rounded-lg border border-ops-surface1 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
                          <button
                            onClick={() => onEdit(asset)}
                            className="block w-full px-3 py-2 text-left text-xs text-ops-subtext transition-colors hover:bg-ops-surface0 hover:text-ops-accent"
                          >
                            编辑
                          </button>
                          <button
                            onClick={() => onDelete(asset)}
                            className="block w-full border-t border-ops-surface1 px-3 py-2 text-left text-xs text-ops-alert transition-colors hover:bg-ops-alert/10"
                          >
                            删除
                          </button>
                        </div>
                      </details>
                    </div>
                  </td>
                </tr>
              )
            })}
            {assets.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-ops-subtext">
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
