interface ReadWriteConfirmation {
  sessionId: string
  message: string
  remember: boolean
}

interface ReadWriteConfirmModalProps {
  confirmation: ReadWriteConfirmation
  onRememberChange: (remember: boolean) => void
  onClose: () => void
  onConfirm: () => void
}

export default function ReadWriteConfirmModal({
  confirmation,
  onRememberChange,
  onClose,
  onConfirm,
}: ReadWriteConfirmModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 z-30 flex items-center justify-center">
      <div className="bg-ops-panel border border-ops-alert/40 rounded-xl p-5 w-[460px] shadow-2xl">
        <h3 className="text-base font-semibold text-ops-alert">读写模式确认</h3>
        <p className="text-sm text-ops-subtext mt-2 leading-relaxed">
          当前会话已开启读写权限。AI 可能调用会改变目标系统状态的工具；高危工具仍会走后端审批。
        </p>
        <pre className="mt-3 max-h-32 overflow-y-auto whitespace-pre-wrap break-all bg-ops-dark border border-ops-surface0 rounded-lg p-2 text-xs text-ops-text">
          {confirmation.message}
        </pre>
        <label className="mt-3 flex items-center gap-2 text-sm text-ops-text">
          <input
            type="checkbox"
            checked={confirmation.remember}
            onChange={(event) => onRememberChange(event.target.checked)}
            className="accent-ops-accent"
          />
          本会话不再提示
        </label>
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm bg-ops-alert text-white rounded-lg font-medium hover:bg-ops-alert/80 transition-colors"
          >
            确认发送
          </button>
        </div>
      </div>
    </div>
  )
}
