import { ChannelSection, Field, notificationInputClass } from './NotificationChannelSection'
import { useNotificationConfig } from './useNotificationConfig'

export default function NotificationsModal() {
  const {
    closeModal,
    config,
    error,
    handleSave,
    handleTest,
    loading,
    saving,
    testingChannel,
    updateConfig,
  } = useNotificationConfig()

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" onClick={closeModal}>
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 border-b border-ops-surface0 px-6 py-5">
          <div>
            <h2 className="text-lg font-bold text-ops-text">告警通道配置</h2>
            <p className="mt-1 text-sm leading-6 text-ops-subtext">
              用于自动巡检、告警闭环和审批事件通知。建议至少启用一个即时通道和一个邮件归档通道。
            </p>
          </div>
          <button onClick={closeModal} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text">关闭</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
              {error}
            </div>
          )}

          {loading ? (
            <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 py-10 text-center text-sm text-ops-subtext">
              正在加载告警通道配置...
            </div>
          ) : (
            <div className="space-y-4">
              <ChannelSection
                title="企业微信"
                description="适合运维群即时提醒，支持巡检失败、告警升级和审批通知。"
                enabled={config.wechat_enabled}
                onEnabledChange={(enabled) => updateConfig({ wechat_enabled: enabled })}
                onTest={() => void handleTest('wechat')}
                testing={testingChannel === 'wechat'}
              >
                <Field label="机器人 Webhook" value={config.wechat_webhook} onChange={(wechat_webhook) => updateConfig({ wechat_webhook })} className={notificationInputClass} placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
              </ChannelSection>

              <ChannelSection
                title="钉钉"
                description="适合团队群通知和事件分派，建议单独配置 AIOps 告警群。"
                enabled={config.dingtalk_enabled}
                onEnabledChange={(enabled) => updateConfig({ dingtalk_enabled: enabled })}
                onTest={() => void handleTest('dingtalk')}
                testing={testingChannel === 'dingtalk'}
              >
                <Field label="机器人 Webhook" value={config.dingtalk_webhook} onChange={(dingtalk_webhook) => updateConfig({ dingtalk_webhook })} className={notificationInputClass} placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
              </ChannelSection>

              <ChannelSection
                title="邮件"
                description="适合归档巡检报告、审批结果和重大告警闭环记录。"
                enabled={config.email_enabled}
                onEnabledChange={(enabled) => updateConfig({ email_enabled: enabled })}
                onTest={() => void handleTest('email')}
                testing={testingChannel === 'email'}
              >
                <Field label="收件人邮箱" value={config.email_address} onChange={(email_address) => updateConfig({ email_address })} className={notificationInputClass} placeholder="ops@example.com" />
                <div className="grid gap-3 sm:grid-cols-[1fr_120px]">
                  <Field label="SMTP 服务器" value={config.smtp_server} onChange={(smtp_server) => updateConfig({ smtp_server })} className={notificationInputClass} placeholder="smtp.example.com" />
                  <Field label="端口" type="number" value={String(config.smtp_port)} onChange={(smtp_port) => updateConfig({ smtp_port: parseInt(smtp_port) || 465 })} className={notificationInputClass} placeholder="465" />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="SMTP 用户名" value={config.smtp_user} onChange={(smtp_user) => updateConfig({ smtp_user })} className={notificationInputClass} placeholder="ops@example.com" />
                  <Field label="SMTP 密码" type="password" value={config.smtp_pass} onChange={(smtp_pass) => updateConfig({ smtp_pass })} className={notificationInputClass} placeholder="应用专用密码" />
                </div>
              </ChannelSection>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-ops-surface0 bg-ops-dark/45 px-6 py-4">
          <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={handleSave} disabled={saving || loading}
            className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors">
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
