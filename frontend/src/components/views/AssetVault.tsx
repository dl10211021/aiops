import InspectionReportModal from '@/components/inspection/InspectionReportModal'
import PageHeader from '@/components/layout/PageHeader'
import { BatchImportAssetsDialog, DeleteAssetDialog, NormalizeAssetsDialog } from './AssetVaultDialogs'
import { AssetVaultFilterPanel, AssetVaultHeaderActions } from './AssetVaultFilterPanel'
import { VerificationPanel } from './AssetVerificationPanel'
import { AssetTablePanel } from './AssetVaultPageSections'
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
    categoryStats: catalogCategoryStats,
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
    deleteTarget,
    deletingAsset,
    handleBatchImportConfirmed,
    handleConnect,
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

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="w-full max-w-none pb-4">
        <PageHeader
          title="资产中心"
          description="资产、协议、凭据、标签、验证矩阵。"
          actions={(
            <AssetVaultHeaderActions
              onBatchImport={() => setBatchImportOpen(true)}
              onCreateAsset={openCreateAsset}
              onNormalize={handleNormalizeAssets}
            />
          )}
        />

        <AssetVaultFilterPanel
          assetCount={assets.length}
          assetTypeFilter={assetTypeFilter}
          assetTypeLabels={assetTypeLabels}
          availableAssetTypes={availableAssetTypes}
          availableCategoryOptions={availableCategoryOptions}
          availableConnectors={availableConnectors}
          categoryFilter={categoryFilter}
          categoryStats={catalogCategoryStats}
          catalogTypeCount={catalogTypes.length}
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
          onClearFilters={clearFilters}
          onConnect={handleConnect}
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

