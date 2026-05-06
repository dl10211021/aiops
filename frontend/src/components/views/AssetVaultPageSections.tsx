import type { Asset, AssetVerificationMatrix, ProtocolVerificationOverview } from '@/types'
import { AssetCard } from './AssetVaultCards'
import { OverviewCard, type AssetDisplayMeta } from './AssetVaultParts'
import { assetTypeKey } from './assetVaultModel'
import type { AssetVaultGroup } from './assetVaultViewModel'

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
  return (
    <section className="overflow-hidden rounded-lg border border-ops-surface1/80 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
      <div className="flex min-h-[50px] flex-col gap-3 border-b border-ops-surface1/75 bg-ops-surface0/65 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="text-sm font-bold text-ops-text">资产列表</h2>
          <span className="rounded-lg border border-ops-surface1 bg-ops-panel px-2 py-0.5 text-[11px] text-ops-subtext">
            {assets.length} 条
          </span>
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
            placeholder="搜索资产、地址、账号、协议"
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
      <div className="overflow-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-ops-surface0/55 text-[11px] uppercase tracking-normal text-ops-overlay">
            <tr className="border-b border-ops-surface1/75">
              <th className="px-4 py-3 font-semibold">名称</th>
              <th className="px-4 py-3 font-semibold">地址</th>
              <th className="px-4 py-3 font-semibold">类型</th>
              <th className="px-4 py-3 font-semibold">协议</th>
              <th className="px-4 py-3 font-semibold">标签</th>
              <th className="px-4 py-3 font-semibold">验证</th>
              <th className="px-4 py-3 text-right font-semibold">操作</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => {
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
                        onClick={() => onEdit(asset)}
                        className="rounded-lg border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-accent"
                      >
                        编辑
                      </button>
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
                        onClick={() => onDelete(asset)}
                        className="rounded-lg border border-ops-alert/30 bg-ops-alert/8 px-2.5 py-1 text-xs font-semibold text-ops-alert hover:bg-ops-alert/14"
                      >
                        删除
                      </button>
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
