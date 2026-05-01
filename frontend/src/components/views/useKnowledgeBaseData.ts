import type { ChangeEvent } from 'react'
import { useCallback, useEffect, useState } from 'react'
import {
  deleteKnowledgeDocument,
  listKnowledgeDocuments,
  uploadKnowledgeDocument,
} from '@/api/knowledge'
import { useStore } from '@/store'
import type { KnowledgeFile } from '@/types'
import { isAcceptedKnowledgeFile } from './knowledgeBaseModel'

export function useKnowledgeBaseData() {
  const addToast = useStore((s) => s.addToast)
  const [files, setFiles] = useState<KnowledgeFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeFile | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  useEffect(() => {
    void loadFiles()
  }, [loadFiles])

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

  return {
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
  }
}
