import { useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import {
  KnowledgeDeleteDialog,
  KnowledgeEmptyState,
  KnowledgeFileCard,
  KnowledgeTabs,
  KnowledgeUploadButton,
  MemoryCreatePanel,
  MemoryDeleteDialog,
  MemoryDetailPanel,
  MemoryItemCard,
  MemoryPendingConflictsPanel,
  MemoryReviewPanel,
  MemorySearchPanel,
  MemoryStoresPanel,
  MemoryVersionsPanel,
  KnowledgeCompileQueuePanel,
  KnowledgeVaultSearchPanel,
  KnowledgeVaultGraphPanel,
  KnowledgeCandidatePanel,
  KnowledgeCandidateEditor,
  KnowledgeArticlePanel,
  KnowledgeArticleViewer,
  type KnowledgeTab,
} from './KnowledgeBaseParts'
import { useKnowledgeBaseData } from './useKnowledgeBaseData'

export default function KnowledgeBase() {
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('documents')
  const [documentStep, setDocumentStep] = useState<'source' | 'compile' | 'review' | 'discover'>('source')
  const [memoryStep, setMemoryStep] = useState<'browse' | 'write' | 'govern'>('browse')
  const {
    deleteTarget,
    deletingMemory,
    creatingMemory,
    deleting,
    error,
    exportingMemory,
    exportingVault,
    importingVault,
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
    loadingVaultGraph,
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
  } = useKnowledgeBaseData()

  const handleRefresh = () => {
    if (activeTab === 'memory') {
      void loadMemories()
    } else {
      void loadFiles()
    }
  }

  const handleOpenMemoryPath = (path: string) => {
    const item = memoryItems.find((candidate) => candidate.path === path)
    if (item) void handleOpenMemory(item)
  }

  const visibleError = activeTab === 'documents' ? error : memoryError
  const friendlyError = visibleError === 'Not Found'
    ? '后台接口返回 Not Found，通常是服务未加载最新路由或需要重启。页面功能已保留，可先刷新或重启服务后再试。'
    : visibleError
  const documentStepGuide = {
    source: {
      title: '当前在做：资料入库',
      body: '先把原始文件安全保存下来，不让 AI 直接改原文。这里关注来源、格式和留底。',
      next: '下一步让辅助模型编译候选 Wiki。',
    },
    compile: {
      title: '当前在做：AI 编译',
      body: '辅助模型把原始资料压缩成候选知识页，只生成候选，不直接写入正式知识。',
      next: '下一步人工审核候选内容。',
    },
    review: {
      title: '当前在做：审核入库',
      body: '人在这里确认事实、来源和可复用性，只有通过审核的内容才进入正式 Vault。',
      next: '下一步通过检索和图谱追溯知识。',
    },
    discover: {
      title: '当前在做：检索追溯',
      body: '正式知识、来源证据和双链关系集中在这里，用于会话引用、审计和复盘。',
      next: '需要新增资料时回到资料入库。',
    },
  }[documentStep]
  const memoryStepGuide = {
    browse: {
      title: '当前在做：浏览记忆',
      body: '这里查看已经沉淀的文件记忆，包括成功经验、用户偏好、资产画像和规则。',
      next: '没有合适记忆时进入写入与检索。',
    },
    write: {
      title: '当前在做：写入与检索',
      body: '把新的可靠经验写成文件记忆，或检索已有记忆验证 AI 是否能找到正确上下文。',
      next: '下一步处理冲突、复核和版本。',
    },
    govern: {
      title: '当前在做：审计治理',
      body: '错误反馈、冲突记忆、过期经验和版本记录都在这里处理，避免记忆污染。',
      next: '治理完成后回到浏览记忆。',
    },
  }[memoryStep]
  const activeStepGuide = activeTab === 'documents' ? documentStepGuide : memoryStepGuide
  const knowledgeHealth = [
    ['原始资料', `${files.length}`, '只读留底，不被 AI 改写'],
    ['待编译', `${compileQueueItems.length}`, '等待辅助模型生成候选 Wiki'],
    ['待审核', `${candidateItems.length}`, '人工确认后才能进入正式知识'],
    ['正式知识', `${articleItems.length}`, '可被检索、图谱、会话引用'],
  ]
  const memoryHealth = [
    ['记忆库', `${memoryStores.length}`, '全局、会话、资产、主机、类型'],
    ['文件记忆', `${memoryItems.length}`, '成功经验和用户确认事实'],
    ['待治理', `${memoryPendingConflicts.length + memoryReviewItems.length}`, '冲突、过期、反馈待处理'],
    ['历史版本', `${memoryVersions.length}`, '可审计、可恢复、可脱敏'],
  ]

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          title="知识库"
          description="统一管理 Obsidian 兼容 Vault、原始资料、AI 编译队列与长期记忆，支持离线部署、审计和追溯。"
          actions={(
            <>
            {activeTab === 'documents' && (
              <>
                <button
                  onClick={handleExportKnowledgeVault}
                  disabled={exportingVault}
                  className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {exportingVault ? '导出中...' : '导出 Vault'}
                </button>
                <label className={`cursor-pointer bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors ${importingVault ? 'pointer-events-none opacity-50' : ''}`}>
                  {importingVault ? '导入中...' : '导入 Vault'}
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
                  审计治理
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

        <section className="mb-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-ops-accent/80">Knowledge Vault</div>
                <h3 className="mt-1 text-base font-semibold text-ops-text">知识库负责“可信资料”</h3>
                <p className="mt-1 text-sm leading-6 text-ops-subtext">
                  只沉淀文档、巡检报告、Runbook、故障案例、资产画像和可追溯证据。必须先审核，再进入正式知识。
                </p>
              </div>
              <span className="rounded-full border border-ops-accent/30 px-2 py-1 text-xs text-ops-accent">固定四步</span>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-4">
              {knowledgeHealth.map(([label, value, hint]) => (
                <div key={label} className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-3">
                  <div className="text-[11px] text-ops-overlay">{label}</div>
                  <div className="mt-1 text-xl font-semibold text-ops-text">{value}</div>
                  <div className="mt-1 text-[11px] leading-4 text-ops-subtext">{hint}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-ops-success/80">Agent Memory</div>
                <h3 className="mt-1 text-base font-semibold text-ops-text">记忆负责“成功经验”</h3>
                <p className="mt-1 text-sm leading-6 text-ops-subtext">
                  只保存用户点赞、人工确认、资产复盘和可复用经验；差评、冲突、过期内容进入治理，不进入长期记忆。
                </p>
              </div>
              <span className="rounded-full border border-ops-success/30 px-2 py-1 text-xs text-ops-success">文件记忆</span>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-4">
              {memoryHealth.map(([label, value, hint]) => (
                <div key={label} className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-3">
                  <div className="text-[11px] text-ops-overlay">{label}</div>
                  <div className="mt-1 text-xl font-semibold text-ops-text">{value}</div>
                  <div className="mt-1 text-[11px] leading-4 text-ops-subtext">{hint}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mb-4 rounded-lg border border-ops-accent/20 bg-gradient-to-r from-ops-accent/10 via-ops-panel/70 to-ops-dark/30 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-ops-accent/80">
                {activeTab === 'documents' ? 'Vault 工作流' : 'AI 记忆工作流'}
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
                  ['source', '1. 资料入库', `${files.length} 份原始资料`, '上传、导入、留底'],
                  ['compile', '2. AI 编译', `${compileQueueItems.length} 个待处理`, '生成候选 Wiki'],
                  ['review', '3. 审核入库', `${candidateItems.length} 个候选 / ${articleItems.length} 篇正式`, '人工确认可信知识'],
                  ['discover', '4. 检索追溯', `${vaultSearchResults.length} 条命中`, '搜索、图谱、证据链'],
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
                  {files.length > 0 ? (
                    <div className="grid gap-2 2xl:grid-cols-2">
                      {files.map((file) => (
                        <KnowledgeFileCard key={file.filename} file={file} onDelete={setDeleteTarget} />
                      ))}
                    </div>
                  ) : (
                    <KnowledgeEmptyState uploading={uploading} onUpload={handleUpload} />
                  )}
                </section>
                <aside className="space-y-3">
                  <div className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                    <div className="text-sm font-semibold text-ops-text">资料入库只做三件事</div>
                    <div className="mt-3 space-y-2 text-xs leading-5 text-ops-subtext">
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">保存原始资料，不让 AI 改原文。</div>
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">生成 source session，记录来源路径和状态。</div>
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">后续再进入 AI 编译，不在这里混杂审核和检索。</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDocumentStep('compile')}
                      className="mt-4 w-full rounded-md border border-ops-accent/45 px-3 py-2 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                    >
                      下一步：AI 编译
                    </button>
                  </div>
                </aside>
              </div>
            )}

            {documentStep === 'compile' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
                <KnowledgeCompileQueuePanel
                  compilingSourceSession={compilingSourceSession}
                  items={compileQueueItems}
                  onCompile={handleCompileKnowledgeSource}
                />
                <aside className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                  <div className="text-sm font-semibold text-ops-text">这一阶段只负责生成候选</div>
                  <p className="mt-2 text-xs leading-5 text-ops-subtext">
                    辅助模型把原始资料整理成候选 Wiki。候选不会直接进入长期知识，必须到下一步人工审核。
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setDocumentStep('source')}
                      className="rounded-md border border-ops-surface0 px-3 py-1.5 text-xs font-semibold text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
                    >
                      返回入库
                    </button>
                    <button
                      type="button"
                      onClick={() => setDocumentStep('review')}
                      className="rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                    >
                      去审核入库
                    </button>
                  </div>
                </aside>
              </div>
            )}

            {documentStep === 'review' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(340px,0.55fr)_minmax(0,1fr)]">
                <section className="space-y-4">
                  <KnowledgeCandidatePanel
                    approvingSourceSession={approvingSourceSession}
                    items={candidateItems}
                    openingCandidate={openingCandidate}
                    onApprove={handleApproveKnowledgeCandidate}
                    onOpen={handleOpenKnowledgeCandidate}
                  />
                  <KnowledgeArticlePanel
                    items={articleItems}
                    openingArticle={openingArticle}
                    onOpen={handleOpenKnowledgeArticle}
                  />
                </section>
                <section className="space-y-4">
                  <KnowledgeCandidateEditor
                    draft={candidateDraft}
                    candidate={selectedCandidate}
                    saving={savingCandidate}
                    onDraftChange={setCandidateDraft}
                    onSave={handleSaveKnowledgeCandidate}
                  />
                  <KnowledgeArticleViewer article={selectedArticle} />
                  <div className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
                    <div className="text-sm font-semibold text-ops-text">审核完成后做什么？</div>
                    <p className="mt-2 text-xs leading-5 text-ops-subtext">
                      正式文章会进入检索和图谱，后续会话、记忆和审计都从这里追溯证据。
                    </p>
                    <button
                      type="button"
                      onClick={() => setDocumentStep('discover')}
                      className="mt-4 rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                    >
                      下一步：检索追溯
                    </button>
                  </div>
                </section>
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
                  ['browse', '1. 浏览记忆', `${memoryItems.length} 条文件记忆`, '查看、编辑、删除'],
                  ['write', '2. 写入与检索', `${memorySearchResults.length} 条检索命中`, '新建、搜索、验证'],
                  ['govern', '3. 审计治理', `${memoryPendingConflicts.length + memoryReviewItems.length} 项待处理`, '冲突、复核、版本'],
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
                        会话点赞、资产画像和人工确认经验沉淀后，会在这里形成 Claude 风格文件记忆。
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
                    冲突、过期、失败反馈都集中到审计治理，避免错误经验长期污染 AI。
                  </p>
                  <button
                    type="button"
                    onClick={() => setMemoryStep('govern')}
                    className="mt-4 rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                  >
                    下一步：审计治理
                  </button>
                </aside>
              </div>
            )}

            {memoryStep === 'govern' && (
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.75fr)]">
                <section className="space-y-4">
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
