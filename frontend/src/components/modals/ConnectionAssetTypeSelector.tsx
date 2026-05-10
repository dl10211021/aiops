import { toolLabel } from '@/utils/assetDisplay'
import type { AssetAccessProtocol, ToolDisplayDetail } from '@/types'
import { MATURITY_LABELS } from './connectionModalHelpers'
import type { AssetCatalogStatus, AssetCategoryOption, AssetSubType } from './connectionModalHelpers'

interface OptionGroup<T> {
  group: string
  items: T[]
}

interface ConnectionAssetTypeSelectorProps {
  assetCategories: AssetCategoryOption[]
  assetTypeSearch: string
  catalogStatus: AssetCatalogStatus
  category: string
  categoryGroups: Array<OptionGroup<AssetCategoryOption>>
  currentAccessProtocol?: AssetAccessProtocol
  currentProtocol: string
  accessProtocolOptions: AssetAccessProtocol[]
  filteredSubTypeOptions: AssetSubType[]
  normalizedAssetTypeSearch: string
  searchedSubTypeOptions: AssetSubType[]
  selectedConnectionHint: string
  selectedConnectorGroup: string
  selectedConnectorLabel: string
  selectedMaturity: string
  selectedSubInfo?: AssetSubType
  selectedToolDetails: ToolDisplayDetail[]
  selectedTools: string[]
  subType: string
  subTypeGroups: Array<OptionGroup<AssetSubType>>
  subTypeOptions: AssetSubType[]
  onCategoryChange: (category: string) => void
  onProtocolChange: (protocol: string) => void
  onSearchChange: (value: string) => void
  onSubTypeChange: (subType: string) => void
}

export default function ConnectionAssetTypeSelector({
  assetCategories,
  assetTypeSearch,
  catalogStatus,
  category,
  categoryGroups,
  currentAccessProtocol,
  currentProtocol,
  accessProtocolOptions,
  filteredSubTypeOptions,
  normalizedAssetTypeSearch,
  searchedSubTypeOptions,
  selectedConnectionHint,
  selectedConnectorGroup,
  selectedConnectorLabel,
  selectedMaturity,
  selectedSubInfo,
  selectedToolDetails,
  selectedTools,
  subType,
  subTypeGroups,
  subTypeOptions,
  onCategoryChange,
  onProtocolChange,
  onSearchChange,
  onSubTypeChange,
}: ConnectionAssetTypeSelectorProps) {
  const displayTools: ToolDisplayDetail[] = selectedToolDetails.length > 0
    ? selectedToolDetails
    : selectedTools.map((name) => ({ name }))
  const catalogLabel = catalogStatus.loading
    ? '目录加载中'
    : catalogStatus.source === 'backend'
      ? `后端真实目录 ${catalogStatus.total} 类`
      : `离线兜底 ${catalogStatus.total} 类`

  return (
    <section className="ops-data-panel p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-ops-text">资产类型与主接入方式</div>
          <div className="mt-0.5 text-[11px] text-ops-overlay">
            当前分类 {subTypeOptions.length} 类资产，只展示 AI 运维最常用的登录、查询或 API 接入。
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-1.5">
          <span className={`ops-control px-2 py-0.5 text-[10px] ${
            catalogStatus.source === 'backend' && !catalogStatus.loading
              ? 'text-ops-success'
              : 'text-ops-alert'
          }`}>
            {catalogLabel}
          </span>
          <span className="ops-control px-2 py-0.5 text-[10px] text-ops-subtext">
            {currentProtocol.toUpperCase()}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs text-ops-subtext">资产类别</label>
          <select
            value={category}
            onChange={(event) => onCategoryChange(event.target.value)}
            className="ops-control w-full appearance-none px-3 py-2 text-sm"
          >
            {categoryGroups.map((group) => (
              <optgroup key={group.group} label={group.group}>
                {group.items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </optgroup>
            ))}
          </select>
          <div className="mt-1 text-[11px] text-ops-overlay">
            {assetCategories.length} 个分类 · {assetCategories.find((item) => item.id === category)?.group || '其它'}
          </div>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between gap-2">
            <label className="text-xs text-ops-subtext">资产类型</label>
            <span className="text-[10px] text-ops-overlay">
              {normalizedAssetTypeSearch ? `${searchedSubTypeOptions.length}/${subTypeOptions.length}` : `${subTypeOptions.length}`} 类
            </span>
          </div>
          <input
            value={assetTypeSearch}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="搜索资产类型或主接入方式"
            className="ops-control mb-2 w-full px-3 py-2 text-sm"
          />
          <select
            value={subType}
            onChange={(event) => onSubTypeChange(event.target.value)}
            className="ops-control w-full appearance-none px-3 py-2 text-sm"
          >
            {subTypeGroups.map((group) => (
              <optgroup key={group.group} label={group.group}>
                {group.items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </optgroup>
            ))}
            {filteredSubTypeOptions.length === 0 && <option value={subType}>没有匹配项</option>}
          </select>
        </div>
        {selectedSubInfo && (
          <div className="ops-data-panel col-span-2 px-3 py-2">
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-ops-text">{selectedSubInfo.label}</span>
                <span className="text-ops-overlay">/</span>
                <span className="text-ops-subtext">{selectedConnectorLabel}</span>
                <span className="text-ops-overlay">/</span>
                <span className="text-ops-subtext">{selectedConnectorGroup}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="ops-control px-1.5 py-0.5 text-[10px] text-ops-subtext">
                  默认端口 {selectedSubInfo.defaultPort}
                </span>
                <span className="ops-control px-1.5 py-0.5 text-[10px] text-ops-subtext">
                  {selectedSubInfo.capability?.credential_fields?.length || 2} 个凭据字段
                </span>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-ops-overlay">能力状态</span>
              <span className={`rounded px-1.5 py-0.5 text-[10px] ${
                selectedMaturity === 'native'
                  ? 'bg-ops-success/15 text-ops-success'
                  : selectedMaturity === 'needs_adapter'
                    ? 'bg-ops-alert/15 text-ops-alert'
                    : 'bg-ops-accent/15 text-ops-accent'
              }`}>
                {MATURITY_LABELS[selectedMaturity] || selectedMaturity}
              </span>
            </div>
            {accessProtocolOptions.length > 1 && (
              <div className="mt-3 grid gap-2 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <label className="mb-1 block text-[11px] text-ops-overlay">接入协议</label>
                  <select
                    value={currentProtocol}
                    onChange={(event) => onProtocolChange(event.target.value)}
                    className="ops-control w-full appearance-none px-2.5 py-1.5 text-xs"
                  >
                    {accessProtocolOptions.map((item) => (
                      <option key={`${item.protocol}-${item.purpose || 'operation'}`} value={item.protocol}>
                        {item.label || item.protocol.toUpperCase()}
                        {item.role === 'default' || item.is_default ? '（默认）' : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="rounded bg-ops-surface0/55 px-2.5 py-2 text-[11px] leading-5 text-ops-subtext">
                  {currentAccessProtocol?.description || '同一资产类型可按现场接入条件选择 SSH、API 等不同原生协议。'}
                </div>
              </div>
            )}
            {selectedConnectionHint && (
              <p className="mt-2 rounded-lg bg-ops-surface0/55 px-2.5 py-2 text-[11px] leading-5 text-ops-subtext">
                {selectedConnectionHint}
              </p>
            )}
            {displayTools.length > 0 && (
              <details className="ops-data-panel mt-2 px-2.5 py-2">
                <summary className="cursor-pointer text-[11px] font-semibold text-ops-subtext">
                  AI 可用工具 {displayTools.length} 个
                </summary>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {displayTools.map((tool) => (
                    <span
                      key={tool.name}
                      title={[tool.name, tool.description].filter(Boolean).join(' · ')}
                      className="ops-control px-1.5 py-0.5 text-[10px] text-ops-subtext"
                    >
                      {tool.label || toolLabel(tool.name)}
                    </span>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
