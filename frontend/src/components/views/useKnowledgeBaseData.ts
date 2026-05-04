import type { ChangeEvent } from 'react'
import { useCallback, useEffect, useState } from 'react'
import {
  createMemoryItem,
  deleteKnowledgeDocument,
  deleteMemoryItem,
  exportMemoryStore,
  confirmMemoryReview,
  listKnowledgeDocuments,
  listMemoryItems,
  listMemoryPendingConflicts,
  listMemoryReviewItems,
  listMemoryStores,
  listMemoryVersions,
  readMemoryItem,
  restoreMemoryVersion,
  resolveMemoryPendingConflict,
  updateMemoryItem,
  uploadKnowledgeDocument,
} from '@/api/knowledge'
import { useStore } from '@/store'
import type { KnowledgeFile, MemoryDetail, MemoryItem, MemoryPendingConflict, MemoryReviewItem, MemoryStoreInfo, MemoryVersion } from '@/types'
import { isAcceptedKnowledgeFile } from './knowledgeBaseModel'

export function useKnowledgeBaseData() {
  const addToast = useStore((s) => s.addToast)
  const [files, setFiles] = useState<KnowledgeFile[]>([])
  const [memoryItems, setMemoryItems] = useState<MemoryItem[]>([])
  const [memoryStores, setMemoryStores] = useState<MemoryStoreInfo[]>([])
  const [memoryVersions, setMemoryVersions] = useState<MemoryVersion[]>([])
  const [memoryPendingConflicts, setMemoryPendingConflicts] = useState<MemoryPendingConflict[]>([])
  const [memoryReviewItems, setMemoryReviewItems] = useState<MemoryReviewItem[]>([])
  const [selectedMemory, setSelectedMemory] = useState<MemoryDetail | null>(null)
  const [memoryDraft, setMemoryDraft] = useState('')
  const [memoryCreateScope, setMemoryCreateScope] = useState('manual')
  const [memoryCreateSummary, setMemoryCreateSummary] = useState('')
  const [uploading, setUploading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeFile | null>(null)
  const [memoryDeleteTarget, setMemoryDeleteTarget] = useState<MemoryItem | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deletingMemory, setDeletingMemory] = useState(false)
  const [savingMemory, setSavingMemory] = useState(false)
  const [creatingMemory, setCreatingMemory] = useState(false)
  const [exportingMemory, setExportingMemory] = useState(false)
  const [resolvingMemoryConflict, setResolvingMemoryConflict] = useState<string | null>(null)
  const [reviewingMemoryPath, setReviewingMemoryPath] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [memoryLoading, setMemoryLoading] = useState(true)
  const [error, setError] = useState('')
  const [memoryError, setMemoryError] = useState('')

  const loadFiles = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await listKnowledgeDocuments()
      setFiles(res.data.files || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载知识库失败')
      addToast('加载知识库失败', 'error')
    } finally {
      setLoading(false)
    }
  }, [addToast])

  const loadMemories = useCallback(async () => {
    setMemoryLoading(true)
    setMemoryError('')
    try {
      const [itemsRes, versionsRes, pendingRes] = await Promise.all([
        listMemoryItems(),
        listMemoryVersions(30),
        listMemoryPendingConflicts(50),
      ])
      const reviewRes = await listMemoryReviewItems(180, 50)
      setMemoryItems(itemsRes.data.items || [])
      setMemoryVersions(versionsRes.data.versions || [])
      setMemoryPendingConflicts(pendingRes.data.items || [])
      setMemoryReviewItems(reviewRes.data.items || [])
      setSelectedMemory((current) => {
        if (!current) return current
        const stillExists = (itemsRes.data.items || []).some((item) => item.path === current.path)
        return stillExists ? current : null
      })
      void listMemoryStores().then((storesRes) => setMemoryStores(storesRes.data.stores || []))
    } catch (e: unknown) {
      setMemoryError(e instanceof Error ? e.message : '加载 AI 记忆失败')
      addToast('加载 AI 记忆失败', 'error')
    } finally {
      setMemoryLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    void loadFiles()
    void loadMemories()
  }, [loadFiles, loadMemories])

  const handleUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    const selectedFiles = Array.from(fileList)
    const rejectedFiles = selectedFiles.filter((file) => !isAcceptedKnowledgeFile(file.name))
    if (rejectedFiles.length > 0) {
      addToast(`暂不支持：${rejectedFiles.map((file) => file.name).join('、')}`, 'error')
      e.target.value = ''
      return
    }

    setUploading(true)
    let successCount = 0
    for (const file of selectedFiles) {
      try {
        await uploadKnowledgeDocument(file)
        successCount++
      } catch {
        addToast(`上传 ${file.name} 失败`, 'error')
      }
    }
    if (successCount > 0) {
      addToast(`成功上传 ${successCount} 个文档`, 'success')
      await loadFiles()
    }
    setUploading(false)
    e.target.value = ''
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    const filename = deleteTarget.filename
    setDeleting(true)
    try {
      await deleteKnowledgeDocument(filename)
      setFiles((current) => current.filter((f) => f.filename !== filename))
      setDeleteTarget(null)
      addToast('文档已删除', 'success')
    } catch {
      addToast('删除失败', 'error')
    } finally {
      setDeleting(false)
    }
  }

  const handleOpenMemory = async (item: MemoryItem) => {
    setMemoryError('')
    try {
      const res = await readMemoryItem(item.path)
      setSelectedMemory(res.data.item)
      setMemoryDraft(res.data.item.content)
    } catch (e: unknown) {
      setMemoryError(e instanceof Error ? e.message : '读取 AI 记忆失败')
      addToast('读取 AI 记忆失败', 'error')
    }
  }

  const handleCreateMemory = async () => {
    const scope = memoryCreateScope.trim()
    const summary = memoryCreateSummary.trim()
    if (!scope || !summary) {
      addToast('请填写记忆作用域和内容', 'error')
      return
    }
    setCreatingMemory(true)
    try {
      await createMemoryItem(scope, summary)
      setMemoryCreateSummary('')
      await loadMemories()
      addToast('AI 记忆已创建', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '创建 AI 记忆失败', 'error')
    } finally {
      setCreatingMemory(false)
    }
  }

  const handleDeleteMemory = async () => {
    if (!memoryDeleteTarget) return
    const path = memoryDeleteTarget.path
    setDeletingMemory(true)
    try {
      await deleteMemoryItem(path)
      setMemoryItems((current) => current.filter((item) => item.path !== path))
      setSelectedMemory((current) => (current?.path === path ? null : current))
      setMemoryDeleteTarget(null)
      await loadMemories()
      addToast('AI 记忆已删除', 'success')
    } catch {
      addToast('删除 AI 记忆失败', 'error')
    } finally {
      setDeletingMemory(false)
    }
  }

  const handleSaveMemory = async () => {
    if (!selectedMemory) return
    setSavingMemory(true)
    try {
      const res = await updateMemoryItem(selectedMemory.path, memoryDraft, selectedMemory.content_sha256)
      setSelectedMemory(res.data.item)
      setMemoryDraft(res.data.item.content)
      await loadMemories()
      addToast('AI 记忆已更新', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存 AI 记忆失败', 'error')
    } finally {
      setSavingMemory(false)
    }
  }

  const handleRestoreMemoryVersion = async (version: MemoryVersion) => {
    if (!version.version_id) {
      addToast('该版本缺少恢复标识，无法恢复', 'error')
      return
    }
    try {
      await restoreMemoryVersion(version.version_id)
      await loadMemories()
      addToast('AI 记忆版本已恢复', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '恢复 AI 记忆失败', 'error')
    }
  }

  const handleResolveMemoryConflict = async (
    item: MemoryPendingConflict,
    action: 'accept_new' | 'keep_old' | 'merged',
  ) => {
    setResolvingMemoryConflict(`${item.version_id}:${action}`)
    try {
      await resolveMemoryPendingConflict(item.version_id, action)
      await loadMemories()
      addToast('待确认记忆已处理', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '处理待确认记忆失败', 'error')
    } finally {
      setResolvingMemoryConflict(null)
    }
  }

  const handleConfirmMemoryReview = async (item: MemoryReviewItem) => {
    setReviewingMemoryPath(item.path)
    try {
      await confirmMemoryReview(item.path)
      await loadMemories()
      addToast('记忆已标记为复核通过', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '标记复核失败', 'error')
    } finally {
      setReviewingMemoryPath(null)
    }
  }

  const handleExportMemory = async () => {
    setExportingMemory(true)
    try {
      const res = await exportMemoryStore()
      const blob = new Blob([JSON.stringify(res.data.export, null, 2)], { type: 'application/json;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `opscore-memory-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
      addToast('AI 记忆已导出', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '导出 AI 记忆失败', 'error')
    } finally {
      setExportingMemory(false)
    }
  }

  return {
    deleteTarget,
    deletingMemory,
    creatingMemory,
    deleting,
    error,
    exportingMemory,
    files,
    handleDelete,
    handleDeleteMemory,
    handleCreateMemory,
    handleExportMemory,
    handleConfirmMemoryReview,
    handleOpenMemory,
    handleRestoreMemoryVersion,
    handleResolveMemoryConflict,
    handleSaveMemory,
    handleUpload,
    loadFiles,
    loadMemories,
    loading,
    memoryDeleteTarget,
    memoryDraft,
    memoryError,
    memoryCreateScope,
    memoryCreateSummary,
    memoryItems,
    memoryLoading,
    memoryPendingConflicts,
    memoryReviewItems,
    memoryStores,
    memoryVersions,
    savingMemory,
    selectedMemory,
    resolvingMemoryConflict,
    reviewingMemoryPath,
    setDeleteTarget,
    setMemoryCreateScope,
    setMemoryCreateSummary,
    setMemoryDraft,
    setMemoryDeleteTarget,
    uploading,
  }
}
