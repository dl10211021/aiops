import { useSessionActions } from './useSessionActions'

export default function SessionActionsModal() {
  const {
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
  } = useSessionActions()

  return (
    <div className="ops-modal-backdrop" onClick={closeModal}>
      <div className="ops-modal-surface flex max-h-[92vh] w-[460px] max-w-[94vw] flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="ops-modal-header">
          <div>
            <h2 className="ops-modal-title">会话操作</h2>
            <p className="ops-modal-description">生成画像、导出记录、Webhook 发送和危险清理都集中在这里。</p>
          </div>
          <button onClick={closeModal} className="ops-icon-button" title="关闭">×</button>
        </div>
        <div className="ops-modal-body p-5">
        {confirmClear ? (
          <div className="ops-data-panel border-ops-alert/35 bg-ops-alert/8 p-3">
            <div className="text-sm font-semibold text-ops-alert">确认清空聊天记录</div>
            <p className="mt-2 text-xs leading-5 text-ops-subtext">
              将清空当前会话的前端显示和后端历史记录。此操作不会断开资产连接，但清空后无法从页面恢复。
            </p>
            <div className="ops-data-panel mt-3 px-3 py-2 text-xs text-ops-text">
              {session?.remark || session?.host || currentSessionId || '-'}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setConfirmClear(false)}
                disabled={busy}
                className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
              >
                取消
              </button>
              <button
                onClick={handleClearHistory}
                disabled={busy}
                className="ops-danger-action px-3 py-1.5 text-xs disabled:opacity-50"
              >
                {busy ? '清空中...' : '确认清空'}
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="space-y-1.5">
              <button onClick={handleGenerateProfile}
                disabled={busy}
                className="ops-muted-action w-full px-3 py-2 text-left text-sm disabled:opacity-50">
                生成资产画像
              </button>
              <button onClick={handleExport}
                className="ops-muted-action w-full px-3 py-2 text-left text-sm">
                导出聊天记录 (Markdown)
              </button>
              <button onClick={() => setConfirmClear(true)}
                className="ops-danger-action w-full px-3 py-2 text-left text-sm">
                清空聊天记录
              </button>
            </div>
            <div className="ops-data-panel mt-4 p-3">
              <div className="mb-2 text-xs font-semibold text-ops-text">发送到 Webhook</div>
              <input
                value={webhookUrl}
                onChange={(event) => {
                  setWebhookUrl(event.target.value)
                  setWebhookPreview(null)
                }}
                placeholder="https://example.com/webhook"
                className="ops-control w-full px-3 py-2 text-xs"
              />
              <div className="mt-2 grid grid-cols-2 gap-2">
                <select
                  value={webhookPayload}
                  onChange={(event) => {
                    setWebhookPayload(event.target.value as typeof webhookPayload)
                    setWebhookPreview(null)
                  }}
                  className="ops-control px-2 py-2 text-xs"
                >
                  <option value="profile">资产画像</option>
                  <option value="summary">画像+摘要</option>
                  <option value="markdown">完整 Markdown</option>
                </select>
                <select
                  value={webhookChannel}
                  onChange={(event) => {
                    setWebhookChannel(event.target.value as typeof webhookChannel)
                    setWebhookPreview(null)
                  }}
                  className="ops-control px-2 py-2 text-xs"
                >
                  <option value="generic">通用 JSON</option>
                  <option value="wechat">企业微信</option>
                  <option value="dingtalk">钉钉</option>
                </select>
              </div>
              <label className="ops-data-panel mt-2 flex items-start gap-2 px-2 py-2 text-[11px] leading-4 text-ops-subtext">
                <input
                  type="checkbox"
                  checked={allowPrivateWebhook}
                  onChange={(event) => {
                    setAllowPrivateWebhook(event.target.checked)
                    setWebhookPreview(null)
                  }}
                  className="mt-0.5 accent-ops-accent"
                />
                允许发送到内网或保留地址。仅在确认这是公司内部可信 Webhook 时开启。
              </label>
              {webhookPreview && (
                <div className="ops-data-panel mt-2 p-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                    <span className="font-semibold text-ops-text">发送预览</span>
                    <span className="text-ops-overlay">{webhookPreview.target.host}:{webhookPreview.target.port} · {webhookPreview.payload.bytes} bytes</span>
                  </div>
                  {webhookPreview.target.private_target && (
                    <div className="mt-1 rounded border border-ops-alert/35 bg-ops-alert/10 px-2 py-1 text-[11px] text-ops-alert">
                      目标解析到内网或保留地址，发送前请确认边界。
                    </div>
                  )}
                  <pre className="ops-data-panel mt-2 max-h-28 overflow-y-auto whitespace-pre-wrap break-all p-2 text-[10px] leading-4 text-ops-subtext">
                    {webhookPreview.payload.preview}
                  </pre>
                </div>
              )}
              {webhookHistory.length > 0 && (
                <div className="ops-data-panel mt-2 p-2">
                  <div className="mb-1 text-[11px] font-semibold text-ops-overlay">最近发送</div>
                  <div className="space-y-1">
                    {webhookHistory.slice(0, 3).map((item) => (
                      <div key={item.id} className="flex items-center justify-between gap-2 text-[11px]">
                        <span className="truncate text-ops-subtext">{item.webhook_host} · {item.payload_type}</span>
                        <span className={item.status === 'success' ? 'text-ops-success' : 'text-ops-alert'}>
                          {item.status === 'success' ? '成功' : '失败'} {item.http_status || ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <button
                onClick={handlePreviewWebhook}
                disabled={busy}
                className="ops-muted-action mt-2 w-full px-3 py-2 text-xs disabled:opacity-50"
              >
                {busy ? '处理中...' : '预览发送内容'}
              </button>
              <button
                onClick={handleSendWebhook}
                disabled={busy || !webhookPreview}
                className="ops-primary-action mt-2 w-full px-3 py-2 text-xs disabled:opacity-50"
              >
                {busy ? '发送中...' : '确认发送当前会话'}
              </button>
            </div>
            <button onClick={closeModal} className="mt-3 w-full py-1 text-center text-xs text-ops-overlay hover:text-ops-subtext">
              关闭
            </button>
          </>
        )}
        </div>
      </div>
    </div>
  )
}
