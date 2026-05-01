import { useCallback, useEffect, useState } from 'react'
import {
  type AssetCategoryDefinition,
  type AssetTypeDefinition,
  getAssetTypes,
  getDashboardOverview,
  getProtocolVerificationOverview,
  getSavedAssets,
} from '@/api/client'
import { useStore } from '@/store'
import type { Asset, ProtocolVerificationOverview } from '@/types'

export function useAssetVaultData() {
  const assets = useStore((s) => s.assets)
  const setAssets = useStore((s) => s.setAssets)
  const addToast = useStore((s) => s.addToast)
  const [categoryLabels, setCategoryLabels] = useState<Record<string, string>>({})
  const [catalogCategories, setCatalogCategories] = useState<AssetCategoryDefinition[]>([])
  const [catalogConnectorGroups, setCatalogConnectorGroups] = useState<Array<AssetCategoryDefinition & { tools?: string[] }>>([])
  const [catalogTypes, setCatalogTypes] = useState<AssetTypeDefinition[]>([])
  const [overview, setOverview] = useState<Record<string, number> | null>(null)
  const [verificationOverview, setVerificationOverview] = useState<ProtocolVerificationOverview | null>(null)

  const refreshVerificationOverview = useCallback(async (clearOnError = false) => {
    try {
      const res = await getProtocolVerificationOverview()
      setVerificationOverview(res.data)
    } catch {
      if (clearOnError) setVerificationOverview(null)
    }
  }, [])

  const loadAssets = useCallback(async () => {
    try {
      const res = await getSavedAssets()
      setAssets((res.data.assets || []) as Asset[])
      void getDashboardOverview().then((r) => setOverview(r.data.summary)).catch(() => setOverview(null))
      void refreshVerificationOverview(true)
    } catch {
      addToast('加载资产列表失败', 'error')
    }
  }, [setAssets, addToast, refreshVerificationOverview])

  useEffect(() => { void loadAssets() }, [loadAssets])
  useEffect(() => {
    getAssetTypes()
      .then((r) => {
        const categories = r.data.categories || []
        setCatalogCategories(categories)
        setCatalogConnectorGroups(r.data.connector_groups || [])
        setCatalogTypes(r.data.types || [])
        setCategoryLabels({
          ...Object.fromEntries(categories.map((c) => [c.id, c.label])),
          other: '其他',
        })
      })
      .catch(() => {
        setCatalogCategories([])
        setCatalogConnectorGroups([])
        setCatalogTypes([])
        setCategoryLabels({ other: '其他' })
      })
  }, [])

  return {
    assets,
    catalogCategories,
    catalogConnectorGroups,
    catalogTypes,
    categoryLabels,
    loadAssets,
    overview,
    refreshVerificationOverview,
    setAssets,
    verificationOverview,
  }
}
