import { useState } from 'react'
import {
  clearSessionHistory,
  exportSessionHistory,
  generateSessionProfile,
  getSessionWebhookHistory,
  previewSessionWebhook,
  sendSessionWebhook,
} from '@/api/sessions'
import { useStore } from '@/store'

export type WebhookPreview = Awaited<ReturnType<typeof previewSessionWebhook>>['data']
export type WebhookDelivery = Awaited<ReturnType<typeof getSessionWebhookHistory>>['data']['deliveries'][number]
export type WebhookChannel = 'generic' | 'wechat' | 'dingtalk'
export type WebhookPayload = 'profile' | 'summary' | 'markdown'

export function useSessionActions() {
  const closeModal = useStore((s) => s.closeModal)
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)
  const clearMessages = useStore((s) => s.clearMessages)
  const addToast = useStore((s) => s.addToast)
  const [confirmClear, setConfirmClear] = useState(false)
  const [busy, setBusy] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState(() => localStorage.getItem('opscore_session_webhook_url') || '')
  const [webhookChannel, setWebhookChannel] = useState<WebhookChannel>('generic')
  const [webhookPayload, setWebhookPayload] = useState<WebhookPayload>('profile')
  const [allowPrivateWebhook, setAllowPrivateWebhook] = useState(false)
  const [webhookPreview, setWebhookPreview] = useState<WebhookPreview | null>(null)
  const [webhookHistory, setWebhookHistory] = useState<WebhookDelivery[]>([])

  const session = currentSessionId ? sessions[currentSessionId] : null

  const handleClearHistory = async () => {
    if (!currentSessionId) return
    setBusy(true)
    try {
      await clearSessionHistory(currentSessionId)
      clearMessages(currentSessionId)
      addToast('聊天记录已清空', 'success')
      closeModal()
    } catch {
      addToast('清空失败', 'error')
      setBusy(false)
    }
  }

  const handleExport = async () => {
    if (!currentSessionId) return
    try {
      const res = await exportSessionHistory(currentSessionId)
      if (res.data.markdown) {
        const blob = new Blob([res.data.markdown], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat_${session?.remark || session?.host || currentSessionId}.md`
        a.click()
        URL.revokeObjectURL(url)
        addToast('导出成功', 'success')
      } else {
        addToast('无可导出内容', 'info')
      }
    } catch {
      addToast('导出失败', 'error')
    }
    closeModal()
  }

  const handleGenerateProfile = async () => {
    if (!currentSessionId) return
    setBusy(true)
    try {
      await generateSessionProfile(currentSessionId, undefined, true)
      addToast('资产画像已生成，会话顶部会显示画像面板', 'success')
      closeModal()
    } catch (err) {
      const message = err instanceof Error ? err.message : '资产画像生成失败'
      addToast(message, 'error')
      setBusy(false)
    }
  }

  const webhookParams = () => ({
    webhook_url: webhookUrl.trim(),
    channel: webhookChannel,
    payload_type: webhookPayload,
    title: `OpsCore 会话报告 - ${session?.remark || session?.host || currentSessionId}`,
    allow_private_targets: allowPrivateWebhook,
  })

  const handlePreviewWebhook = async () => {
    if (!currentSessionId) return
    if (!webhookUrl.trim()) {
      addToast('请先填写 Webhook 地址', 'error')
      return
    }
    setBusy(true)
    try {
      localStorage.setItem('opscore_session_webhook_url', webhookUrl.trim())
      const res = await previewSessionWebhook(currentSessionId, webhookParams())
      setWebhookPreview(res.data)
      const history = await getSessionWebhookHistory(currentSessionId, 5)
      setWebhookHistory(history.data.deliveries || [])
      addToast('Webhook 预览已生成，请确认后发送', 'success')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Webhook 预览失败'
      addToast(message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleSendWebhook = async () => {
    if (!currentSessionId) return
    if (!webhookPreview) {
      await handlePreviewWebhook()
      return
    }
    setBusy(true)
    try {
      await sendSessionWebhook(currentSessionId, webhookParams())
      addToast('Webhook 已发送', 'success')
      const history = await getSessionWebhookHistory(currentSessionId, 5)
      setWebhookHistory(history.data.deliveries || [])
      closeModal()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Webhook 发送失败'
      addToast(message, 'error')
      setBusy(false)
    }
  }

  return {
    allowPrivateWebhook,
    busy,
    closeModal,
    confirmClear,
    currentSessionId,
    handleClearHistory,
    handleExport,
    handleGenerateProfile,
    handlePreviewWebhook,
    handleSendWebhook,
    session,
    setAllowPrivateWebhook,
    setConfirmClear,
    setWebhookChannel,
    setWebhookPayload,
    setWebhookPreview,
    setWebhookUrl,
    webhookChannel,
    webhookHistory,
    webhookPayload,
    webhookPreview,
    webhookUrl,
  }
}
