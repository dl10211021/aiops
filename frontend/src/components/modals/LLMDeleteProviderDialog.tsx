import type { ProviderConfig } from '@/api/client'

interface LLMDeleteProviderDialogProps {
  target: ProviderConfig
  onCancel: () => void
  onConfirm: () => void
}

export default function LLMDeleteProviderDialog({
  target,
  onCancel,
  onConfirm,
}: LLMDeleteProviderDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={(event) => event.stopPropagation()}>
      <section className="ops-modal-surface w-full max-w-md">
        <div className="ops-modal-header">
          <div className="text-xs font-semibold text-ops-alert">删除模型供应商</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认删除配置</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            删除后该供应商下的模型不会再出现在会话模型选择里，已保存的 API Key 也会从配置中移除。
          </p>
        </div>
        <div className="p-5">
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
            <div className="truncate text-sm font-semibold text-ops-text">{target.name}</div>
            <div className="mt-1 truncate font-mono text-xs text-ops-overlay">{target.base_url || '官方默认端点'}</div>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button
            onClick={onCancel}
            className="ops-muted-action px-4 py-2 text-sm"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="ops-danger-action px-4 py-2 text-sm"
          >
            确认删除
          </button>
        </div>
      </section>
    </div>
  )
}
