import { CategoryFilterRow, FilterRow, type FilterOption } from './AssetVaultParts'

export function AssetVaultHeaderActions({
  onBatchImport,
  onCreateAsset,
  onNormalize,
}: {
  onBatchImport: () => void
  onCreateAsset: () => void
  onNormalize: () => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button onClick={onBatchImport}
        className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text">批量导入</button>
      <button onClick={onNormalize}
        className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text">规范化检查</button>
      <button onClick={onCreateAsset}
        className="rounded-lg bg-ops-accent px-3 py-1.5 text-sm font-bold text-ops-dark transition-colors hover:bg-ops-accent/80">新建资产</button>
    </div>
  )
}

export function AssetVaultFilterPanel({
  assetTypeFilter,
  assetTypeLabels,
  availableAssetTypes,
  availableCategoryOptions,
  availableConnectors,
  categoryFilter,
  connectorFilter,
  connectorLabels,
  hasActiveFilters,
  onAssetTypeChange,
  onCategoryChange,
  onClearFilters,
  onConnectorChange,
}: {
  assetTypeFilter: string
  assetTypeLabels: Record<string, string>
  availableAssetTypes: string[]
  availableCategoryOptions: FilterOption[]
  availableConnectors: string[]
  categoryFilter: string
  connectorFilter: string
  connectorLabels: Record<string, string>
  hasActiveFilters: boolean
  onAssetTypeChange: (value: string) => void
  onCategoryChange: (value: string) => void
  onClearFilters: () => void
  onConnectorChange: (value: string) => void
}) {
  return (
    <details className="mb-3 rounded-xl border border-ops-surface1/70 bg-ops-panel">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3">
        <div>
          <div className="text-xs font-semibold text-ops-text">高级筛选</div>
          <div className="text-[11px] text-ops-overlay">
            {hasActiveFilters
              ? '已启用筛选条件，展开可调整分类、类型和主接入。'
              : '按分类、类型、主接入定位资产；默认收起，优先展示资产列表。'}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={`rounded-full border px-2.5 py-1 text-[11px] ${
              hasActiveFilters
                ? 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent'
                : 'border-ops-surface1 bg-ops-dark/40 text-ops-overlay'
            }`}
          >
            {hasActiveFilters ? '筛选中' : '展开筛选'}
          </span>
          {hasActiveFilters && (
            <button
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                onClearFilters()
              }}
              className="rounded-lg bg-ops-surface0 px-2.5 py-1 text-xs text-ops-subtext hover:text-ops-text"
            >
              清空
            </button>
          )}
        </div>
      </summary>
      <div className="border-t border-ops-surface1/70 px-4 py-3">
        <CategoryFilterRow
          value={categoryFilter}
          options={availableCategoryOptions}
          onChange={onCategoryChange}
        />
        <FilterRow
          label="类型"
          value={assetTypeFilter}
          options={availableAssetTypes.map((id) => ({ id, label: assetTypeLabels[id] || id.toUpperCase() }))}
          onChange={onAssetTypeChange}
        />
        <FilterRow
          label="主接入"
          value={connectorFilter}
          options={availableConnectors.map((id) => ({ id, label: connectorLabels[id] || id.toUpperCase() }))}
          onChange={onConnectorChange}
        />
      </div>
    </details>
  )
}
