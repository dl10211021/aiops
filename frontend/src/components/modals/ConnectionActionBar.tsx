interface ConnectionActionBarProps {
  canSubmitAsset: boolean
  connecting: boolean
  testing: boolean
  onConnect: () => void
  onSaveOnly: () => void
  onTest: () => void
}

export default function ConnectionActionBar({
  canSubmitAsset,
  connecting,
  testing,
  onConnect,
  onSaveOnly,
  onTest,
}: ConnectionActionBarProps) {
  const isEditingAsset = typeof window !== 'undefined' && Boolean(window.sessionStorage.getItem('asset_editing_id'))

  return (
    <div className="flex shrink-0 justify-between border-t border-ops-surface0 bg-ops-panel px-6 py-4">
      <button
        onClick={onSaveOnly}
        disabled={connecting || !canSubmitAsset}
        className="rounded-lg bg-ops-surface0 px-4 py-2 text-sm text-ops-subtext transition-colors hover:text-ops-text disabled:opacity-40"
      >
        {isEditingAsset ? '保存修改' : '保存资产'}
      </button>
      <div className="flex gap-2">
        <button
          onClick={onTest}
          disabled={testing || !canSubmitAsset}
          className="rounded-lg bg-ops-surface0 px-4 py-2 text-sm text-ops-subtext transition-colors hover:text-ops-text disabled:opacity-40"
        >
          {testing ? '测试中...' : '测试连接'}
        </button>
        <button
          onClick={onConnect}
          disabled={connecting || !canSubmitAsset}
          className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark transition-colors hover:bg-ops-accent/80 disabled:opacity-40"
        >
          {connecting ? '连接中...' : '连接并打开会话'}
        </button>
      </div>
    </div>
  )
}
