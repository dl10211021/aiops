import { useEffect, useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import { useStore } from '@/store'
import {
  KnowledgeDeleteDialog,
  KnowledgeDocumentPreviewDialog,
  KnowledgeEmptyState,
  KnowledgeFileCard,
  KnowledgeLibraryControls,
  KnowledgeTabs,
  KnowledgeUploadButton,
  MemoryCreatePanel,
  MemoryDeleteDialog,
  MemoryDetailPanel,
  MemoryItemCard,
  MemoryPendingConflictsPanel,
  MemoryQualityPanel,
  MemoryReviewPanel,
  MemorySearchPanel,
  SessionMemoryActivityPanel,
  MemoryStoresPanel,
  MemoryVersionsPanel,
  KnowledgeVaultSearchPanel,
  KnowledgeVaultGraphPanel,
  type KnowledgeTab,
} from './KnowledgeBaseParts'
import { useKnowledgeBaseData } from './useKnowledgeBaseData'

export default function KnowledgeBase() {
  const setView = useStore((state) => state.setView)
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('documents')
  const [documentStep, setDocumentStep] = useState<'source' | 'discover'>('source')
  const [memoryStep, setMemoryStep] = useState<'browse' | 'write' | 'govern'>('browse')
  const [memoryFocusMessageId, setMemoryFocusMessageId] = useState<string | number | null>(null)
  const {
    deleteTarget,
    documentExtension,
    documentPage,
    documentPageSize,
    documentPagination,
    documentQuery,
    documentSort,
    documentSummary,
    documentVectorStatus,
    deletingMemory,
    creatingMemory,
    deleting,
    error,
    exportingMemory,
    exportingVault,
    importingVault,
    files,
    searchingVault,
    loadingVaultGraph,
    handleDelete,
    handleCloseKnowledgePreview,
    handleLoadKnowledgeVaultGraph,
    handleSearchKnowledgeVault,
    handleDeleteMemory,
    handleCreateMemory,
    handleExportMemory,
    handleExportKnowledgeVault,
    handleImportKnowledgeVault,
    handleConfirmMemoryReview,
    handleOpenMemory,
    handleOpenKnowledgeDocument,
    handleReindexKnowledgeDocument,
    handleRedactMemoryVersion,
    handleRestoreMemoryVersion,
    handleResolveMemoryConflict,
    handleSaveMemory,
    handleSearchMemory,
    handleUpload,
    loadFiles,
    loadMemories,
    loadSessionMemoryActivity,
    loading,
    memoryDeleteTarget,
    knowledgePreview,
    knowledgePreviewTarget,
    knowledgeVectorStore,
    memoryDraft,
    memoryError,
    memoryCreateScope,
    memoryCreateSummary,
    memoryItems,
    memoryLoading,
    memoryPendingConflicts,
    memoryQuality,
    memoryReviewItems,
    sessionMemoryActivity,
    sessionMemoryActivityLoading,
    memorySearchQuery,
    memorySearchResults,
    memorySearchScopes,
    memoryStores,
    memoryVersions,
    readingKnowledge,
    reindexingKnowledge,
    savingMemory,
    selectedMemory,
    redactingMemoryVersion,
    resolvingMemoryConflict,
    reviewingMemoryPath,
    setDeleteTarget,
    setDocumentExtension,
    setDocumentPage,
    setDocumentPageSize,
    setDocumentQuery,
    setDocumentSort,
    setDocumentVectorStatus,
    setMemoryCreateScope,
    setMemoryCreateSummary,
    setMemoryDraft,
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
  } = useKnowledgeBaseData()

  useEffect(() => {
    const handleKnowledgeTarget = (event: Event) => {
      const detail = (event as CustomEvent<{
        tab?: KnowledgeTab
        messageId?: string | number
        step?: 'browse' | 'write' | 'govern' | 'source' | 'discover'
        query?: string
        scope?: string
      }>).detail
      if (detail?.tab === 'memory') {
        setActiveTab('memory')
        setMemoryStep(detail.step === 'browse' || detail.step === 'write' || detail.step === 'govern' ? detail.step : 'govern')
        setMemoryFocusMessageId(detail.messageId ?? null)
        void loadMemories()
        void loadSessionMemoryActivity()
      }
      if (detail?.tab === 'documents') {
        setActiveTab('documents')
        setMemoryFocusMessageId(null)
        const query = detail.query?.trim()
        setDocumentStep(
          detail.step === 'source' || detail.step === 'discover'
            ? detail.step
            : query
              ? 'discover'
              : 'source',
        )
        if (query) {
          const scope = detail.scope || 'all'
          setVaultSearchQuery(query)
          setVaultSearchScope(scope)
          window.setTimeout(() => {
            void handleSearchKnowledgeVault({ query, scope })
          }, 80)
        }
      }
    }
    window.addEventListener('opscore:knowledge-target', handleKnowledgeTarget)
    return () => {
      window.removeEventListener('opscore:knowledge-target', handleKnowledgeTarget)
    }
  }, [handleSearchKnowledgeVault, loadMemories, loadSessionMemoryActivity, setVaultSearchQuery, setVaultSearchScope])

  const handleRefresh = () => {
    if (activeTab === 'memory') {
      void loadMemories()
      void loadSessionMemoryActivity()
    } else {
      void loadFiles()
    }
  }

  const handleOpenMemoryPath = (path: string) => {
    const item = memoryItems.find((candidate) => candidate.path === path)
    if (item) void handleOpenMemory(item)
  }

  const handleFocusChatMessage = (messageId: string | number) => {
    setView('chat')
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('opscore:chat-focus-message', {
        detail: { messageId },
      }))
    }, 90)
  }

  const visibleError = activeTab === 'documents' ? error : memoryError
  const friendlyError = visibleError === 'Not Found'
    ? '后台接口返回 Not Found，通常是服务未加载最新路由或需要重启。页面功能已保留，可先刷新或重启服务后再试。'
    : visibleError
  const activeStepGuide = activeTab === 'documents'
    ? {
      title: '资料库',
      body: '这里先解决最基础的问题：你上传了什么、内容是什么、向量状态怎么样、能不能删除。RAG 检索和知识图谱放在第二步，不再和上传列表混在一起。',
      next: '默认先看资料列表：上次上传、内容、删除、向量状态都在这里。',
    }
    : {
      title: 'AI 记忆',
      body: '这里管理 AI 已经记住的经验、偏好和资产画像。好的回答可以沉淀，错误回答只做纠错记录。',
      next: '查看、新增、管理记忆。',
    }
  const knowledgeHealth = [
    ['资料', `${files.length}`, '保存原文，不被 AI 改写'],
    ['待索引', `${files.filter((file) => file.vector_status === 'pending').length}`, '等待 RAG 索引完成'],
    ['可检索', `${files.filter((file) => file.vector_status === 'indexed').length}`, '可被会话引用'],
    ['命中证据', `${vaultSearchResults.length}`, '检索结果可追溯'],
  ]
  const memoryHealth = [
    ['记忆库', `${memoryStores.length}`, '按会话、资产、主机分类'],
    ['文件记忆', `${memoryItems.length}`, '成功经验和用户确认事实'],
    ['本会话反馈', `${sessionMemoryActivity?.summary.promoted_count || 0}/${sessionMemoryActivity?.summary.rejected_count || 0}`, '好评 / 差评，能追溯到输出'],
    ['待治理', `${memoryPendingConflicts.length + memoryReviewItems.length}`, '冲突、过期、反馈待处理'],
    ['历史版本', `${memoryVersions.length}`, '可恢复、可脱敏、可追溯'],
  ]

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          title="知识库"
          description="统一管理上传资料、内容预览、向量状态、RAG 检索、知识图谱和 AI 记忆。"
          actions={(
            <>
            {activeTab === 'documents' && (
              <>
                <button
                  onClick={handleExportKnowledgeVault}
                  disabled={exportingVault}
                  className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {exportingVault ? '导出中...' : '导出备份'}
                </button>
                <label className={`cursor-pointer bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors ${importingVault ? 'pointer-events-none opacity-50' : ''}`}>
                  {importingVault ? '导入中...' : '导入备份 ZIP'}
                  <input
                    type="file"
                    accept=".zip,application/zip"
                    className="hidden"
                    disabled={importingVault}
                    onChange={handleImportKnowledgeVault}
                  />
                </label>
                <KnowledgeUploadButton uploading={uploading} onUpload={handleUpload} />
              </>
            )}
            {activeTab === 'memory' && (
              <>
                <button
                  type="button"
                  onClick={() => setMemoryStep('write')}
                  className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-semibold hover:bg-ops-accent/90 transition-colors"
                >
                  新建记忆
                </button>
                <button
                  type="button"
                  onClick={() => setMemoryStep('write')}
                  className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors"
                >
                  搜索记忆
                </button>
                <button
                  type="button"
                  onClick={() => setMemoryStep('govern')}
                  className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors"
                >
                  管理记忆
                </button>
              </>
            )}
            <button
              onClick={handleRefresh}
              className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors"
            >
              刷新
            </button>
            </>
          )}
        />

        <KnowledgeTabs
          activeTab={activeTab}
          documentCount={files.length}
          memoryCount={memoryItems.length}
          onChange={(tab) => {
            setActiveTab(tab)
            if (tab === 'documents') {
              setDocumentStep('discover')
            } else {
              setMemoryStep('browse')
            }
          }}
        />


        <section className="mb-4 rounded-lg border border-ops-accent/20 bg-gradient-to-r from-ops-accent/10 via-ops-panel/70 to-ops-dark/30 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-ops-accent/80">
                {activeTab === 'documents' ? '资料库' : 'AI 记忆'}
              </div>
              <h3 className="mt-1 text-base font-semibold text-ops-text">{activeStepGuide.title}</h3>
              <p className="mt-1 max-w-4xl text-sm leading-6 text-ops-subtext">{activeStepGuide.body}</p>
            </div>
            <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2 text-xs leading-5 text-ops-subtext lg:max-w-xs">
              {activeStepGuide.next}
            </div>
          </div>
        </section>

        {visibleError && (
          <div className="mb-4 flex flex-col gap-3 rounded-lg border border-amber-300/25 bg-amber-300/5 px-4 py-3 text-sm text-amber-100 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/80">
                {activeTab === 'documents' ? '知识库接口提示' : '记忆接口提示'}
              </div>
              <div className="mt-1 text-sm leading-6 text-ops-subtext">{friendlyError}</div>
            </div>
            <button
              onClick={handleRefresh}
              className="shrink-0 rounded-md border border-amber-300/35 px-3 py-1.5 text-xs font-semibold text-amber-100 hover:bg-amber-300/10"
            >
              重新加载
            </button>
          </div>
        )}

        {activeTab === 'documents' && loading && (
          <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-8 text-center text-sm text-ops-subtext">
            正在加载知识库文档...
          </section>
        )}

        {activeTab === 'documents' && !loading ? (
          <div className="space-y-4">
            <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-3">
              <div className="grid gap-2 md:grid-cols-4">
                {([
                  ['source', '资料列表', `${files.length} 份资料`, '上传、查看、删除'],
                  ['discover', '检索与图谱', `${vaultSearchResults.length} 条命中`, '查证据和关系'],
                ] as const).map(([id, label, count, desc]) => (
                  <button
                    key={id}
                    onClick={() => setDocumentStep(id)}
                    className={`rounded-md border px-4 py-3 text-left transition-colors ${
                      documentStep === id
                        ? 'border-ops-accent bg-ops-accent text-ops-dark'
                        : 'border-ops-surface0 bg-ops-dark/25 text-ops-subtext hover:border-ops-accent/40 hover:text-ops-text'
                    }`}
                  >
                    <span className="block text-sm font-bold">{label}</span>
                    <span className="mt-1 block text-xs opacity-85">{count}</span>
                    <span className="mt-1 block text-[11px] opacity-75">{desc}</span>
                  </button>
                ))}
              </div>
            </section>

            {documentStep === 'source' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
                <section className="space-y-3">
                  <KnowledgeLibraryControls
                    extension={documentExtension}
                    pageSize={documentPageSize}
                    pagination={documentPagination}
                    query={documentQuery}
                    sort={documentSort}
                    summary={documentSummary}
                    vectorStatus={documentVectorStatus}
                    vectorStore={knowledgeVectorStore}
                    onExtensionChange={setDocumentExtension}
                    onPageChange={setDocumentPage}
                    onPageSizeChange={setDocumentPageSize}
                    onQueryChange={setDocumentQuery}
                    onRefresh={() => void loadFiles()}
                    onSortChange={setDocumentSort}
                    onVectorStatusChange={setDocumentVectorStatus}
                  />
                  {files.length > 0 ? (
                    <div className="grid gap-2 2xl:grid-cols-2">
                      {files.map((file) => (
                        <KnowledgeFileCard
                          key={file.filename}
                          file={file}
                          onOpen={handleOpenKnowledgeDocument}
                          onReindex={handleReindexKnowledgeDocument}
                          onDelete={setDeleteTarget}
                          reindexing={reindexingKnowledge === file.filename}
                        />
                      ))}
                    </div>
                  ) : (
                    <KnowledgeEmptyState uploading={uploading} onUpload={handleUpload} />
                  )}
                </section>
                <aside className="space-y-3">
                  <div className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                    <div className="text-sm font-semibold text-ops-text">资料库说明</div>
                    <div className="mt-3 space-y-2 text-xs leading-5 text-ops-subtext">
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">你上次上传的资料就在左侧列表，点“查看内容”可以看原文或来源记录。</div>
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">向量状态只代表语义检索是否就绪；即使跳过向量，原文仍然保留。</div>
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">删除按钮会同步移除资料库记录和对应来源文件。</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDocumentStep('discover')}
                      className="mt-4 w-full rounded-md border border-ops-accent/45 px-3 py-2 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                    >
                      下一步：RAG 检索
                    </button>
                  </div>
                </aside>
              </div>
            )}

            {documentStep === 'discover' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.8fr)]">
                <KnowledgeVaultSearchPanel
                  query={vaultSearchQuery}
                  results={vaultSearchResults}
                  scope={vaultSearchScope}
                  searching={searchingVault}
                  onQueryChange={setVaultSearchQuery}
                  onScopeChange={setVaultSearchScope}
                  onSearch={handleSearchKnowledgeVault}
                />
                <KnowledgeVaultGraphPanel
                  graph={vaultGraph}
                  includeCandidates={vaultGraphIncludeCandidates}
                  loading={loadingVaultGraph}
                  onIncludeCandidatesChange={setVaultGraphIncludeCandidates}
                  onLoad={handleLoadKnowledgeVaultGraph}
                />
              </div>
            )}
          </div>
        ) : null}

        {activeTab === 'memory' && memoryLoading && (
          <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-8 text-center text-sm text-ops-subtext">
            正在加载 AI 记忆...
          </section>
        )}

        {activeTab === 'memory' && !memoryLoading && (
          <div className="space-y-4">
            <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-3">
              <div className="grid gap-2 md:grid-cols-3">
                {([
                  ['browse', '记忆列表', `${memoryItems.length} 条文件记忆`, '查看、编辑、删除'],
                  ['write', '新增/搜索', `${memorySearchResults.length} 条检索命中`, '新增和搜索记忆'],
                  ['govern', '管理记忆', `${memoryPendingConflicts.length + memoryReviewItems.length} 项待处理`, '处理冲突和版本'],
                ] as const).map(([id, label, count, desc]) => (
                  <button
                    key={id}
                    onClick={() => setMemoryStep(id)}
                    className={`rounded-md border px-4 py-3 text-left transition-colors ${
                      memoryStep === id
                        ? 'border-ops-accent bg-ops-accent text-ops-dark'
                        : 'border-ops-surface0 bg-ops-dark/25 text-ops-subtext hover:border-ops-accent/40 hover:text-ops-text'
                    }`}
                  >
                    <span className="block text-sm font-bold">{label}</span>
                    <span className="mt-1 block text-xs opacity-85">{count}</span>
                    <span className="mt-1 block text-[11px] opacity-75">{desc}</span>
                  </button>
                ))}
              </div>
            </section>

            <MemoryQualityPanel
              report={memoryQuality}
              onGoGovern={() => setMemoryStep('govern')}
              onOpen={handleOpenMemoryPath}
              onRefresh={() => void loadMemories()}
            />

            {memoryStep === 'browse' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(420px,1fr)]">
                <section className="space-y-2">
                  {memoryItems.length > 0 ? memoryItems.map((item) => (
                    <MemoryItemCard
                      key={item.path}
                      item={item}
                      selected={selectedMemory?.path === item.path}
                      onOpen={handleOpenMemory}
                      onDelete={setMemoryDeleteTarget}
                    />
                  )) : (
                    <div className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-6">
                      <div className="text-sm font-semibold text-ops-text">暂无 AI 记忆</div>
                      <p className="mt-2 text-sm leading-6 text-ops-subtext">
                        会话点赞、资产画像和有效经验沉淀后，会在这里形成 Claude 风格文件记忆。
                      </p>
                    </div>
                  )}
                </section>
                <MemoryDetailPanel
                  draft={memoryDraft}
                  exporting={exportingMemory}
                  memory={selectedMemory}
                  saving={savingMemory}
                  onDraftChange={setMemoryDraft}
                  onExport={() => void handleExportMemory()}
                  onSave={() => void handleSaveMemory()}
                />
                <aside className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                  <div className="text-sm font-semibold text-ops-text">没有找到合适记忆？</div>
                  <p className="mt-2 text-xs leading-5 text-ops-subtext">
                    进入写入与检索，把新的成功经验、用户偏好或资产画像沉淀成可审计文件。
                  </p>
                  <button
                    type="button"
                    onClick={() => setMemoryStep('write')}
                    className="mt-4 rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                  >
                    去写入/检索
                  </button>
                </aside>
              </div>
            )}

            {memoryStep === 'write' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(360px,0.7fr)_minmax(0,1fr)]">
                <MemoryCreatePanel
                  creating={creatingMemory}
                  scope={memoryCreateScope}
                  summary={memoryCreateSummary}
                  onCreate={() => void handleCreateMemory()}
                  onScopeChange={setMemoryCreateScope}
                  onSummaryChange={setMemoryCreateSummary}
                />
                <MemorySearchPanel
                  query={memorySearchQuery}
                  results={memorySearchResults}
                  scopes={memorySearchScopes}
                  searching={searchingMemory}
                  onQueryChange={setMemorySearchQuery}
                  onScopesChange={setMemorySearchScopes}
                  onSearch={() => void handleSearchMemory()}
                />
                <aside className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                  <div className="text-sm font-semibold text-ops-text">记忆写完后要治理</div>
                  <p className="mt-2 text-xs leading-5 text-ops-subtext">
                    冲突、过期、失败反馈都集中到管理记忆，避免错误经验长期污染 AI。
                  </p>
                  <button
                    type="button"
                    onClick={() => setMemoryStep('govern')}
                    className="mt-4 rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                  >
                    下一步：管理记忆
                  </button>
                </aside>
              </div>
            )}

            {memoryStep === 'govern' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.75fr)]">
                <section className="space-y-4">
                  <SessionMemoryActivityPanel
                    activity={sessionMemoryActivity}
                    focusMessageId={memoryFocusMessageId}
                    loading={sessionMemoryActivityLoading}
                    onFocusMessage={handleFocusChatMessage}
                    onReload={() => void loadSessionMemoryActivity()}
                  />
                  <MemoryPendingConflictsPanel
                    items={memoryPendingConflicts}
                    resolvingKey={resolvingMemoryConflict}
                    onOpen={handleOpenMemoryPath}
                    onResolve={(item, action) => void handleResolveMemoryConflict(item, action)}
                  />
                  <MemoryReviewPanel
                    items={memoryReviewItems}
                    reviewingPath={reviewingMemoryPath}
                    onOpen={handleOpenMemoryPath}
                    onReview={(item) => void handleConfirmMemoryReview(item)}
                  />
                </section>
                <aside className="space-y-4">
                  <MemoryStoresPanel stores={memoryStores} />
                  <MemoryVersionsPanel
                    versions={memoryVersions}
                    redactingVersionId={redactingMemoryVersion}
                    onRedact={(version) => void handleRedactMemoryVersion(version)}
                    onRestore={(version) => void handleRestoreMemoryVersion(version)}
                  />
                </aside>
              </div>
            )}
          </div>
        )}
      </div>
      {deleteTarget && (
        <KnowledgeDeleteDialog
          deleting={deleting}
          target={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete()}
        />
      )}
      {knowledgePreviewTarget && (
        <KnowledgeDocumentPreviewDialog
          content={knowledgePreview}
          loading={readingKnowledge}
          target={knowledgePreviewTarget}
          onClose={handleCloseKnowledgePreview}
        />
      )}
      {memoryDeleteTarget && (
        <MemoryDeleteDialog
          deleting={deletingMemory}
          target={memoryDeleteTarget}
          onCancel={() => setMemoryDeleteTarget(null)}
          onConfirm={() => void handleDeleteMemory()}
        />
      )}
    </div>
  )
}
