import PageHeader from '@/components/layout/PageHeader'
import { lazy, Suspense, useDeferredValue, useEffect, useMemo, useState } from 'react'
import { getAssetTypeFormCatalog } from '@/api/assets'
import type { AssetTypeDefinition } from '@/types'
import { AssetVaultFilterPanel, AssetVaultHeaderActions } from './AssetVaultFilterPanel'
import { AssetEnterpriseCommandPanel, AssetTablePanel } from './AssetVaultPageSections'
import { buildAssetVaultViewModel } from './assetVaultViewModel'
import { useAssetVaultActions } from './useAssetVaultActions'
import { useAssetVaultData } from './useAssetVaultData'
import { useAssetVaultFilterValidation, useAssetVaultFilters } from './useAssetVaultFilters'
import { useStore } from '@/store'

const InspectionReportModal = lazy(() => import('@/components/inspection/InspectionReportModal'))
const AssetVaultEditorDrawer = lazy(() => import('./AssetVaultEditorDrawer').then((module) => ({ default: module.AssetVaultEditorDrawer })))
const VerificationPanel = lazy(() => import('./AssetVerificationPanel').then((module) => ({ default: module.VerificationPanel })))
const BatchImportAssetsDialog = lazy(() => import('./AssetVaultDialogs').then((module) => ({ default: module.BatchImportAssetsDialog })))
const DeleteAssetDialog = lazy(() => import('./AssetVaultDialogs').then((module) => ({ default: module.DeleteAssetDialog })))
const NormalizeAssetsDialog = lazy(() => import('./AssetVaultDialogs').then((module) => ({ default: module.NormalizeAssetsDialog })))

function AssetModalFallback() {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 text-sm text-ops-subtext">
      加载中...
    </div>
  )
}

export default function AssetVault() {
  const sessionGroups = useStore((s) => s.sessionGroups)
  const [fullCatalogTypes, setFullCatalogTypes] = useState<AssetTypeDefinition[] | null>(null)
  const {
    assets,
    catalogCategories,
    catalogConnectorGroups,
    catalogTypes,
    categoryLabels,
    loadAssets,
    refreshVerificationOverview,
    setAssets,
    verificationOverview,
  } = useAssetVaultData()

  const {
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
  } = useAssetVaultFilters()
  const deferredSearch = useDeferredValue(search)

  const {
    assetTypeLabels,
    availableAssetTypes,
    availableCategoryOptions,
    availableConnectors,
    connectorForAssetTypeFilter,
    connectorLabels,
    displayForAsset,
    filtered,
    hasActiveFilters,
    matrixByAssetId,
  } = useMemo(() => buildAssetVaultViewModel({
    assets,
    assetTypeFilter,
    catalogCategories,
    catalogConnectorGroups,
    catalogTypes,
    categoryFilter,
    categoryLabels,
    connectorFilter,
    search: deferredSearch,
    verificationOverview,
  }), [
    assets,
    assetTypeFilter,
    catalogCategories,
    catalogConnectorGroups,
    catalogTypes,
    categoryFilter,
    categoryLabels,
    connectorFilter,
    deferredSearch,
    verificationOverview,
  ])

  useAssetVaultFilterValidation({
    assetTypeFilter,
    availableAssetTypes,
    availableCategoryOptions,
    availableConnectors,
    categoryFilter,
    connectorFilter,
    setAssetTypeFilter,
    setCategoryFilter,
    setConnectorFilter,
  })

  const {
    batchImportDraft,
    batchImportOpen,
    bulkDeletingAssets,
    bulkVerifyingAssets,
    connectingAssetGroup,
    connectingSelectedAssets,
    editTarget,
    mutatingAssetGroup,
    deleteTarget,
    deletingAsset,
    handleAssignAssetsToGroup,
    handleBatchImportConfirmed,
    handleBulkDeleteAssets,
    handleBulkVerifyAssets,
    handleConnect,
    handleConnectAssetGroup,
    handleConnectSelectedAssets,
    handleCreateAssetGroup,
    handleDeleteAssetGroup,
    handleEditAsset,
    handleSaveAsset,
    handleDeleteConfirmed,
    handleNormalizeAssets,
    handleNormalizeConfirmed,
    handleRenameAssetGroup,
    importingAssets,
    normalizeDialog,
    normalizingAssets,
    openCreateAsset,
    openVerification,
    reportRunId,
    runVerification,
    setBatchImportDraft,
    setBatchImportOpen,
    setEditTarget,
    setDeleteTarget,
    setNormalizeDialog,
    setReportRunId,
    setVerificationPanel,
    savingAsset,
    verificationPanel,
  } = useAssetVaultActions({
    assets,
    displayForAsset,
    loadAssets,
    refreshVerificationOverview,
    setAssets,
  })

  const readyCount = verificationOverview?.summary.ready_assets || 0

  useEffect(() => {
    if (!editTarget || fullCatalogTypes) return
    let cancelled = false
    getAssetTypeFormCatalog()
      .then((response) => {
        if (!cancelled) setFullCatalogTypes(response.data.types || [])
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [editTarget, fullCatalogTypes])

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          title="资产台账"
          description="统一维护数据中心系统、数据库、网络、存储、虚拟化和平台类资产。"
          actions={(
            <AssetVaultHeaderActions
              onBatchImport={() => setBatchImportOpen(true)}
              onCreateAsset={openCreateAsset}
              onNormalize={handleNormalizeAssets}
            />
          )}
        />

        <AssetEnterpriseCommandPanel
          assetCount={assets.length}
          catalogTypeCount={catalogTypes.length}
          filteredCount={filtered.length}
          readyCount={readyCount}
        />

        <AssetVaultFilterPanel
          assetTypeFilter={assetTypeFilter}
          assetTypeLabels={assetTypeLabels}
          availableAssetTypes={availableAssetTypes}
          availableCategoryOptions={availableCategoryOptions}
          availableConnectors={availableConnectors}
          categoryFilter={categoryFilter}
          connectorFilter={connectorFilter}
          connectorLabels={connectorLabels}
          hasActiveFilters={hasActiveFilters}
          onAssetTypeChange={(value) => handleAssetTypeFilterChange(value, connectorForAssetTypeFilter)}
          onCategoryChange={handleCategoryFilterChange}
          onClearFilters={clearFilters}
          onConnectorChange={setConnectorFilter}
        />

        <AssetTablePanel
          assets={filtered}
          displayForAsset={displayForAsset}
          hasActiveFilters={hasActiveFilters}
          matrixByAssetId={matrixByAssetId}
          bulkDeleting={bulkDeletingAssets}
          bulkVerifying={bulkVerifyingAssets}
          connectingGroup={connectingAssetGroup}
          connectingSelected={connectingSelectedAssets}
          mutatingGroup={mutatingAssetGroup}
          sessionGroups={sessionGroups}
          onClearFilters={clearFilters}
          onAssignGroup={(selectedAssets, groupName) => void handleAssignAssetsToGroup(selectedAssets, groupName)}
          onBulkDelete={(selectedAssets) => void handleBulkDeleteAssets(selectedAssets)}
          onBulkVerify={(selectedAssets) => void handleBulkVerifyAssets(selectedAssets)}
          onConnect={handleConnect}
          onConnectGroup={(groupAssets, groupName) => void handleConnectAssetGroup(groupAssets, groupName)}
          onConnectSelected={(selectedAssets) => void handleConnectSelectedAssets(selectedAssets)}
          onCreateGroup={handleCreateAssetGroup}
          onDeleteGroup={(groupName) => void handleDeleteAssetGroup(groupName)}
          onEdit={handleEditAsset}
          onDelete={setDeleteTarget}
          onOpenVerification={(item) => void openVerification(item)}
          onRenameGroup={(groupName, nextGroupName) => void handleRenameAssetGroup(groupName, nextGroupName)}
          onRefresh={() => void loadAssets()}
          onSearchChange={setSearch}
          search={search}
        />
      </div>
      <Suspense fallback={<AssetModalFallback />}>
        {verificationPanel && (
          <VerificationPanel
            panel={verificationPanel}
            onClose={() => setVerificationPanel(null)}
            onRun={() => void runVerification()}
            onOpenInspectionReport={(runId) => setReportRunId(runId)}
          />
        )}
        {reportRunId && <InspectionReportModal runId={reportRunId} onClose={() => setReportRunId(null)} />}
        {editTarget && (
          <AssetVaultEditorDrawer
            asset={editTarget}
            catalogTypes={fullCatalogTypes || catalogTypes}
            display={displayForAsset(editTarget)}
            saving={savingAsset}
            sessionGroups={sessionGroups}
            onClose={() => setEditTarget(null)}
            onConnect={(asset) => {
              setEditTarget(null)
              handleConnect(asset)
            }}
            onOpenVerification={(asset) => {
              setEditTarget(null)
              void openVerification(asset)
            }}
            onSave={(asset, patch) => void handleSaveAsset(asset, patch)}
          />
        )}
        {batchImportOpen && (
          <BatchImportAssetsDialog
            draft={batchImportDraft}
            importing={importingAssets}
            onCancel={() => setBatchImportOpen(false)}
            onChange={setBatchImportDraft}
            onConfirm={() => void handleBatchImportConfirmed()}
          />
        )}
        {deleteTarget && (
          <DeleteAssetDialog
            asset={deleteTarget}
            deleting={deletingAsset}
            display={displayForAsset(deleteTarget)}
            onCancel={() => setDeleteTarget(null)}
            onConfirm={() => void handleDeleteConfirmed()}
          />
        )}
        {normalizeDialog && (
          <NormalizeAssetsDialog
            duplicatesToRemove={normalizeDialog.duplicatesToRemove}
            normalizing={normalizingAssets}
            rowsToUpdate={normalizeDialog.rowsToUpdate}
            onCancel={() => setNormalizeDialog(null)}
            onConfirm={() => void handleNormalizeConfirmed()}
          />
        )}
      </Suspense>
    </div>
  )
}

