import { useState } from 'react'
import {
  applyAssetNormalization,
  batchImportAssets,
  deleteAsset,
  getAssetVerificationMatrix,
  getAssetVerificationRuns,
  listInspectionRuns,
  previewAssetNormalization,
  verifyAsset,
} from '@/api/client'
import { useStore } from '@/store'
import type { Asset, AssetVerificationMatrix, AssetVerificationRun, InspectionRun } from '@/types'
import { statusLabel } from '@/utils/assetDisplay'
import type { AssetDisplayMeta } from './AssetVaultParts'

type VerificationPanelState = {
  asset: Asset
  display: AssetDisplayMeta
  matrix: AssetVerificationMatrix | null
  runs: AssetVerificationRun[]
  inspectionRuns: InspectionRun[]
  loading: boolean
  running: boolean
}

type UseAssetVaultActionsArgs = {
  assets: Asset[]
  displayForAsset: (asset: Asset) => AssetDisplayMeta
  loadAssets: () => Promise<void>
  refreshVerificationOverview: () => Promise<void>
  setAssets: (assets: Asset[]) => void
}

export function useAssetVaultActions({
  assets,
  displayForAsset,
  loadAssets,
  refreshVerificationOverview,
  setAssets,
}: UseAssetVaultActionsArgs) {
  const openModal = useStore((s) => s.openModal)
  const addToast = useStore((s) => s.addToast)
  const [verificationPanel, setVerificationPanel] = useState<VerificationPanelState | null>(null)
  const [reportRunId, setReportRunId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Asset | null>(null)
  const [deletingAsset, setDeletingAsset] = useState(false)
  const [batchImportOpen, setBatchImportOpen] = useState(false)
  const [batchImportDraft, setBatchImportDraft] = useState('[\n  {\n    "remark": "Oracle TEST",\n    "host": "172.17.1.207",\n    "port": 1561,\n    "username": "system",\n    "asset_type": "oracle",\n    "protocol": "oracle",\n    "tags": ["数据库"]\n  }\n]')
  const [importingAssets, setImportingAssets] = useState(false)
  const [normalizeDialog, setNormalizeDialog] = useState<{ rowsToUpdate: number; duplicatesToRemove: number } | null>(null)
  const [normalizingAssets, setNormalizingAssets] = useState(false)
  const [bulkVerifyingAssets, setBulkVerifyingAssets] = useState(false)

  const openCreateAsset = () => {
    sessionStorage.removeItem('asset_editing_id')
    openModal('connect')
  }

  const handleDeleteConfirmed = async () => {
    if (!deleteTarget) return
    setDeletingAsset(true)
    try {
      await deleteAsset(deleteTarget.id)
      setAssets(assets.filter((asset) => asset.id !== deleteTarget.id))
      setDeleteTarget(null)
      addToast('资产已移除', 'success')
    } catch {
      addToast('删除失败', 'error')
    } finally {
      setDeletingAsset(false)
    }
  }

  const handleConnect = (asset: Asset) => {
    sessionStorage.removeItem('asset_editing_id')
    sessionStorage.setItem('prefill_asset', JSON.stringify(asset))
    openModal('connect')
  }

  const handleEditAsset = (asset: Asset) => {
    sessionStorage.setItem('asset_editing_id', String(asset.id))
    sessionStorage.setItem('prefill_asset', JSON.stringify(asset))
    openModal('connect')
  }

  const handleNormalizeAssets = async () => {
    try {
      const preview = await previewAssetNormalization()
      const summary = preview.data.summary
      const totalIssues = summary.rows_to_update + summary.duplicates_to_remove
      if (totalIssues <= 0) {
        addToast('资产数据无需规范化', 'success')
        return
      }
      setNormalizeDialog({
        rowsToUpdate: summary.rows_to_update,
        duplicatesToRemove: summary.duplicates_to_remove,
      })
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '资产规范化预检查失败', 'error')
    }
  }

  const handleNormalizeConfirmed = async () => {
    setNormalizingAssets(true)
    try {
      const res = await applyAssetNormalization()
      addToast(`资产规范化完成，删除重复 ${res.data.removed_ids.length} 条`, 'success')
      setNormalizeDialog(null)
      await loadAssets()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '资产规范化失败', 'error')
    } finally {
      setNormalizingAssets(false)
    }
  }

  const handleBatchImportConfirmed = async () => {
    setImportingAssets(true)
    try {
      const parsed = JSON.parse(batchImportDraft) as unknown
      if (!Array.isArray(parsed)) {
        addToast('导入内容必须是 JSON 数组', 'error')
        return
      }
      await batchImportAssets(parsed as Partial<Asset>[])
      setBatchImportOpen(false)
      addToast(`资产导入完成：${parsed.length} 条`, 'success')
      await loadAssets()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '资产导入失败', 'error')
    } finally {
      setImportingAssets(false)
    }
  }

  const openVerification = async (asset: Asset) => {
    const display = displayForAsset(asset)
    setVerificationPanel({ asset, display, matrix: null, runs: [], inspectionRuns: [], loading: true, running: false })
    try {
      const [matrixRes, runsRes, inspectionRunsRes] = await Promise.all([
        getAssetVerificationMatrix(asset.id),
        getAssetVerificationRuns(asset.id, 10),
        listInspectionRuns({ assetId: asset.id, limit: 8 }),
      ])
      setVerificationPanel({
        asset,
        display,
        matrix: matrixRes.data.matrix,
        runs: runsRes.data.runs || [],
        inspectionRuns: inspectionRunsRes.data.runs || [],
        loading: false,
        running: false,
      })
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '加载验证矩阵失败', 'error')
      setVerificationPanel((current) => current ? { ...current, loading: false } : current)
    }
  }

  const runVerification = async () => {
    if (!verificationPanel) return
    const asset = verificationPanel.asset
    setVerificationPanel({ ...verificationPanel, running: true })
    try {
      const res = await verifyAsset(asset.id)
      const runs = await getAssetVerificationRuns(asset.id, 10)
      setVerificationPanel((current) => current ? {
        ...current,
        runs: runs.data.runs || [res.data.run],
        running: false,
      } : current)
      void refreshVerificationOverview()
      addToast(`资产验证完成：${statusLabel(res.data.run.status)}`, res.data.run.status === 'success' ? 'success' : 'error')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '资产验证失败', 'error')
      setVerificationPanel((current) => current ? { ...current, running: false } : current)
    }
  }

  const handleBulkVerifyAssets = async (selectedAssets: Asset[]) => {
    if (!selectedAssets.length) {
      addToast('请先选择要验证的资产', 'error')
      return
    }
    setBulkVerifyingAssets(true)
    let successCount = 0
    let reviewCount = 0
    try {
      for (const asset of selectedAssets) {
        try {
          const res = await verifyAsset(asset.id)
          if (res.data.run.status === 'success') {
            successCount += 1
          } else {
            reviewCount += 1
          }
        } catch {
          reviewCount += 1
        }
      }
      await refreshVerificationOverview()
      addToast(
        `批量验证完成：成功 ${successCount} 条，需复核 ${reviewCount} 条`,
        reviewCount > 0 ? 'error' : 'success'
      )
    } finally {
      setBulkVerifyingAssets(false)
    }
  }

  return {
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
    setBatchImportDraft,
    setBatchImportOpen,
    openVerification,
    reportRunId,
    runVerification,
    setDeleteTarget,
    setNormalizeDialog,
    setReportRunId,
    setVerificationPanel,
    verificationPanel,
  }
}
