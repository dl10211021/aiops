import type { AssetCategoryDefinition, AssetTypeDefinition } from '@/api/client'
import type { Asset, ProtocolVerificationStatusOverview } from '@/types'
import { protocolLabel } from '@/utils/assetDisplay'
import type { AssetDisplayMeta, FilterOption } from './AssetVaultParts'
import {
  CATEGORY_ORDER,
  CONNECTOR_FALLBACK_ORDER,
  assetTypeKey,
  connectorForType,
  normalizeFilterValue,
  orderIndex,
} from './assetVaultModel'

export type AssetVaultGroup = {
  id: string
  label: string
  group: string
  order: number
  items: Asset[]
}

type AssetVaultViewModelInput = {
  assets: Asset[]
  assetTypeFilter: string
  catalogCategories: AssetCategoryDefinition[]
  catalogConnectorGroups: Array<AssetCategoryDefinition & { tools?: string[] }>
  catalogTypes: AssetTypeDefinition[]
  categoryFilter: string
  categoryLabels: Record<string, string>
  connectorFilter: string
  search: string
  verificationOverview: ProtocolVerificationStatusOverview | null
}

export function buildAssetVaultViewModel({
  assets,
  assetTypeFilter,
  catalogCategories,
  catalogConnectorGroups,
  catalogTypes,
  categoryFilter,
  categoryLabels,
  connectorFilter,
  search,
  verificationOverview,
}: AssetVaultViewModelInput) {
  const catalogTypeById = new Map(catalogTypes.map((t) => [normalizeFilterValue(t.id), t]))
  const catalogCategoryById = new Map(catalogCategories.map((category) => [category.id, category]))
  const connectorOrder = new Map(catalogConnectorGroups.map((g, index) => [g.id, g.order ?? index]))
  const catalogTypeOrder = new Map(catalogTypes.map((t, index) => [normalizeFilterValue(t.id), index]))

  const assetTypeLabels = {
    ...Object.fromEntries(catalogTypes.map((t) => [t.id, t.label])),
    unknown: '未知',
  } as Record<string, string>
  const connectorLabels = {
    ...Object.fromEntries(catalogConnectorGroups.map((g) => [g.id, g.label])),
    unknown: '待适配',
  } as Record<string, string>

  const typeForAsset = (asset: Asset) =>
    catalogTypeById.get(normalizeFilterValue(asset.asset_type || asset.extra_args?.sub_type))
  const rawCategoryForAsset = (asset: Asset) =>
    normalizeFilterValue(asset.extra_args?.category || typeForAsset(asset)?.category, 'other')
  const rawConnectorForAsset = (asset: Asset) =>
    connectorForType(catalogTypeById, String(asset.asset_type || asset.extra_args?.sub_type || ''), asset.protocol || asset.asset_type)
  const assetMetaById = new Map(assets.map((asset) => {
    const category = rawCategoryForAsset(asset)
    const connector = rawConnectorForAsset(asset)
    const typeKey = assetTypeKey(asset)
    const protocol = normalizeFilterValue(asset.protocol || asset.asset_type)
    return [asset.id, {
      category,
      connector,
      protocol,
      searchText: [
        asset.host,
        asset.remark,
        asset.username,
        asset.asset_type,
        protocol,
        connectorLabels[connector] || connector,
      ].filter(Boolean).join('\n').toLowerCase(),
      typeKey,
    }]
  }))
  const metaForAsset = (asset: Asset) => assetMetaById.get(asset.id) || {
    category: rawCategoryForAsset(asset),
    connector: rawConnectorForAsset(asset),
    protocol: normalizeFilterValue(asset.protocol || asset.asset_type),
    searchText: '',
    typeKey: assetTypeKey(asset),
  }
  const categoryForAsset = (asset: Asset) => metaForAsset(asset).category
  const connectorForAsset = (asset: Asset) => metaForAsset(asset).connector
  const protocolLabelForAsset = (asset: Asset, connector: string) => {
    const category = categoryForAsset(asset)
    if (category === 'db' && connector === 'database_http') return '数据库 API'
    if (category === 'db' && connector === 'database_jdbc') return 'JDBC'
    return protocolLabel(asset.protocol || asset.asset_type)
  }
  const displayForAsset = (asset: Asset): AssetDisplayMeta => {
    const { category, connector, typeKey } = metaForAsset(asset)
    return {
      typeLabel: assetTypeLabels[typeKey] || asset.asset_type || '资产',
      categoryLabel: categoryLabels[category] || category.toUpperCase(),
      connectorLabel: connectorLabels[connector] || connector,
      protocolLabel: protocolLabelForAsset(asset, connector),
    }
  }

  const q = search.toLowerCase()
  const filtered = assets.filter((asset) => {
    const { category, connector, searchText, typeKey } = metaForAsset(asset)
    const matchesSearch = !q || searchText.includes(q)
    const matchesCategory = categoryFilter === 'all' || category === categoryFilter
    const matchesAssetType = assetTypeFilter === 'all' || typeKey === assetTypeFilter
    const matchesConnector = connectorFilter === 'all' || connector === connectorFilter
    return matchesSearch && matchesCategory && matchesAssetType && matchesConnector
  })

  const assetCategoryCounts = new Map<string, number>()
  const assetTypeKeysByCategory = new Map<string, Set<string>>()
  const assetConnectorsByCategoryAndType = new Map<string, Set<string>>()
  assets.forEach((asset) => {
    const { category, connector, typeKey } = metaForAsset(asset)
    assetCategoryCounts.set(category, (assetCategoryCounts.get(category) || 0) + 1)
    if (!assetTypeKeysByCategory.has(category)) assetTypeKeysByCategory.set(category, new Set())
    assetTypeKeysByCategory.get(category)?.add(typeKey)
    const connectorScope = `${category}\n${typeKey}`
    if (!assetConnectorsByCategoryAndType.has(connectorScope)) assetConnectorsByCategoryAndType.set(connectorScope, new Set())
    assetConnectorsByCategoryAndType.get(connectorScope)?.add(connector)
  })
  const catalogTypeCategoryCounts = new Map<string, number>()
  catalogTypes.forEach((type) => {
    catalogTypeCategoryCounts.set(type.category, (catalogTypeCategoryCounts.get(type.category) || 0) + 1)
  })

  const availableCategoryOptions = Array.from(new Set([
    ...catalogCategories.map((c) => c.id),
    ...assetCategoryCounts.keys(),
  ]))
    .filter(Boolean)
    .map((id): FilterOption => {
      const meta = catalogCategoryById.get(id)
      return {
        id,
        label: meta?.label || categoryLabels[id] || id.toUpperCase(),
        group: meta?.group || '其它',
        order: meta?.order ?? orderIndex(CATEGORY_ORDER, id),
        description: meta?.description,
      }
    })
    .sort((a, b) => (a.order ?? 999) - (b.order ?? 999) || a.label.localeCompare(b.label))

  const typeCategoryMatches = (type: AssetTypeDefinition) => categoryFilter === 'all' || type.category === categoryFilter
  const scopedCatalogTypes = catalogTypes.filter(typeCategoryMatches)
  const assetTypeKeys = categoryFilter === 'all'
    ? Array.from(new Set(Array.from(assetTypeKeysByCategory.values()).flatMap((items) => Array.from(items))))
    : Array.from(assetTypeKeysByCategory.get(categoryFilter) || [])

  const availableAssetTypes = Array.from(new Set([
    ...scopedCatalogTypes.map((t) => normalizeFilterValue(t.id)),
    ...assetTypeKeys,
  ]))
    .filter(Boolean)
    .sort((a, b) => (catalogTypeOrder.get(a) ?? catalogTypes.length) - (catalogTypeOrder.get(b) ?? catalogTypes.length) || a.localeCompare(b))

  const connectorMatchesSelectedType = (type: AssetTypeDefinition) =>
    assetTypeFilter === 'all' || normalizeFilterValue(type.id) === assetTypeFilter
  const assetConnectorKeys = Array.from(assetConnectorsByCategoryAndType.entries()).flatMap(([scope, connectors]) => {
    const [category, typeKey] = scope.split('\n')
    if (categoryFilter !== 'all' && category !== categoryFilter) return []
    if (assetTypeFilter !== 'all' && typeKey !== assetTypeFilter) return []
    return Array.from(connectors)
  })

  const availableConnectors = Array.from(new Set([
    ...scopedCatalogTypes.filter(connectorMatchesSelectedType).map((t) => normalizeFilterValue(t.capability?.connector)),
    ...assetConnectorKeys,
  ]))
    .filter(Boolean)
    .sort((a, b) => (connectorOrder.get(a) ?? orderIndex(CONNECTOR_FALLBACK_ORDER, a)) - (connectorOrder.get(b) ?? orderIndex(CONNECTOR_FALLBACK_ORDER, b)) || a.localeCompare(b))

  const matrixByAssetId = new Map((verificationOverview?.matrix || []).map((item) => [item.asset.id, item]))
  const categoryStats = availableCategoryOptions
    .filter((option) => option.id !== 'all')
    .map((option) => ({
      ...option,
      assetCount: assetCategoryCounts.get(option.id) || 0,
      typeCount: catalogTypeCategoryCounts.get(option.id) || 0,
    }))
    .filter((option) => option.typeCount > 0 || option.assetCount > 0)
    .sort((a, b) => (a.order ?? 999) - (b.order ?? 999) || a.label.localeCompare(b.label))

  const grouped = new Map<string, AssetVaultGroup>()
  filtered.forEach((asset) => {
    const category = categoryForAsset(asset)
    const meta = catalogCategoryById.get(category)
    const current = grouped.get(category)
    if (current) {
      current.items.push(asset)
    } else {
      grouped.set(category, {
        id: category,
        label: meta?.label || categoryLabels[category] || category.toUpperCase(),
        group: meta?.group || '其它',
        order: meta?.order ?? orderIndex(CATEGORY_ORDER, category),
        items: [asset],
      })
    }
  })

  const assetGroups = Array.from(grouped.values())
    .sort((a, b) => a.order - b.order || a.label.localeCompare(b.label))
  const connectorForAssetTypeFilter = (value: string) =>
    catalogTypeById.get(value)?.capability?.connector

  return {
    assetGroups,
    assetTypeLabels,
    availableAssetTypes,
    availableCategoryOptions,
    availableConnectors,
    categoryForAsset,
    categoryStats,
    connectorForAsset,
    connectorForAssetTypeFilter,
    connectorLabels,
    displayForAsset,
    filtered,
    hasActiveFilters: categoryFilter !== 'all' || assetTypeFilter !== 'all' || connectorFilter !== 'all' || Boolean(search),
    matrixByAssetId,
    protocolLabelForAsset,
  }
}
