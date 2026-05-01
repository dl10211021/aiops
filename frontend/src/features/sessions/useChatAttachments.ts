import { useEffect, useRef, useState } from 'react'
import { useStore } from '@/store'
import {
  appendSessionAttachments,
  attachmentUploadToastMessage,
  parseChatAttachmentFiles,
  selectPreviewFiles,
} from './chatAttachmentUpload'
import type { ChatAttachmentPreview } from './chatTypes'

export function useChatAttachments(currentSessionId: string | null, isStreaming: boolean) {
  const addToast = useStore((state) => state.addToast)
  const [attachmentsBySession, setAttachmentsBySession] = useState<Record<string, ChatAttachmentPreview[]>>({})
  const [uploading, setUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const previewUrlsRef = useRef<Set<string>>(new Set())
  const attachments = currentSessionId ? attachmentsBySession[currentSessionId] || [] : []

  const setSessionAttachments = (next: ChatAttachmentPreview[]) => {
    if (!currentSessionId) return
    setAttachmentsBySession((prev) => ({ ...prev, [currentSessionId]: next }))
  }

  const revokePreviews = (items: ChatAttachmentPreview[]) => {
    for (const item of items) {
      if (item.previewUrl && previewUrlsRef.current.has(item.previewUrl)) {
        URL.revokeObjectURL(item.previewUrl)
        previewUrlsRef.current.delete(item.previewUrl)
      }
    }
  }

  useEffect(() => {
    return () => {
      for (const url of previewUrlsRef.current) URL.revokeObjectURL(url)
      previewUrlsRef.current.clear()
    }
  }, [])

  const handleFiles = async (files: FileList | File[] | null) => {
    if (!files || !currentSessionId) return
    const targetSessionId = currentSessionId
    const { incoming, selected } = selectPreviewFiles(files)
    if (selected.length === 0) return
    setUploading(true)
    try {
      const { failed, parsed } = await parseChatAttachmentFiles(selected, (url) => previewUrlsRef.current.add(url))
      if (parsed.length === 0) {
        throw new Error(failed[0] || '附件解析失败')
      }
      setAttachmentsBySession((prev) => ({
        ...prev,
        [targetSessionId]: appendSessionAttachments(prev[targetSessionId] || [], parsed),
      }))
      const limitTip = incoming.length > selected.length ? `，已按上限取前 ${selected.length} 个` : ''
      const toast = attachmentUploadToastMessage({ failed, limitTip, parsed })
      addToast(toast.message, toast.type)
    } catch (err) {
      addToast(err instanceof Error ? err.message : '附件解析失败', 'error')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const removeAttachment = (id: string) => {
    const target = attachments.find((item) => item.id === id)
    if (target) revokePreviews([target])
    setSessionAttachments(attachments.filter((item) => item.id !== id))
  }

  const handleInputPaste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const pastedFiles = Array.from(event.clipboardData.files || [])
    if (pastedFiles.length === 0 || isStreaming) return
    event.preventDefault()
    void handleFiles(pastedFiles)
  }

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    if (!isStreaming) setIsDragging(true)
  }

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setIsDragging(false)
    }
  }

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    if (isStreaming) return
    const droppedFiles = Array.from(event.dataTransfer.files || [])
    if (droppedFiles.length > 0) void handleFiles(droppedFiles)
  }

  return {
    attachments,
    attachmentsBySession,
    fileInputRef,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleFiles,
    handleInputPaste,
    isDragging,
    removeAttachment,
    revokePreviews,
    setAttachmentsBySession,
    uploading,
  }
}
