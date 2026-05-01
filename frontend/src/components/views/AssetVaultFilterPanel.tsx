import { CategoryFilterRow, FilterRow, type FilterOption } from './AssetVaultParts'

export interface AssetCategoryStat extends FilterOption {
  assetCount: number
  typeCount: number
}

export function AssetVaultHeaderActions({
  search,
  onCreateAsset,
  onNormalize,
  onRefresh,
  onSearchChange,
}: {
  search: string
  onCreateAsset: () => void
  onNormalize: () => void
  onRefresh: () => void
  onSearchChange: (value: string) => void
}) {
  return (
    <>
      <input
        type="text"
        placeholder="搜索资产、账号、连接方式..."
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        className="min-w-72 flex-1 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-1.5 text-sm text-ops-text outline-none focus:border-ops-accent xl:w-80 xl:flex-none"
      />
      <button onClick={onCreateAsset}
        className="rounded-lg bg-ops-accent px-3 py-1.5 text-sm font-medium text-ops-dark transition-colors hover:bg-ops-accent/80">+ 新建连接</button>
      <button onClick={onNormalize}
        className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext transition-colors hover:text-ops-text">规范化</button>
      <button onClick={onRefresh}
        className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext transition-colors hover:text-ops-text">刷新</button>
    </>
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
    <div className="mb-5 rounded-lg border border-ops-surface0 bg-ops-panel/60 p-3">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold text-ops-text">资产目录过滤</div>
          <div className="text-[11px] text-ops-overlay">按分类、资产类型和连接方式联动确认资产中心覆盖范围，筛选不会影响保存数据。</div>
        </div>
        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="rounded-lg bg-ops-surface0 px-2.5 py-1 text-xs text-ops-subtext hover:text-ops-text"
          >
            清空过滤
          </button>
        )}
      </div>
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
        label="连接方式"
        value={connectorFilter}
        options={availableConnectors.map((id) => ({ id, label: connectorLabels[id] || id.toUpperCase() }))}
        onChange={onConnectorChange}
      />
      {categoryStats.length > 0 && (
        <div className="mt-3 border-t border-ops-surface0 pt-3">
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
                    : 'border-ops-surface0 bg-ops-dark/25 hover:border-ops-accent/45'
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
  )
}
