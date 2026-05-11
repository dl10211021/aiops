import { useCallback, useEffect, useState } from 'react'
import {
  getAssetTypeSummary,
  getProtocolVerificationStatusOverview,
  getSavedAssets,
} from '@/api/assets'
import { useStore } from '@/store'
import type { Asset, AssetCategoryDefinition, AssetTypeDefinition, ProtocolVerificationStatusOverview } from '@/types'

const ASSET_LIST_CACHE_TTL_MS = 30_000
const ASSET_CATALOG_CACHE_TTL_MS = 5 * 60_000

type AssetCatalogCache = {
  catalogCategories: AssetCategoryDefinition[]
  catalogConnectorGroups: Array<AssetCategoryDefinition & { tools?: string[] }>
  catalogTypes: AssetTypeDefinition[]
  categoryLabels: Record<string, string>
}

let lastAssetListLoadedAt = 0
let lastVerificationOverviewRequestedAt = 0
let cachedVerificationOverview: ProtocolVerificationStatusOverview | null = null
let cachedAssetCatalog: { data: AssetCatalogCache; loadedAt: number } | null = null
let catalogLoadPromise: Promise<AssetCatalogCache> | null = null

function getCachedAssetCatalog() {
  if (!cachedAssetCatalog) return null
  if (Date.now() - cachedAssetCatalog.loadedAt > ASSET_CATALOG_CACHE_TTL_MS) return null
  return cachedAssetCatalog.data
}

async function loadAssetCatalog() {
  const cached = getCachedAssetCatalog()
  if (cached) return cached
  if (!catalogLoadPromise) {
    catalogLoadPromise = getAssetTypeSummary()
      .then((r) => {
        const categories = r.data.categories || []
        const data = {
          catalogCategories: categories,
          catalogConnectorGroups: r.data.connector_groups || [],
          catalogTypes: r.data.types || [],
          categoryLabels: {
            ...Object.fromEntries(categories.map((c) => [c.id, c.label])),
            other: '其他',
          },
        }
        cachedAssetCatalog = { data, loadedAt: Date.now() }
        return data
      })
      .finally(() => {
        catalogLoadPromise = null
      })
  }
  return catalogLoadPromise
}

type LoadAssetsOptions = {
  force?: boolean
}

export function useAssetVaultData() {
  const assets = useStore((s) => s.assets)
  const setAssets = useStore((s) => s.setAssets)
  const addToast = useStore((s) => s.addToast)
  const initialCatalog = getCachedAssetCatalog()
  const [categoryLabels, setCategoryLabels] = useState<Record<string, string>>(() => initialCatalog?.categoryLabels || {})
  const [catalogCategories, setCatalogCategories] = useState<AssetCategoryDefinition[]>(() => initialCatalog?.catalogCategories || [])
  const [catalogConnectorGroups, setCatalogConnectorGroups] = useState<Array<AssetCategoryDefinition & { tools?: string[] }>>(() => initialCatalog?.catalogConnectorGroups || [])
  const [catalogTypes, setCatalogTypes] = useState<AssetTypeDefinition[]>(() => initialCatalog?.catalogTypes || [])
  const [verificationOverview, setVerificationOverview] = useState<ProtocolVerificationStatusOverview | null>(() => cachedVerificationOverview)

  const refreshVerificationOverview = useCallback(async (clearOnError = false) => {
    lastVerificationOverviewRequestedAt = Date.now()
    try {
      const res = await getProtocolVerificationStatusOverview()
      cachedVerificationOverview = res.data
      setVerificationOverview(res.data)
    } catch {
      if (clearOnError) {
        cachedVerificationOverview = null
        setVerificationOverview(null)
      }
    }
  }, [])

  const loadAssets = useCallback(async (options: LoadAssetsOptions = {}) => {
    const force = options.force ?? true
    const hasFreshAssets = assets.length > 0 && Date.now() - lastAssetListLoadedAt < ASSET_LIST_CACHE_TTL_MS
    if (!force && hasFreshAssets) {
      if (Date.now() - lastVerificationOverviewRequestedAt > ASSET_LIST_CACHE_TTL_MS) {
        void refreshVerificationOverview(true)
      }
      return
    }
    try {
      const res = await getSavedAssets()
      lastAssetListLoadedAt = Date.now()
      setAssets((res.data.assets || []) as Asset[])
      void refreshVerificationOverview(true)
    } catch {
      addToast('加载资产列表失败', 'error')
    }
  }, [assets.length, setAssets, addToast, refreshVerificationOverview])

  useEffect(() => { void loadAssets({ force: false }) }, [loadAssets])
  useEffect(() => {
    let cancelled = false
    loadAssetCatalog()
      .then((catalog) => {
        if (cancelled) return
        setCatalogCategories(catalog.catalogCategories)
        setCatalogConnectorGroups(catalog.catalogConnectorGroups)
        setCatalogTypes(catalog.catalogTypes)
        setCategoryLabels(catalog.categoryLabels)
      })
      .catch(() => {
        if (cancelled) return
        setCatalogCategories([])
        setCatalogConnectorGroups([])
        setCatalogTypes([])
        setCategoryLabels({ other: '其他' })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return {
    assets,
    catalogCategories,
    catalogConnectorGroups,
    catalogTypes,
    categoryLabels,
    loadAssets,
    refreshVerificationOverview,
    setAssets,
    verificationOverview,
  }
}
