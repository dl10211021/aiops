import InspectionReportModal from '@/components/inspection/InspectionReportModal'
import PageHeader from '@/components/layout/PageHeader'
import { AssetEmptyState } from './AssetVaultCards'
import { DeleteAssetDialog, NormalizeAssetsDialog } from './AssetVaultDialogs'
import { AssetVaultFilterPanel, AssetVaultHeaderActions } from './AssetVaultFilterPanel'
import { VerificationPanel } from './AssetVerificationPanel'
import { AssetGroupSections, AssetOverviewGrid } from './AssetVaultPageSections'
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
    overview,
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
    assetGroups,
    assetTypeLabels,
    availableAssetTypes,
    availableCategoryOptions,
    availableConnectors,
    categoryForAsset,
    categoryStats: catalogCategoryStats,
    connectorForAsset,
    connectorForAssetTypeFilter,
    connectorLabels,
    displayForAsset,
    filtered,
    hasActiveFilters,
    matrixByAssetId,
    protocolLabelForAsset,
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
    deleteTarget,
    deletingAsset,
    handleConnect,
    handleDeleteConfirmed,
    handleNormalizeAssets,
    handleNormalizeConfirmed,
    normalizeDialog,
    normalizingAssets,
    openCreateAsset,
    openVerification,
    reportRunId,
    runVerification,
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
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          eyebrow="数据中心资产台账"
          title="资产中心"
          description="统一管理资产凭据、连接方式、巡检入口和 AI 会话上下文"
          actions={(
            <AssetVaultHeaderActions
              search={search}
              onCreateAsset={openCreateAsset}
              onNormalize={handleNormalizeAssets}
              onRefresh={loadAssets}
              onSearchChange={setSearch}
            />
          )}
        />

        <AssetOverviewGrid overview={overview} verificationOverview={verificationOverview} />

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

        <AssetGroupSections
          assetGroups={assetGroups}
          assetTypeLabels={assetTypeLabels}
          categoryForAsset={categoryForAsset}
          categoryLabels={categoryLabels}
          connectorForAsset={connectorForAsset}
          connectorLabels={connectorLabels}
          matrixByAssetId={matrixByAssetId}
          protocolLabelForAsset={protocolLabelForAsset}
          onConnect={handleConnect}
          onDelete={setDeleteTarget}
          onOpenVerification={(item) => void openVerification(item)}
        />

        {filtered.length === 0 && (
          <AssetEmptyState
            assetCount={assets.length}
            hasActiveFilters={hasActiveFilters}
            onClearFilters={clearFilters}
            onCreateAsset={openCreateAsset}
          />
        )}
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

