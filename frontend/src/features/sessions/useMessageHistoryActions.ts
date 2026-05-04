import { useState } from 'react'
import {
  deleteSessionHistoryMessage,
  feedbackSessionHistoryMessage,
  updateSessionHistoryMessage,
} from '@/api/client'
import { useStore } from '@/store'
import type { ChatMessage } from '@/types'
import { messageMemoryId } from './sessionHistory'

export function useMessageHistoryActions(currentSessionId: string | null) {
  const removeMessage = useStore((state) => state.removeMessage)
  const updateMessage = useStore((state) => state.updateMessage)
  const addToast = useStore((state) => state.addToast)
  const [editingMessage, setEditingMessage] = useState<ChatMessage | null>(null)
  const [editingContent, setEditingContent] = useState('')
  const [editingBusy, setEditingBusy] = useState(false)

  const startEditMessage = (message: ChatMessage) => {
    if (!messageMemoryId(message)) {
      addToast('这条消息还没有写入历史，稍后再试', 'info')
      return
    }
    setEditingMessage(message)
    setEditingContent(message.content)
  }

  const closeEditMessage = () => {
    setEditingMessage(null)
  }

  const saveEditedMessage = async () => {
    const sessionId = currentSessionId
    const message = editingMessage
    const memoryId = message ? messageMemoryId(message) : null
    if (!sessionId || !message || !memoryId) return
    setEditingBusy(true)
    try {
      const res = await updateSessionHistoryMessage(sessionId, memoryId, editingContent)
      updateMessage(sessionId, message.id, (current) => ({
        ...current,
        content: res.data.message.content,
        memoryId: res.data.message._memory_id || memoryId,
        _memory_id: res.data.message._memory_id || memoryId,
      }))
      setEditingMessage(null)
      setEditingContent('')
      addToast('消息已更新', 'success')
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '消息更新失败', 'error')
    }
    setEditingBusy(false)
  }

  const deleteMessage = async (message: ChatMessage) => {
    const sessionId = currentSessionId
    const memoryId = messageMemoryId(message)
    if (!sessionId || !memoryId) {
      addToast('这条消息还没有写入历史，稍后再试', 'info')
      return
    }
    if (!window.confirm('确认删除这段会话内容？删除后刷新页面也不会恢复。')) return
    try {
      await deleteSessionHistoryMessage(sessionId, memoryId)
      removeMessage(sessionId, message.id)
      addToast('消息已删除', 'success')
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '消息删除失败', 'error')
    }
  }

  const feedbackMessage = async (message: ChatMessage, rating: 'up' | 'down') => {
    const sessionId = currentSessionId
    const memoryId = messageMemoryId(message)
    if (!sessionId || !memoryId) {
      addToast('这条 AI 输出还没有写入历史，稍后再试', 'info')
      return
    }
    try {
      const res = await feedbackSessionHistoryMessage(sessionId, memoryId, rating)
      updateMessage(sessionId, message.id, (current) => ({
        ...current,
        feedback: res.data.message.feedback,
        memoryId: res.data.message._memory_id || memoryId,
        _memory_id: res.data.message._memory_id || memoryId,
      }))
      addToast(
        rating === 'up'
          ? '已记录好评：已进入会话记忆，后续复用前仍会实时验证'
          : '已记录差评：只用于纠错审计，不作为成功经验沉淀',
        'success',
      )
      window.dispatchEvent(new CustomEvent('opscore:session-memory-activity-updated', {
        detail: { sessionId, messageId: memoryId, rating },
      }))
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '反馈记录失败', 'error')
    }
  }

  return {
    closeEditMessage,
    deleteMessage,
    editingBusy,
    editingContent,
    editingMessage,
    saveEditedMessage,
    setEditingContent,
    startEditMessage,
    feedbackMessage,
  }
}
