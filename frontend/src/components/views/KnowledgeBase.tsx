import PageHeader from '@/components/layout/PageHeader'
import {
  KnowledgeDeleteDialog,
  KnowledgeEmptyState,
  KnowledgeFileCard,
  KnowledgeUploadButton,
} from './KnowledgeBaseParts'
import { useKnowledgeBaseData } from './useKnowledgeBaseData'

export default function KnowledgeBase() {
  const {
    deleteTarget,
    deleting,
    error,
    files,
    handleDelete,
    handleUpload,
    loadFiles,
    loading,
    setDeleteTarget,
    uploading,
  } = useKnowledgeBaseData()

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          title="知识库"
          description="上传运维文档，AI 将自动学习并在会话和巡检中引用。"
          actions={(
            <>
            <KnowledgeUploadButton uploading={uploading} onUpload={handleUpload} />
            <button
              onClick={() => void loadFiles()}
              className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors"
            >
              刷新
            </button>
            </>
          )}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        {loading && (
          <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-8 text-center text-sm text-ops-subtext">
            正在加载知识库文档...
          </section>
        )}

        {/* File list */}
        {!loading && files.length > 0 ? (
          <div className="grid gap-2 xl:grid-cols-2 2xl:grid-cols-3">
            {files.map((file) => (
              <KnowledgeFileCard key={file.filename} file={file} onDelete={setDeleteTarget} />
            ))}
          </div>
        ) : !loading ? (
          <KnowledgeEmptyState uploading={uploading} onUpload={handleUpload} />
        ) : null}
      </div>
      {deleteTarget && (
        <KnowledgeDeleteDialog
          deleting={deleting}
          target={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete()}
        />
      )}
    </div>
  )
}
