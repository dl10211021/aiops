import { CategoryFilterRow, FilterRow, type FilterOption } from './AssetVaultParts'

export interface AssetCategoryStat extends FilterOption {
  assetCount: number
  typeCount: number
}

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
    <div className="flex items-center gap-2">
      <details className="relative">
        <summary className="list-none rounded-lg border border-ops-surface1 bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text">
          更多
        </summary>
        <div className="absolute right-0 z-20 mt-2 w-36 overflow-hidden rounded-lg border border-ops-surface1 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
          <button onClick={onBatchImport}
            className="block w-full px-3 py-2 text-left text-xs text-ops-subtext transition-colors hover:bg-ops-surface0 hover:text-ops-text">批量导入</button>
          <button onClick={onNormalize}
            className="block w-full border-t border-ops-surface1 px-3 py-2 text-left text-xs text-ops-subtext transition-colors hover:bg-ops-surface0 hover:text-ops-text">规范化检查</button>
        </div>
      </details>
      <button onClick={onCreateAsset}
        className="rounded-lg bg-ops-accent px-3 py-1.5 text-sm font-bold text-ops-dark transition-colors hover:bg-ops-accent/80">新增资产</button>
    </div>
  )
}

export function AssetVaultFilterPanel({
  assetCount,
  assetTypeFilter,
  assetTypeLabels,
  availableAssetTypes,
  availableCategoryOptions,
  availableConnectors,
  categoryFilter,
  categoryStats,
  catalogTypeCount,
  connectorFilter,
  connectorLabels,
  hasActiveFilters,
  onAssetTypeChange,
  onCategoryChange,
  onClearFilters,
  onConnectorChange,
}: {
  assetCount: number
  assetTypeFilter: string
  assetTypeLabels: Record<string, string>
  availableAssetTypes: string[]
  availableCategoryOptions: FilterOption[]
  availableConnectors: string[]
  categoryFilter: string
  categoryStats: AssetCategoryStat[]
  catalogTypeCount: number
  connectorFilter: string
  connectorLabels: Record<string, string>
  hasActiveFilters: boolean
  onAssetTypeChange: (value: string) => void
  onCategoryChange: (value: string) => void
  onClearFilters: () => void
  onConnectorChange: (value: string) => void
}) {
  return (
    <details className="mb-3 rounded-lg border border-ops-surface1/70 bg-ops-panel">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3">
        <div>
          <div className="text-xs font-semibold text-ops-text">高级筛选</div>
          <div className="text-[11px] text-ops-overlay">{catalogTypeCount} 类资产 / 当前 {assetCount} 条</div>
        </div>
        {hasActiveFilters && (
          <button
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              onClearFilters()
            }}
            className="rounded-lg bg-ops-surface0 px-2.5 py-1 text-xs text-ops-subtext hover:text-ops-text"
          >
            清空过滤
          </button>
        )}
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
        {categoryStats.length > 0 && (
          <div className="mt-3 border-t border-ops-surface1/70 pt-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-xs font-semibold text-ops-text">目录覆盖</span>
              <span className="text-[11px] text-ops-overlay">{catalogTypeCount} 类资产 / 已保存 {assetCount}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-6">
              {categoryStats.slice(0, 12).map((item) => (
                <button
                  key={item.id}
                  onClick={() => onCategoryChange(item.id)}
                  title={item.description || item.label}
                  className={`rounded-lg border p-2 text-left transition-colors ${
                    categoryFilter === item.id
                      ? 'border-ops-accent bg-ops-accent/10'
                      : 'border-ops-surface1 bg-ops-dark/25 hover:border-ops-accent/45'
                  }`}
                >
                  <div className="truncate text-[11px] font-semibold text-ops-text">{item.label}</div>
                  <div className="mt-1 flex items-center justify-between gap-2 text-[10px] text-ops-overlay">
                    <span>{item.typeCount} 类</span>
                    <span>已保存 {item.assetCount}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </details>
  )
}
