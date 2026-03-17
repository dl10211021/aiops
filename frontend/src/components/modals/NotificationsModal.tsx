import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getNotificationConfig, updateNotificationConfig, testNotificationChannel } from '@/api/client'

export default function NotificationsModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [config, setConfig] = useState({
    wechat_enabled: true, wechat_webhook: '',
    dingtalk_enabled: true, dingtalk_webhook: '',
    email_enabled: true, email_address: '',
    smtp_server: '', smtp_port: 465, smtp_user: '', smtp_pass: '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getNotificationConfig().then((r) => {
      setConfig((prev) => ({ ...prev, ...r.data }))
    }).catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateNotificationConfig(config)
      addToast('告警配置已保存', 'success')
      closeModal()
    } catch {
      addToast('保存失败', 'error')
    }
    setSaving(false)
  }

  const handleTest = async (channel: string) => {
    try {
      const res = await testNotificationChannel(channel)
      addToast(res.message, res.status === 'success' ? 'success' : 'error')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '测试失败', 'error')
    }
  }

  const inputCls = "w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[520px] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">🔔 告警通道配置</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>

        <div className="space-y-5">
          {/* WeChat */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <label className="flex items-center gap-2 text-sm text-ops-text">
                <input type="checkbox" checked={config.wechat_enabled}
                  onChange={(e) => setConfig({ ...config, wechat_enabled: e.target.checked })} className="accent-ops-accent" />
                企业微信
              </label>
              <button onClick={() => handleTest('wechat')} className="text-xs text-ops-accent hover:underline">测试</button>
            </div>
            <input value={config.wechat_webhook} onChange={(e) => setConfig({ ...config, wechat_webhook: e.target.value })}
              className={inputCls} placeholder="Webhook URL" />
          </section>

          {/* DingTalk */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <label className="flex items-center gap-2 text-sm text-ops-text">
                <input type="checkbox" checked={config.dingtalk_enabled}
                  onChange={(e) => setConfig({ ...config, dingtalk_enabled: e.target.checked })} className="accent-ops-accent" />
                钉钉
              </label>
              <button onClick={() => handleTest('dingtalk')} className="text-xs text-ops-accent hover:underline">测试</button>
            </div>
            <input value={config.dingtalk_webhook} onChange={(e) => setConfig({ ...config, dingtalk_webhook: e.target.value })}
              className={inputCls} placeholder="Webhook URL" />
          </section>

          {/* Email */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <label className="flex items-center gap-2 text-sm text-ops-text">
                <input type="checkbox" checked={config.email_enabled}
                  onChange={(e) => setConfig({ ...config, email_enabled: e.target.checked })} className="accent-ops-accent" />
                邮件
              </label>
              <button onClick={() => handleTest('email')} className="text-xs text-ops-accent hover:underline">测试</button>
            </div>
            <div className="space-y-2">
              <input value={config.email_address} onChange={(e) => setConfig({ ...config, email_address: e.target.value })}
                className={inputCls} placeholder="收件人邮箱" />
              <div className="grid grid-cols-2 gap-2">
                <input value={config.smtp_server} onChange={(e) => setConfig({ ...config, smtp_server: e.target.value })}
                  className={inputCls} placeholder="SMTP 服务器" />
                <input type="number" value={config.smtp_port} onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value) || 465 })}
                  className={inputCls} placeholder="端口" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input value={config.smtp_user} onChange={(e) => setConfig({ ...config, smtp_user: e.target.value })}
                  className={inputCls} placeholder="SMTP 用户名" />
                <input type="password" value={config.smtp_pass} onChange={(e) => setConfig({ ...config, smtp_pass: e.target.value })}
                  className={inputCls} placeholder="SMTP 密码" />
              </div>
            </div>
          </section>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors">
            {saving ? '保存中...' : '💾 保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
