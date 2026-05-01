import type { Asset, AssetVerificationMatrix, ProtocolVerificationOverview } from '@/types'
import { AssetCard } from './AssetVaultCards'
import { OverviewCard } from './AssetVaultParts'
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
