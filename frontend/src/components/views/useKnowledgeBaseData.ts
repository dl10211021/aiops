import type { ChangeEvent } from 'react'
import { useCallback, useEffect, useState } from 'react'
import {
  approveKnowledgeVaultCandidate,
  compileKnowledgeVaultSource,
  createMemoryItem,
  deleteKnowledgeDocument,
  deleteMemoryItem,
  exportKnowledgeVault,
  exportMemoryStore,
  graphKnowledgeVault,
  confirmMemoryReview,
  importKnowledgeVault,
  listKnowledgeDocuments,
  listKnowledgeVaultArticles,
  listKnowledgeVaultCandidates,
  listKnowledgeVaultQueue,
  listMemoryItems,
  listMemoryPendingConflicts,
  listMemoryReviewItems,
  listMemoryStores,
  listMemoryVersions,
  redactMemoryVersion,
  readMemoryItem,
  readKnowledgeVaultCandidate,
  readKnowledgeVaultArticle,
  restoreMemoryVersion,
  resolveMemoryPendingConflict,
  searchKnowledgeVault,
  searchMemoryItems,
  updateMemoryItem,
  updateKnowledgeVaultCandidate,
  uploadKnowledgeDocument,
} from '@/api/knowledge'
import { getSessionMemoryActivity } from '@/api/sessionHistory'
import { useStore } from '@/store'
import type { KnowledgeCompileQueueItem, KnowledgeFile, KnowledgeVaultGraph, KnowledgeVaultSearchResult, MemoryDetail, MemoryItem, MemoryPendingConflict, MemoryReviewItem, MemorySearchResult, MemoryStoreInfo, MemoryVersion, SessionMemoryActivity } from '@/types'
import { isAcceptedKnowledgeFile } from './knowledgeBaseModel'

export function useKnowledgeBaseData() {
  const addToast = useStore((s) => s.addToast)
  const currentSessionId = useStore((s) => s.currentSessionId)
  const [files, setFiles] = useState<KnowledgeFile[]>([])
  const [compileQueueItems, setCompileQueueItems] = useState<KnowledgeCompileQueueItem[]>([])
  const [candidateItems, setCandidateItems] = useState<KnowledgeCompileQueueItem[]>([])
  const [articleItems, setArticleItems] = useState<KnowledgeCompileQueueItem[]>([])
  const [selectedCandidate, setSelectedCandidate] = useState<KnowledgeCompileQueueItem | null>(null)
  const [selectedArticle, setSelectedArticle] = useState<KnowledgeCompileQueueItem | null>(null)
  const [candidateDraft, setCandidateDraft] = useState('')
  const [vaultSearchQuery, setVaultSearchQuery] = useState('')
  const [vaultSearchScope, setVaultSearchScope] = useState('all')
  const [vaultSearchResults, setVaultSearchResults] = useState<KnowledgeVaultSearchResult[]>([])
  const [vaultGraph, setVaultGraph] = useState<KnowledgeVaultGraph | null>(null)
  const [vaultGraphIncludeCandidates, setVaultGraphIncludeCandidates] = useState(true)
  const [memoryItems, setMemoryItems] = useState<MemoryItem[]>([])
  const [memoryStores, setMemoryStores] = useState<MemoryStoreInfo[]>([])
  const [memoryVersions, setMemoryVersions] = useState<MemoryVersion[]>([])
  const [memoryPendingConflicts, setMemoryPendingConflicts] = useState<MemoryPendingConflict[]>([])
  const [memoryReviewItems, setMemoryReviewItems] = useState<MemoryReviewItem[]>([])
  const [sessionMemoryActivity, setSessionMemoryActivity] = useState<SessionMemoryActivity | null>(null)
  const [selectedMemory, setSelectedMemory] = useState<MemoryDetail | null>(null)
  const [memoryDraft, setMemoryDraft] = useState('')
  const [memoryCreateScope, setMemoryCreateScope] = useState('manual')
  const [memoryCreateSummary, setMemoryCreateSummary] = useState('')
  const [memorySearchQuery, setMemorySearchQuery] = useState('')
  const [memorySearchScopes, setMemorySearchScopes] = useState('manual')
  const [memorySearchResults, setMemorySearchResults] = useState<MemorySearchResult[]>([])
  const [uploading, setUploading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeFile | null>(null)
  const [memoryDeleteTarget, setMemoryDeleteTarget] = useState<MemoryItem | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deletingMemory, setDeletingMemory] = useState(false)
  const [savingMemory, setSavingMemory] = useState(false)
  const [creatingMemory, setCreatingMemory] = useState(false)
  const [searchingMemory, setSearchingMemory] = useState(false)
  const [exportingMemory, setExportingMemory] = useState(false)
  const [exportingVault, setExportingVault] = useState(false)
  const [importingVault, setImportingVault] = useState(false)
  const [resolvingMemoryConflict, setResolvingMemoryConflict] = useState<string | null>(null)
  const [redactingMemoryVersion, setRedactingMemoryVersion] = useState<string | null>(null)
  const [reviewingMemoryPath, setReviewingMemoryPath] = useState<string | null>(null)
  const [compilingSourceSession, setCompilingSourceSession] = useState<string | null>(null)
  const [approvingSourceSession, setApprovingSourceSession] = useState<string | null>(null)
  const [openingCandidate, setOpeningCandidate] = useState<string | null>(null)
  const [openingArticle, setOpeningArticle] = useState<string | null>(null)
  const [savingCandidate, setSavingCandidate] = useState(false)
  const [searchingVault, setSearchingVault] = useState(false)
  const [loadingVaultGraph, setLoadingVaultGraph] = useState(false)
  const [loading, setLoading] = useState(true)
  const [memoryLoading, setMemoryLoading] = useState(true)
  const [sessionMemoryActivityLoading, setSessionMemoryActivityLoading] = useState(false)
  const [error, setError] = useState('')
  const [memoryError, setMemoryError] = useState('')

  const loadFiles = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await listKnowledgeDocuments()
      const [queueRes, candidatesRes, articlesRes] = await Promise.all([
        listKnowledgeVaultQueue(),
        listKnowledgeVaultCandidates(),
        listKnowledgeVaultArticles(),
      ])
      setFiles(res.data.files || [])
      setCompileQueueItems(queueRes.data.items || [])
      setCandidateItems(candidatesRes.data.items || [])
      setArticleItems(articlesRes.data.items || [])
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '加载知识库失败'
      if (message === 'Not Found') {
        setFiles([])
        setCompileQueueItems([])
        setCandidateItems([])
        setArticleItems([])
        setError('')
      } else {
        setError(message)
      }
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
      const message = e instanceof Error ? e.message : '加载 AI 记忆失败'
      setMemoryError(message === 'Not Found' ? 'AI 记忆服务暂未开启或当前服务需要重启。' : message)
    } finally {
      setMemoryLoading(false)
    }
  }, [addToast])

  const loadSessionMemoryActivity = useCallback(async () => {
    if (!currentSessionId) {
      setSessionMemoryActivity(null)
      return
    }
    setSessionMemoryActivityLoading(true)
    try {
      const res = await getSessionMemoryActivity(currentSessionId)
      setSessionMemoryActivity(res.data.activity)
    } catch {
      setSessionMemoryActivity(null)
    } finally {
      setSessionMemoryActivityLoading(false)
    }
  }, [currentSessionId])

  useEffect(() => {
    void loadFiles()
    void loadMemories()
  }, [loadFiles, loadMemories])

  useEffect(() => {
    void loadSessionMemoryActivity()
  }, [loadSessionMemoryActivity])

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

  const handleCompileKnowledgeSource = async (item: KnowledgeCompileQueueItem) => {
    const sourceSessionId = item.source_session_id || item.id
    if (!sourceSessionId) {
      addToast('该资料缺少 source session，无法编译', 'error')
      return
    }
    setCompilingSourceSession(sourceSessionId)
    try {
      const res = await compileKnowledgeVaultSource(sourceSessionId, true)
      await loadFiles()
      const candidatePath = res.data.item?.candidate_path
      addToast(candidatePath ? `候选 Wiki 已生成：${candidatePath}` : '候选 Wiki 已生成', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '生成候选 Wiki 失败', 'error')
    } finally {
      setCompilingSourceSession(null)
    }
  }

  const handleApproveKnowledgeCandidate = async (item: KnowledgeCompileQueueItem) => {
    const sourceSessionId = item.source_session_id || item.id
    if (!sourceSessionId) {
      addToast('该候选缺少 source session，无法批准', 'error')
      return
    }
    setApprovingSourceSession(sourceSessionId)
    try {
      const res = await approveKnowledgeVaultCandidate(sourceSessionId)
      await loadFiles()
      const wikiPath = res.data.item?.wiki_path
      addToast(wikiPath ? `候选已入库：${wikiPath}` : '候选 Wiki 已批准入库', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '批准候选 Wiki 失败', 'error')
    } finally {
      setApprovingSourceSession(null)
    }
  }

  const handleOpenKnowledgeCandidate = async (item: KnowledgeCompileQueueItem) => {
    const sourceSessionId = item.source_session_id || item.id
    if (!sourceSessionId) {
      addToast('该候选缺少 source session，无法打开', 'error')
      return
    }
    setOpeningCandidate(sourceSessionId)
    try {
      const res = await readKnowledgeVaultCandidate(sourceSessionId)
      setSelectedCandidate(res.data.item)
      setCandidateDraft(res.data.item.content || '')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '打开候选 Wiki 失败', 'error')
    } finally {
      setOpeningCandidate(null)
    }
  }

  const handleSaveKnowledgeCandidate = async () => {
    const sourceSessionId = selectedCandidate?.source_session_id || selectedCandidate?.id
    if (!sourceSessionId) {
      addToast('请先打开候选 Wiki', 'error')
      return
    }
    setSavingCandidate(true)
    try {
      const res = await updateKnowledgeVaultCandidate(
        sourceSessionId,
        candidateDraft,
        selectedCandidate?.content_sha256,
      )
      setSelectedCandidate(res.data.item)
      setCandidateDraft(res.data.item.content || '')
      await loadFiles()
      addToast('候选 Wiki 已保存', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存候选 Wiki 失败', 'error')
    } finally {
      setSavingCandidate(false)
    }
  }

  const handleOpenKnowledgeArticle = async (item: KnowledgeCompileQueueItem) => {
    const sourceSessionId = item.source_session_id || item.id
    if (!sourceSessionId) {
      addToast('该文章缺少 source session，无法打开', 'error')
      return
    }
    setOpeningArticle(sourceSessionId)
    try {
      const res = await readKnowledgeVaultArticle(sourceSessionId)
      setSelectedArticle(res.data.item)
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '打开正式 Wiki 失败', 'error')
    } finally {
      setOpeningArticle(null)
    }
  }

  const handleSearchKnowledgeVault = async () => {
    const query = vaultSearchQuery.trim()
    if (!query) {
      addToast('请输入知识库搜索关键词', 'error')
      return
    }
    setSearchingVault(true)
    try {
      const res = await searchKnowledgeVault(query, vaultSearchScope, 20)
      const results = res.data.results || []
      setVaultSearchResults(results)
      addToast(`搜索到 ${results.length} 条知识`, 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '搜索知识库失败', 'error')
    } finally {
      setSearchingVault(false)
    }
  }

  const handleLoadKnowledgeVaultGraph = async () => {
    setLoadingVaultGraph(true)
    try {
      const res = await graphKnowledgeVault(vaultGraphIncludeCandidates)
      setVaultGraph(res.data)
      addToast(`关系图已生成：${res.data.summary.node_count} 个节点，${res.data.summary.edge_count} 条关系`, 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '生成知识图谱失败', 'error')
    } finally {
      setLoadingVaultGraph(false)
    }
  }

  const handleExportKnowledgeVault = async () => {
    setExportingVault(true)
    try {
      const blob = await exportKnowledgeVault()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `opscore-knowledge-vault-${Date.now()}.zip`
      a.click()
      URL.revokeObjectURL(url)
      addToast('Vault 已导出为 ZIP', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '导出 Vault 失败', 'error')
    } finally {
      setExportingVault(false)
    }
  }

  const handleImportKnowledgeVault = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.zip')) {
      addToast('Vault 导入仅支持 ZIP 文件', 'error')
      return
    }
    setImportingVault(true)
    try {
      await importKnowledgeVault(file)
      await loadFiles()
      addToast('Vault ZIP 已导入', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '导入 Vault 失败', 'error')
    } finally {
      setImportingVault(false)
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

  const handleSearchMemory = async () => {
    const query = memorySearchQuery.trim()
    const scopes = memorySearchScopes
      .split(/[\s,，]+/)
      .map((scope) => scope.trim())
      .filter(Boolean)
    if (!query || scopes.length === 0) {
      addToast('请填写检索问题和作用域', 'error')
      return
    }
    setSearchingMemory(true)
    try {
      const res = await searchMemoryItems(query, scopes, 8)
      const results = res.data.results || []
      setMemorySearchResults(results)
      addToast(`检索到 ${results.length} 条记忆`, 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '检索 AI 记忆失败', 'error')
    } finally {
      setSearchingMemory(false)
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

  const handleRedactMemoryVersion = async (version: MemoryVersion) => {
    if (!version.version_id) {
      addToast('该版本缺少脱敏标识，无法脱敏', 'error')
      return
    }
    setRedactingMemoryVersion(version.version_id)
    try {
      await redactMemoryVersion(version.version_id)
      await loadMemories()
      addToast('记忆版本已脱敏', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '记忆版本脱敏失败', 'error')
    } finally {
      setRedactingMemoryVersion(null)
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
    exportingVault,
    files,
    compileQueueItems,
    candidateItems,
    articleItems,
    candidateDraft,
    compilingSourceSession,
    approvingSourceSession,
    openingCandidate,
    openingArticle,
    savingCandidate,
    searchingVault,
    selectedCandidate,
    selectedArticle,
    handleDelete,
    handleCompileKnowledgeSource,
    handleApproveKnowledgeCandidate,
    handleOpenKnowledgeCandidate,
    handleOpenKnowledgeArticle,
    handleLoadKnowledgeVaultGraph,
    handleSearchKnowledgeVault,
    handleSaveKnowledgeCandidate,
    handleDeleteMemory,
    handleCreateMemory,
    handleExportMemory,
    handleExportKnowledgeVault,
    handleImportKnowledgeVault,
    handleConfirmMemoryReview,
    handleOpenMemory,
    handleRedactMemoryVersion,
    handleRestoreMemoryVersion,
    handleResolveMemoryConflict,
    handleSaveMemory,
    handleSearchMemory,
    handleUpload,
    loadFiles,
    loadMemories,
    loadSessionMemoryActivity,
    loadingVaultGraph,
    loading,
    memoryDeleteTarget,
    memoryDraft,
    memoryError,
    importingVault,
    memoryCreateScope,
    memoryCreateSummary,
    memoryItems,
    memoryLoading,
    memoryPendingConflicts,
    memoryReviewItems,
    sessionMemoryActivity,
    sessionMemoryActivityLoading,
    memorySearchQuery,
    memorySearchResults,
    memorySearchScopes,
    memoryStores,
    memoryVersions,
    savingMemory,
    selectedMemory,
    redactingMemoryVersion,
    resolvingMemoryConflict,
    reviewingMemoryPath,
    setDeleteTarget,
    setMemoryCreateScope,
    setMemoryCreateSummary,
    setMemoryDraft,
    setCandidateDraft,
    setVaultGraphIncludeCandidates,
    setVaultSearchQuery,
    setVaultSearchScope,
    setMemoryDeleteTarget,
    setMemorySearchQuery,
    setMemorySearchScopes,
    searchingMemory,
    vaultGraph,
    vaultGraphIncludeCandidates,
    vaultSearchQuery,
    vaultSearchResults,
    vaultSearchScope,
    uploading,
  }
}
