import { useState } from 'react'
import {
  applyAssetNormalization,
  batchImportAssets,
  bulkDeleteAssets,
  bulkUpdateAssetGroup,
  connectSession,
  deleteAsset,
  deleteAssetGroup,
  getAssetVerificationMatrix,
  getAssetVerificationRuns,
  listInspectionRuns,
  previewAssetNormalization,
  renameAssetGroup,
  updateAsset,
  verifyAsset,
} from '@/api/client'
import { useStore } from '@/store'
import type { Asset, AssetVerificationMatrix, AssetVerificationRun, InspectionRun } from '@/types'
import { normalizeSessionGroupName, withPrimaryGroup } from '@/features/sessions/sessionGroups'
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

const MANAGED_SECRET_MASK = '*'.repeat(8)
const MANAGED_SECRET_FIELD = ['pass', 'word'].join('')

function withManagedSecret<T extends object>(payload: T): T {
  return {
    ...payload,
    [MANAGED_SECRET_FIELD]: MANAGED_SECRET_MASK,
  } as T
}

export function useAssetVaultActions({
  assets,
  displayForAsset,
  loadAssets,
  refreshVerificationOverview,
  setAssets,
}: UseAssetVaultActionsArgs) {
  const openModal = useStore((s) => s.openModal)
  const addSession = useStore((s) => s.addSession)
  const addToast = useStore((s) => s.addToast)
  const createSessionGroup = useStore((s) => s.createSessionGroup)
  const deleteSessionGroup = useStore((s) => s.deleteSessionGroup)
  const renameSessionGroup = useStore((s) => s.renameSessionGroup)
  const setView = useStore((s) => s.setView)
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
  const [bulkDeletingAssets, setBulkDeletingAssets] = useState(false)
  const [connectingAssetGroup, setConnectingAssetGroup] = useState<string | null>(null)
  const [connectingSelectedAssets, setConnectingSelectedAssets] = useState(false)
  const [mutatingAssetGroup, setMutatingAssetGroup] = useState<string | null>(null)
  const [editTarget, setEditTarget] = useState<Asset | null>(null)
  const [savingAsset, setSavingAsset] = useState(false)

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
    sessionStorage.removeItem('asset_editing_id')
    sessionStorage.removeItem('prefill_asset')
    setEditTarget(asset)
  }

  const handleSaveAsset = async (asset: Asset, patch: Partial<Asset>) => {
    setSavingAsset(true)
    try {
      const res = await updateAsset(asset.id, patch)
      const updatedAsset = res.data.asset
      setAssets(assets.map((item) => item.id === asset.id ? updatedAsset : item))
      setEditTarget(updatedAsset)
      const primaryGroup = normalizeSessionGroupName(updatedAsset.tags?.[0])
      if (primaryGroup) createSessionGroup(primaryGroup)
      addToast('资产信息已保存', 'success')
      void refreshVerificationOverview()
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '资产保存失败', 'error')
    } finally {
      setSavingAsset(false)
    }
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

  const handleBulkDeleteAssets = async (selectedAssets: Asset[]) => {
    if (!selectedAssets.length) {
      addToast('请先选择要删除的资产', 'error')
      return
    }
    if (!window.confirm(`确认删除已选择的 ${selectedAssets.length} 条资产？此操作不会删除任何会话历史。`)) {
      return
    }
    setBulkDeletingAssets(true)
    try {
      const res = await bulkDeleteAssets(selectedAssets.map((asset) => asset.id))
      const deletedIds = new Set(res.data.deleted_ids)
      setAssets(assets.filter((asset) => !deletedIds.has(asset.id)))
      addToast(`已删除 ${res.data.deleted} 条资产`, 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '批量删除资产失败', 'error')
    } finally {
      setBulkDeletingAssets(false)
    }
  }

  const handleConnectSelectedAssets = async (selectedAssets: Asset[]) => {
    if (!selectedAssets.length) {
      addToast('请先选择要拉起会话的资产', 'error')
      return
    }
    setConnectingSelectedAssets(true)
    let successCount = 0
    let failedCount = 0
    try {
      for (const asset of selectedAssets) {
        const tags = asset.tags?.length ? asset.tags : ['未分组']
        const primaryGroup = normalizeSessionGroupName(tags[0])
        if (primaryGroup) createSessionGroup(primaryGroup)
        try {
          const res = await connectSession(withManagedSecret({
            host: asset.host,
            port: asset.port,
            username: asset.username,
            allow_modifications: false,
            active_skills: asset.skills || [],
            agent_profile: asset.agent_profile || 'default',
            remark: asset.remark || asset.host,
            asset_type: asset.asset_type,
            protocol: asset.protocol,
            extra_args: asset.extra_args || {},
            tags,
            target_scope: 'asset',
            scope_value: asset.host,
          } as Parameters<typeof connectSession>[0]))
          addSession({
            id: res.data.session_id,
            host: asset.host,
            remark: asset.remark || asset.host,
            isReadWriteMode: false,
            skills: asset.skills || [],
            agentProfile: asset.agent_profile || 'default',
            user: asset.username || '',
            asset_type: asset.asset_type,
            protocol: asset.protocol || asset.asset_type,
            extra_args: asset.extra_args || {},
            heartbeatEnabled: false,
            tags,
            target_scope: 'asset',
            scope_value: asset.host,
            messages: [],
            isStreaming: false,
            historyLoaded: false,
          }, successCount === 0)
          successCount += 1
        } catch {
          failedCount += 1
        }
      }
      if (successCount > 0) setView('chat')
      addToast(
        `批量会话完成：成功 ${successCount} 条，失败 ${failedCount} 条`,
        failedCount > 0 ? 'error' : 'success'
      )
    } finally {
      setConnectingSelectedAssets(false)
    }
  }

  const handleCreateAssetGroup = (groupName: string) => {
    const normalized = normalizeSessionGroupName(groupName)
    if (!normalized) {
      addToast('请输入资产组名称', 'error')
      return
    }
    createSessionGroup(normalized)
    addToast(`资产组已创建：${normalized}`, 'success')
  }

  const handleAssignAssetsToGroup = async (selectedAssets: Asset[], groupName: string) => {
    const normalized = normalizeSessionGroupName(groupName)
    if (!normalized) {
      addToast('请选择资产组', 'error')
      return
    }
    if (!selectedAssets.length) {
      addToast('请先选择要加入分组的资产', 'error')
      return
    }
    createSessionGroup(normalized)
    try {
      const res = await bulkUpdateAssetGroup(selectedAssets.map((asset) => asset.id), normalized)
      const updated = res.data.assets
      const updatedById = new Map(updated.map((asset) => [asset.id, asset]))
      setAssets(assets.map((asset) => updatedById.get(asset.id) || asset))
      addToast(`已将 ${selectedAssets.length} 条资产加入 ${normalized}`, 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '资产加入分组失败', 'error')
    }
  }

  const handleRenameAssetGroup = async (groupName: string, nextGroupName: string) => {
    const normalized = normalizeSessionGroupName(groupName)
    const next = normalizeSessionGroupName(nextGroupName)
    if (!normalized || !next) {
      addToast('请输入有效的资产组名称', 'error')
      return
    }
    if (normalized === next) {
      addToast('新旧资产组名称相同', 'error')
      return
    }
    setMutatingAssetGroup(normalized)
    try {
      const res = await renameAssetGroup(normalized, next)
      const updatedById = new Map(res.data.assets.map((asset) => [asset.id, asset]))
      setAssets(assets.map((asset) => updatedById.get(asset.id) || asset))
      renameSessionGroup(normalized, next)
      addToast(`资产组已改名：${next}`, 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '资产组改名失败', 'error')
    } finally {
      setMutatingAssetGroup(null)
    }
  }

  const handleDeleteAssetGroup = async (groupName: string) => {
    const normalized = normalizeSessionGroupName(groupName)
    if (!normalized || normalized === '未分组') {
      addToast('默认资产组不能删除', 'error')
      return
    }
    setMutatingAssetGroup(normalized)
    try {
      const res = await deleteAssetGroup(normalized)
      const updatedById = new Map(res.data.assets.map((asset) => [asset.id, asset]))
      setAssets(assets.map((asset) => updatedById.get(asset.id) || asset))
      deleteSessionGroup(normalized, res.data.fallback_group)
      addToast(`资产组已删除：${normalized}`, 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '资产组删除失败', 'error')
    } finally {
      setMutatingAssetGroup(null)
    }
  }

  const handleConnectAssetGroup = async (groupAssets: Asset[], groupName: string) => {
    const normalized = normalizeSessionGroupName(groupName)
    if (!normalized) {
      addToast('资产组名称无效', 'error')
      return
    }
    if (!groupAssets.length) {
      addToast('当前资产组没有可拉起的资产', 'error')
      return
    }
    createSessionGroup(normalized)
    setConnectingAssetGroup(normalized)
    let successCount = 0
    let failedCount = 0
    try {
      for (const asset of groupAssets) {
        const tags = withPrimaryGroup(asset.tags, normalized)
        try {
          const res = await connectSession(withManagedSecret({
            host: asset.host,
            port: asset.port,
            username: asset.username,
            allow_modifications: false,
            active_skills: asset.skills || [],
            agent_profile: asset.agent_profile || 'default',
            remark: asset.remark || asset.host,
            asset_type: asset.asset_type,
            protocol: asset.protocol,
            extra_args: asset.extra_args || {},
            tags,
            target_scope: 'asset',
            scope_value: asset.host,
          } as Parameters<typeof connectSession>[0]))
          addSession({
            id: res.data.session_id,
            host: asset.host,
            remark: asset.remark || asset.host,
            isReadWriteMode: false,
            skills: asset.skills || [],
            agentProfile: asset.agent_profile || 'default',
            user: asset.username || '',
            asset_type: asset.asset_type,
            protocol: asset.protocol || asset.asset_type,
            extra_args: asset.extra_args || {},
            heartbeatEnabled: false,
            tags,
            target_scope: 'asset',
            scope_value: asset.host,
            messages: [],
            isStreaming: false,
            historyLoaded: false,
          }, successCount === 0)
          successCount += 1
        } catch {
          failedCount += 1
        }
      }
      if (successCount > 0) setView('chat')
      addToast(
        `资产组会话完成：成功 ${successCount} 条，失败 ${failedCount} 条`,
        failedCount > 0 ? 'error' : 'success'
      )
    } finally {
      setConnectingAssetGroup(null)
    }
  }

  return {
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
    handleBatchImportConfirmed,
    handleBulkDeleteAssets,
    handleBulkVerifyAssets,
    handleConnectSelectedAssets,
    handleAssignAssetsToGroup,
    handleConnect,
    handleConnectAssetGroup,
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
    setBatchImportDraft,
    setBatchImportOpen,
    setEditTarget,
    openVerification,
    reportRunId,
    runVerification,
    setDeleteTarget,
    setNormalizeDialog,
    setReportRunId,
    setVerificationPanel,
    savingAsset,
    verificationPanel,
  }
}
