import { useEffect, useState } from 'react'
import {
  getNotificationConfig,
  testNotificationChannel,
  updateNotificationConfig,
} from '@/api/notifications'
import { useStore } from '@/store'

export type NotificationConfig = {
  wechat_enabled: boolean
  wechat_webhook: string
  dingtalk_enabled: boolean
  dingtalk_webhook: string
  email_enabled: boolean
  email_address: string
  smtp_server: string
  smtp_port: number
  smtp_user: string
  smtp_pass: string
}

export type NotificationChannelStatus = {
  channel: string
  label: string
  enabled: boolean
  configured: boolean
  ready: boolean
  status: 'ready' | 'missing_config' | 'disabled' | string
  message: string
  required_fields: string[]
}

const DEFAULT_NOTIFICATION_CONFIG: NotificationConfig = {
  wechat_enabled: true,
  wechat_webhook: '',
  dingtalk_enabled: true,
  dingtalk_webhook: '',
  email_enabled: true,
  email_address: '',
  smtp_server: '',
  smtp_port: 465,
  smtp_user: '',
  smtp_pass: '',
}

export function useNotificationConfig() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [config, setConfig] = useState<NotificationConfig>(DEFAULT_NOTIFICATION_CONFIG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingChannel, setTestingChannel] = useState<string | null>(null)
  const [channels, setChannels] = useState<NotificationChannelStatus[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    getNotificationConfig().then((r) => {
      const data = r.data as Partial<NotificationConfig> & { channels?: NotificationChannelStatus[] }
      setConfig((prev) => ({ ...prev, ...data }))
      setChannels(Array.isArray(data.channels) ? data.channels : [])
    }).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : '加载告警通道配置失败')
    }).finally(() => setLoading(false))
  }, [])

  const updateConfig = (patch: Partial<NotificationConfig>) => {
    setConfig((current) => ({ ...current, ...patch }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateNotificationConfig(config)
      addToast('告警配置已保存', 'success')
      closeModal()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async (channel: string) => {
    setTestingChannel(channel)
    try {
      const res = await testNotificationChannel(channel)
      addToast(res.message, res.status === 'success' ? 'success' : 'error')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '测试失败', 'error')
    } finally {
      setTestingChannel(null)
    }
  }

  return {
    channels,
    closeModal,
    config,
    error,
    handleSave,
    handleTest,
    loading,
    saving,
    testingChannel,
    updateConfig,
  }
}
