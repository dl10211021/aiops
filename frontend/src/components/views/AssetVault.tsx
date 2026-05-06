import InspectionReportModal from '@/components/inspection/InspectionReportModal'
import PageHeader from '@/components/layout/PageHeader'
import { BatchImportAssetsDialog, DeleteAssetDialog, NormalizeAssetsDialog } from './AssetVaultDialogs'
import { AssetVaultFilterPanel, AssetVaultHeaderActions } from './AssetVaultFilterPanel'
import { VerificationPanel } from './AssetVerificationPanel'
import { AssetEnterpriseCommandPanel, AssetTablePanel } from './AssetVaultPageSections'
import { buildAssetVaultViewModel } from './assetVaultViewModel'
import { useAssetVaultActions } from './useAssetVaultActions'
import { useAssetVaultData } from './useAssetVaultData'
import { useAssetVaultFilterValidation, useAssetVaultFilters } from './useAssetVaultFilters'

export default function AssetVault() {
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
  } = buildAssetVaultViewModel({
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
  })

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
    bulkVerifyingAssets,
    deleteTarget,
    deletingAsset,
    handleBatchImportConfirmed,
    handleBulkVerifyAssets,
    handleConnect,
    handleEditAsset,
    handleDeleteConfirmed,
    handleNormalizeAssets,
    handleNormalizeConfirmed,
    importingAssets,
    normalizeDialog,
    normalizingAssets,
    openCreateAsset,
    openVerification,
    reportRunId,
    runVerification,
    setBatchImportDraft,
    setBatchImportOpen,
    setDeleteTarget,
    setNormalizeDialog,
    setReportRunId,
    setVerificationPanel,
    verificationPanel,
  } = useAssetVaultActions({
    assets,
    displayForAsset,
    loadAssets,
    refreshVerificationOverview,
    setAssets,
  })

  const readyCount = verificationOverview?.summary.ready_assets || 0

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="w-full max-w-none pb-4">
        <PageHeader
          title="资产中心"
          description="企业级资产台账：统一维护数据中心系统、数据库、网络、存储、虚拟化和平台类资产。"
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
          bulkVerifying={bulkVerifyingAssets}
          onClearFilters={clearFilters}
          onBulkVerify={(selectedAssets) => void handleBulkVerifyAssets(selectedAssets)}
          onConnect={handleConnect}
          onEdit={handleEditAsset}
          onDelete={setDeleteTarget}
          onOpenVerification={(item) => void openVerification(item)}
          onRefresh={() => void loadAssets()}
          onSearchChange={setSearch}
          search={search}
        />
      </div>
      {verificationPanel && (
        <VerificationPanel
          panel={verificationPanel}
          onClose={() => setVerificationPanel(null)}
          onRun={() => void runVerification()}
          onOpenInspectionReport={(runId) => setReportRunId(runId)}
        />
      )}
      {reportRunId && <InspectionReportModal runId={reportRunId} onClose={() => setReportRunId(null)} />}
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
    </div>
  )
}

