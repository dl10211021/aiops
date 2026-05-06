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
  MemorySearchPanel,
  SessionMemoryActivityPanel,
  KnowledgeVaultSearchPanel,
  type KnowledgeTab,
} from './KnowledgeBaseParts'
import { useKnowledgeBaseData } from './useKnowledgeBaseData'

export default function KnowledgeBase() {
  const setView = useStore((state) => state.setView)
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('documents')
  const [documentStep, setDocumentStep] = useState<'source' | 'discover'>('source')
  const [memoryStep, setMemoryStep] = useState<'browse' | 'write' | 'feedback'>('browse')
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
    files,
    searchingVault,
    handleDelete,
    handleCloseKnowledgePreview,
    handleSearchKnowledgeVault,
    handleDeleteMemory,
    handleCreateMemory,
    handleExportMemory,
    handleOpenMemory,
    handleOpenKnowledgeDocument,
    handleReindexKnowledgeDocument,
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
    sessionMemoryActivity,
    sessionMemoryActivityLoading,
    memorySearchQuery,
    memorySearchResults,
    memorySearchScopes,
    readingKnowledge,
    reindexingKnowledge,
    savingMemory,
    selectedMemory,
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
    setVaultSearchQuery,
    setVaultSearchScope,
    setMemoryDeleteTarget,
    setMemorySearchQuery,
    setMemorySearchScopes,
    searchingMemory,
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
        step?: 'browse' | 'write' | 'feedback' | 'govern' | 'source' | 'discover'
        query?: string
        scope?: string
      }>).detail
      if (detail?.tab === 'memory') {
        setActiveTab('memory')
        if (detail.step === 'browse' || detail.step === 'write' || detail.step === 'feedback') {
          setMemoryStep(detail.step)
        } else {
          setMemoryStep(detail.messageId ? 'feedback' : 'browse')
        }
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
      body: '这里先解决最基础的问题：你上传了什么、内容是什么、向量状态怎么样、能不能删除。召回测试单独放在第二步，不和上传列表混在一起。',
      next: '默认先看资料列表：上次上传、内容、删除、向量状态都在这里。',
    }
    : {
      title: 'AI 记忆',
      body: '这里采用 Hermes-style 保留逻辑：完整会话历史用于审计，文件记忆只展示当前 session 的会话状态、成功经验、错误反馈和资产画像。',
      next: '知识库/RAG 可以全局共享；AI 会话记忆严格按 session 隔离，审计归档不会自动进入提示词。',
    }
  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          title="知识库"
          description="资料库/RAG 用于全局共享知识；AI 会话记忆只属于当前 session，互不串用。"
          actions={(
            <>
            {activeTab === 'documents' && (
              <>
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
                  onClick={() => setMemoryStep('feedback')}
                  className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors"
                >
                  反馈追踪
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
              setDocumentStep('source')
            } else {
              setMemoryStep('browse')
            }
          }}
        />

        <section className="mb-4 grid gap-3 lg:grid-cols-2">
          <div className="rounded-lg border border-ops-success/25 bg-ops-success/5 px-4 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ops-success/80">共享范围</div>
            <div className="mt-1 text-sm font-semibold text-ops-text">知识库 / RAG 全局共享</div>
            <p className="mt-1 text-xs leading-5 text-ops-subtext">
              上传资料、原文预览、向量索引和 RAG 召回面向整个系统，所有会话都可以按权限检索这些资料。
            </p>
          </div>
          <div className="rounded-lg border border-ops-accent/25 bg-ops-accent/5 px-4 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ops-accent/80">隔离范围</div>
          <div className="mt-1 text-sm font-semibold text-ops-text">AI 会话记忆按 session 隔离</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
              点赞、点踩、画像和成功经验只进入当前会话；完整轨迹保留用于审计，压缩后的成功经验/错误反馈才会被当前会话召回。
          </p>
          </div>
        </section>


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
              <div className="grid gap-2 md:grid-cols-2">
                {([
                  ['source', '资料列表', `${files.length} 份资料`, '上传、查看、删除'],
                  ['discover', '召回测试', `${vaultSearchResults.length} 条命中`, '验证知识能否命中'],
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
                      下一步：RAG 召回测试
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
                <aside className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                  <div className="text-sm font-semibold text-ops-text">召回测试怎么看</div>
                  <div className="mt-3 space-y-2 text-xs leading-5 text-ops-subtext">
                    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">
                      输入问题后，系统会返回命中的原文、摘要或来源记录。能看到来源，才算可追溯。
                    </div>
                    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">
                      召回率不伪造百分比，先看“命中数量、证据相关性、来源覆盖”。需要更准时，优先补资料或重建向量。
                    </div>
                    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">
                      如果资料已上传但没有命中，先回到资料列表确认向量状态，再点“重建向量”。
                    </div>
                  </div>
                </aside>
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
                  ['browse', '记忆列表', `${memoryItems.length} 条文件记忆`, '状态/经验/反馈'],
                  ['write', '新增/搜索', `${memorySearchResults.length} 条检索命中`, '写入当前 session'],
                  ['feedback', '反馈追踪', `${sessionMemoryActivity?.summary.promoted_count || 0}/${sessionMemoryActivity?.summary.rejected_count || 0}`, '本会话反馈'],
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
                        当前会话的点赞、资产画像和有效经验沉淀后，会在这里形成可追溯的文件记忆。
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
                  <div className="text-sm font-semibold text-ops-text">简单记忆规则</div>
                  <p className="mt-2 text-xs leading-5 text-ops-subtext">
                    点赞代表这条回答值得沉淀到当前会话；点踩代表这条回答不要作为成功经验，只作为本会话“避免这样做”的纠错记忆。
                  </p>
                  <button
                    type="button"
                    onClick={() => setMemoryStep('feedback')}
                    className="mt-4 rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                  >
                    查看本会话反馈
                  </button>
                </aside>
              </div>
            )}

            {memoryStep === 'feedback' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
                <SessionMemoryActivityPanel
                  activity={sessionMemoryActivity}
                  focusMessageId={memoryFocusMessageId}
                  loading={sessionMemoryActivityLoading}
                  onFocusMessage={handleFocusChatMessage}
                  onReload={() => void loadSessionMemoryActivity()}
                />
                <aside className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                  <div className="text-sm font-semibold text-ops-text">反馈和会话输出怎么对应</div>
                  <div className="mt-3 space-y-2 text-xs leading-5 text-ops-subtext">
                    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">点“定位输出”会回到会话里的对应 AI 回答。</div>
                    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">点赞会加强当前会话成功经验，点踩只保留为本会话纠错提醒。</div>
                    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">没有点过赞踩也没关系，辅助模型仍会根据当前会话上下文沉淀已验证的成功经验。</div>
                  </div>
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
