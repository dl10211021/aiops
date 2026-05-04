import { useEffect, useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import { useStore } from '@/store'
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
  MemoryQualityPanel,
  MemoryReviewPanel,
  MemorySearchPanel,
  SessionMemoryActivityPanel,
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
  const setView = useStore((state) => state.setView)
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('documents')
  const [documentStep, setDocumentStep] = useState<'source' | 'compile' | 'review' | 'discover'>('source')
  const [memoryStep, setMemoryStep] = useState<'browse' | 'write' | 'govern'>('browse')
  const [memoryFocusMessageId, setMemoryFocusMessageId] = useState<string | number | null>(null)
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
    loadSessionMemoryActivity,
    loading,
    memoryDeleteTarget,
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

  useEffect(() => {
    const handleKnowledgeTarget = (event: Event) => {
      const detail = (event as CustomEvent<{
        tab?: KnowledgeTab
        messageId?: string | number
        step?: 'browse' | 'write' | 'govern' | 'source' | 'compile' | 'review' | 'discover'
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
        setDocumentStep(
          detail.step === 'source' || detail.step === 'compile' || detail.step === 'review' || detail.step === 'discover'
            ? detail.step
            : 'discover',
        )
      }
    }
    window.addEventListener('opscore:knowledge-target', handleKnowledgeTarget)
    return () => {
      window.removeEventListener('opscore:knowledge-target', handleKnowledgeTarget)
    }
  }, [loadMemories, loadSessionMemoryActivity])

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
      body: '这里管理上传资料、Wiki 知识和搜索图谱。资料先保存原文，需要时再让 AI 生成 Wiki。',
      next: '简单管理资料和 Wiki。',
    }
    : {
      title: 'AI 记忆',
      body: '这里管理 AI 已经记住的经验、偏好和资产画像。好的回答可以沉淀，错误回答只做纠错记录。',
      next: '查看、新增、管理记忆。',
    }
  const knowledgeHealth = [
    ['原始资料', `${files.length}`, '保存原文，不被 AI 改写'],
    ['待编译', `${compileQueueItems.length}`, '等待生成 Wiki 草稿'],
    ['待整理', `${candidateItems.length}`, '人工确认后才能进入Wiki 知识'],
    ['Wiki 知识', `${articleItems.length}`, '可搜索、可关联、可引用'],
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
          description="统一管理资料、Wiki 知识和 AI 记忆，支持离线部署、检索和追溯。"
          actions={(
            <>
            {activeTab === 'documents' && (
              <>
                <button
                  onClick={handleExportKnowledgeVault}
                  disabled={exportingVault}
                  className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {exportingVault ? '导出中...' : '导出资料库'}
                </button>
                <label className={`cursor-pointer bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors ${importingVault ? 'pointer-events-none opacity-50' : ''}`}>
                  {importingVault ? '导入中...' : '导入资料库'}
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
              setDocumentStep('source')
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
                  ['source', '资料库', `${files.length} 份资料`, '上传和查看资料'],
                  ['compile', '生成 Wiki', `${compileQueueItems.length} 个待处理`, '让 AI 生成 Wiki 草稿'],
                  ['review', 'Wiki 知识', `${candidateItems.length} 个草稿 / ${articleItems.length} 篇 Wiki`, '整理和查看 Wiki'],
                  ['discover', '搜索图谱', `${vaultSearchResults.length} 条命中`, '搜索资料和关联图谱'],
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
                    <div className="text-sm font-semibold text-ops-text">资料库说明</div>
                    <div className="mt-3 space-y-2 text-xs leading-5 text-ops-subtext">
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">原始资料会保留，不会被 AI 修改。</div>
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">需要时让 AI 生成 Wiki 草稿。</div>
                      <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 p-3">后续再进入生成 Wiki，这里只负责保存资料。</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDocumentStep('compile')}
                      className="mt-4 w-full rounded-md border border-ops-accent/45 px-3 py-2 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
                    >
                      下一步：生成 Wiki
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
                    辅助模型把原始资料整理成候选 Wiki。候选不会直接进入长期知识，必须到下一步整理知识。
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
                      去整理知识
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
                    <div className="text-sm font-semibold text-ops-text">整理完成后做什么？</div>
                    <p className="mt-2 text-xs leading-5 text-ops-subtext">
                      Wiki 页面会进入检索和图谱，后续会话和记忆都能从这里追溯来源。
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

