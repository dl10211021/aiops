import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { listKnowledgeDocuments, uploadKnowledgeDocument, deleteKnowledgeDocument } from '@/api/client'
import type { KnowledgeFile } from '@/types'

export default function KnowledgeBase() {
  const addToast = useStore((s) => s.addToast)
  const [files, setFiles] = useState<KnowledgeFile[]>([])
  const [uploading, setUploading] = useState(false)

  const loadFiles = useCallback(async () => {
    try {
      const res = await listKnowledgeDocuments()
      setFiles(res.data.files || [])
    } catch {
      addToast('加载知识库失败', 'error')
    }
  }, [addToast])

  useEffect(() => { loadFiles() }, [loadFiles])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    setUploading(true)
    let successCount = 0
    for (const file of Array.from(fileList)) {
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

  const handleDelete = async (filename: string) => {
    if (!confirm(`确定要删除 ${filename} 吗？`)) return
    try {
      await deleteKnowledgeDocument(filename)
      setFiles(files.filter((f) => f.filename !== filename))
      addToast('文档已删除', 'success')
    } catch {
      addToast('删除失败', 'error')
    }
  }

  const fileIcon = (name: string) => {
    if (name.endsWith('.pdf')) return '📕'
    if (name.endsWith('.md') || name.endsWith('.txt')) return '📄'
    if (name.endsWith('.docx') || name.endsWith('.doc')) return '📘'
    if (name.endsWith('.csv') || name.endsWith('.xlsx')) return '📊'
    return '📁'
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-ops-text">📚 知识库</h1>
            <p className="text-sm text-ops-subtext mt-1">
              上传运维文档，AI 将自动学习并在对话中引用 (RAG)
            </p>
          </div>
          <div className="flex gap-2">
            <label className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors cursor-pointer">
              {uploading ? '上传中...' : '📤 上传文档'}
              <input
                type="file"
                multiple
                accept=".pdf,.txt,.md,.docx,.csv,.xlsx"
                onChange={handleUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>
            <button
              onClick={loadFiles}
              className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors"
            >
              🔄 刷新
            </button>
          </div>
        </div>

        {/* File list */}
        {files.length > 0 ? (
          <div className="space-y-2">
            {files.map((f) => (
              <div
                key={f.filename}
                className="bg-ops-panel border border-ops-surface0 rounded-lg px-4 py-3 flex items-center gap-3 hover:border-ops-accent/40 transition-colors"
              >
                <span className="text-xl">{fileIcon(f.filename)}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-ops-text truncate">{f.filename}</div>
                  <div className="text-xs text-ops-overlay">
                    {f.chunks !== undefined && `${f.chunks} 个向量块`}
                    {f.size !== undefined && ` · ${(f.size / 1024).toFixed(1)} KB`}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(f.filename)}
                  className="text-ops-overlay hover:text-ops-alert text-sm transition-colors"
                  title="删除"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-ops-subtext py-20">
            <div className="text-4xl mb-3">📚</div>
            <p>知识库为空</p>
            <p className="text-xs mt-1">上传 PDF、Markdown、TXT 等文档，AI 将自动学习</p>
          </div>
        )}
      </div>
    </div>
  )
}
