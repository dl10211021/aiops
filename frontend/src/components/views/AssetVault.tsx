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
import { useStore } from '@/store'

export default function AssetVault() {
  const sessionGroups = useStore((s) => s.sessionGroups)
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
    bulkDeletingAssets,
    bulkVerifyingAssets,
    connectingAssetGroup,
    connectingSelectedAssets,
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

