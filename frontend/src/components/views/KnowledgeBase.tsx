import { useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import {
  KnowledgeDeleteDialog,
  KnowledgeEmptyState,
  KnowledgeFileCard,
  KnowledgeTabs,
  KnowledgeUploadButton,
  MemoryDeleteDialog,
  MemoryDetailPanel,
  MemoryItemCard,
  MemoryPendingConflictsPanel,
  MemoryReviewPanel,
  MemoryStoresPanel,
  MemoryVersionsPanel,
  type KnowledgeTab,
} from './KnowledgeBaseParts'
import { useKnowledgeBaseData } from './useKnowledgeBaseData'

export default function KnowledgeBase() {
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('documents')
  const {
    deleteTarget,
    deletingMemory,
    deleting,
    error,
    exportingMemory,
    files,
    handleDelete,
    handleDeleteMemory,
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
    setMemoryDraft,
    setMemoryDeleteTarget,
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

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          title="知识库"
          description="统一管理运维文档与 AI 长期记忆，支持检索、删除和审计。"
          actions={(
            <>
            {activeTab === 'documents' && (
              <KnowledgeUploadButton uploading={uploading} onUpload={handleUpload} />
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
          onChange={setActiveTab}
        />

        {(activeTab === 'documents' ? error : memoryError) && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {activeTab === 'documents' ? error : memoryError}
          </div>
        )}

        {activeTab === 'documents' && loading && (
          <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-8 text-center text-sm text-ops-subtext">
            正在加载知识库文档...
          </section>
        )}

        {activeTab === 'documents' && !loading && files.length > 0 ? (
          <div className="grid gap-2 xl:grid-cols-2 2xl:grid-cols-3">
            {files.map((file) => (
              <KnowledgeFileCard key={file.filename} file={file} onDelete={setDeleteTarget} />
            ))}
          </div>
        ) : activeTab === 'documents' && !loading ? (
          <KnowledgeEmptyState uploading={uploading} onUpload={handleUpload} />
        ) : null}

        {activeTab === 'memory' && memoryLoading && (
          <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-8 text-center text-sm text-ops-subtext">
            正在加载 AI 记忆...
          </section>
        )}

        {activeTab === 'memory' && !memoryLoading && (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]">
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
                    当会话产生可复用经验、用户点赞/点踩反馈或资产画像沉淀后，这里会出现 Claude 风格文件记忆。
                  </p>
                </div>
              )}
            </section>
            <aside className="space-y-4">
              <MemoryDetailPanel
                draft={memoryDraft}
                exporting={exportingMemory}
                memory={selectedMemory}
                saving={savingMemory}
                onDraftChange={setMemoryDraft}
                onExport={() => void handleExportMemory()}
                onSave={() => void handleSaveMemory()}
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
              <MemoryStoresPanel stores={memoryStores} />
              <MemoryVersionsPanel
                versions={memoryVersions}
                onRestore={(version) => void handleRestoreMemoryVersion(version)}
              />
            </aside>
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
