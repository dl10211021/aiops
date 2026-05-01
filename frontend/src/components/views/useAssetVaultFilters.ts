import { useEffect, useState } from 'react'
import { normalizeFilterValue } from './assetVaultModel'

export function useAssetVaultFilters() {
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [assetTypeFilter, setAssetTypeFilter] = useState('all')
  const [connectorFilter, setConnectorFilter] = useState('all')

  const handleCategoryFilterChange = (value: string) => {
    setCategoryFilter(value)
    setAssetTypeFilter('all')
    setConnectorFilter('all')
  }

  const handleAssetTypeFilterChange = (
    value: string,
    connectorForAssetTypeFilter: (assetType: string) => string | undefined,
  ) => {
    setAssetTypeFilter(value)
    if (value === 'all') {
      setConnectorFilter('all')
      return
    }
    const connector = connectorForAssetTypeFilter(value)
    setConnectorFilter(connector ? normalizeFilterValue(connector) : 'all')
  }

  const clearFilters = () => {
    setCategoryFilter('all')
    setAssetTypeFilter('all')
    setConnectorFilter('all')
    setSearch('')
  }

  return {
    assetTypeFilter,
    categoryFilter,
    clearFilters,
    connectorFilter,
    handleAssetTypeFilterChange,
    handleCategoryFilterChange,
    search,
    setAssetTypeFilter,
    setCategoryFilter,
    setConnectorFilter,
    setSearch,
  }
}

export function useAssetVaultFilterValidation({
  assetTypeFilter,
  availableAssetTypes,
  availableCategoryOptions,
  availableConnectors,
  categoryFilter,
  connectorFilter,
  setAssetTypeFilter,
  setCategoryFilter,
  setConnectorFilter,
}: {
  assetTypeFilter: string
  availableAssetTypes: string[]
  availableCategoryOptions: Array<{ id: string }>
  availableConnectors: string[]
  categoryFilter: string
  connectorFilter: string
  setAssetTypeFilter: (value: string) => void
  setCategoryFilter: (value: string) => void
  setConnectorFilter: (value: string) => void
}) {
  useEffect(() => {
    if (categoryFilter !== 'all' && availableCategoryOptions.length > 0 && !availableCategoryOptions.some((option) => option.id === categoryFilter)) {
      setCategoryFilter('all')
      setAssetTypeFilter('all')
      setConnectorFilter('all')
    }
  }, [availableCategoryOptions, categoryFilter])

  useEffect(() => {
    if (assetTypeFilter !== 'all' && availableAssetTypes.length > 0 && !availableAssetTypes.includes(assetTypeFilter)) {
      setAssetTypeFilter('all')
      setConnectorFilter('all')
    }
  }, [availableAssetTypes, assetTypeFilter])

  useEffect(() => {
    if (connectorFilter !== 'all' && availableConnectors.length > 0 && !availableConnectors.includes(connectorFilter)) {
      setConnectorFilter('all')
    }
  }, [availableConnectors, connectorFilter])
}
