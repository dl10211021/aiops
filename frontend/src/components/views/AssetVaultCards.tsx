import type { Asset, ProtocolVerificationStatusOverview } from '@/types'
import { VerificationStatusStrip } from './AssetVerificationPanel'
import { AssetMetaLine } from './AssetVaultParts'
import { normalizeFilterValue, protocolBadgeTone } from './assetVaultModel'

export function AssetCard({
  asset,
  categoryLabel,
  connectorLabel,
  matrix,
  protocolLabel,
  typeLabel,
  onConnect,
  onEdit,
  onDelete,
  onOpenVerification,
}: {
  asset: Asset
  categoryLabel: string
  connectorLabel: string
  matrix?: ProtocolVerificationStatusOverview['matrix'][number]
  protocolLabel: string
  typeLabel: string
  onConnect: (asset: Asset) => void
  onEdit: (asset: Asset) => void
  onDelete: (asset: Asset) => void
  onOpenVerification: (asset: Asset) => void
}) {
  return (
    <div className="ops-data-panel p-4 transition-all hover:-translate-y-0.5 hover:border-ops-accent/45">
      {matrix && <VerificationStatusStrip matrix={matrix} />}
      <div className="mb-2 flex items-start justify-between">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-ops-text">{asset.remark || asset.host}</div>
          <div className="mt-0.5 text-xs text-ops-overlay">{asset.username}@{asset.host}:{asset.port}</div>
        </div>
        <span
          className={`max-w-[9rem] truncate rounded px-1.5 py-0.5 text-[10px] ${protocolBadgeTone(normalizeFilterValue(asset.protocol || asset.asset_type))}`}
          title={typeLabel}
        >
          {typeLabel}
        </span>
      </div>
      <div className="mb-2 grid gap-1.5 rounded-lg border border-ops-surface0 bg-ops-dark/25 p-2 text-[11px]">
        <AssetMetaLine label="分类" value={categoryLabel} />
        <AssetMetaLine label="工具" value={connectorLabel} />
        <AssetMetaLine label="主接入" value={protocolLabel} />
      </div>
      <div className="mb-2 flex flex-wrap gap-1.5 text-[10px]">
        {(asset.tags || []).slice(0, 3).map((tag) => (
          <span key={tag} className="rounded bg-ops-surface0 px-1.5 py-0.5 text-ops-subtext">{tag}</span>
        ))}
      </div>
      {asset.skills?.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {asset.skills.slice(0, 3).map((skill) => (
            <span key={skill} className="rounded bg-ops-surface0 px-1.5 py-0.5 text-[10px] text-ops-subtext">{skill}</span>
          ))}
          {asset.skills.length > 3 && <span className="text-[10px] text-ops-overlay">+{asset.skills.length - 3}</span>}
        </div>
      )}
      <div className="mt-3 grid grid-cols-4 gap-2">
        <button onClick={() => onConnect(asset)} className="ops-primary-action col-span-2 py-1.5 text-xs">连接</button>
        <button onClick={() => onOpenVerification(asset)} className="rounded-lg border border-ops-success/35 bg-ops-success/10 px-2.5 py-1.5 text-xs font-semibold text-ops-success transition-colors hover:bg-ops-success/18">验证</button>
        <button onClick={() => onEdit(asset)} className="ops-muted-action px-2.5 py-1.5 text-xs">编辑</button>
        <button onClick={() => onDelete(asset)} className="ops-danger-action col-span-4 px-2.5 py-1.5 text-xs">删除</button>
      </div>
    </div>
  )
}

export function AssetEmptyState({
  assetCount,
  hasActiveFilters,
  onClearFilters,
  onCreateAsset,
}: {
  assetCount: number
  hasActiveFilters: boolean
  onClearFilters: () => void
  onCreateAsset: () => void
}) {
  return (
    <div className="ops-data-panel p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold text-ops-text">
            {assetCount === 0 ? '还没有保存资产' : '没有匹配的资产'}
          </p>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            {assetCount === 0
              ? '先从资产目录选择类型并保存连接，后续会话、巡检和审批都会复用这份资产上下文。'
              : '当前筛选条件下没有结果，可以清空筛选或切换到其它资产目录。'}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="ops-muted-action px-3 py-1.5 text-xs"
            >
              清空筛选
            </button>
          )}
          <button
            onClick={onCreateAsset}
            className="ops-primary-action px-3 py-1.5 text-xs"
          >
            新建连接
          </button>
        </div>
      </div>
    </div>
  )
}
