import type { SlashCommand } from '@/types'

export function CommandEditorStatus({
  error,
  readonlyDraft,
}: {
  error: string
  readonlyDraft: boolean
}) {
  return (
    <>
      {error && <div className="mb-3 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-sm text-ops-alert">{error}</div>}
      {readonlyDraft && (
        <div className="mb-3 rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-sm text-ops-subtext">
          当前为查看模式。点击下方“编辑模板”后才会修改内置模板覆盖配置。
        </div>
      )}
    </>
  )
}

export function CommandEditorActions({
  busy,
  current,
  isBuiltinDraft,
  readonlyDraft,
  onBeginEdit,
  onDelete,
  onRestore,
  onSave,
}: {
  busy: boolean
  current: Partial<SlashCommand>
  isBuiltinDraft: boolean
  readonlyDraft: boolean
  onBeginEdit: () => void
  onDelete: (commandId: string) => void
  onRestore: (commandId: string) => void
  onSave: () => void
}) {
  return (
    <div className="mt-5 flex justify-between gap-3 border-t border-ops-surface0 pt-4">
      <button
        onClick={() => current.id && (isBuiltinDraft ? onRestore(current.id) : onDelete(current.id))}
        disabled={readonlyDraft || busy || !current.id}
        className="rounded-lg border border-ops-alert/35 px-4 py-2 text-sm text-ops-alert disabled:cursor-not-allowed disabled:opacity-40"
      >
        {isBuiltinDraft ? '恢复默认' : '删除'}
      </button>
      <button
        onClick={readonlyDraft ? onBeginEdit : onSave}
        disabled={busy}
        className="rounded-lg bg-ops-accent px-5 py-2 text-sm font-semibold text-ops-dark disabled:cursor-not-allowed disabled:opacity-50"
      >
        {readonlyDraft ? '编辑模板' : (busy ? '保存中...' : '保存命令')}
      </button>
    </div>
  )
}
