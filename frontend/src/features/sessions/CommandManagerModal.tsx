import type { Session, SlashCommand } from '@/types'
import { commandDraftForSession } from './slashCommands'
import CommandManagerCatalog from './CommandManagerCatalog'
import CommandManagerEditor from './CommandManagerEditor'
import { useCommandManagerSorting } from './useCommandManagerSorting'

interface CommandManagerModalProps {
  session: Session | null
  commands: SlashCommand[]
  availableCommands: SlashCommand[]
  draft: Partial<SlashCommand> | null
  readonlyDraft: boolean
  busy: boolean
  error: string
  onClose: () => void
  onDraftChange: (draft: Partial<SlashCommand>) => void
  onNew: () => void
  onEdit: (command: SlashCommand) => void
  onEditBuiltin: (command: SlashCommand) => void
  onViewBuiltin: (command: SlashCommand) => void
  onCopy: (command: SlashCommand) => void
  onBeginEdit: () => void
  onRestore: (commandId: string) => void
  onRestoreMany: (commandIds: string[]) => void
  onSaveOrder: (commands: Partial<SlashCommand>[]) => Promise<void> | void
  onSave: () => void
  onDelete: (commandId: string) => void
}

export default function CommandManagerModal({
  session,
  commands,
  availableCommands,
  draft,
  readonlyDraft,
  busy,
  error,
  onClose,
  onDraftChange,
  onNew,
  onEdit,
  onEditBuiltin,
  onViewBuiltin,
  onCopy,
  onBeginEdit,
  onRestore,
  onRestoreMany,
  onSaveOrder,
  onSave,
  onDelete,
}: CommandManagerModalProps) {
  const current = draft || commandDraftForSession(session)
  const sorting = useCommandManagerSorting(commands, availableCommands, onSaveOrder)
  const isBuiltinDraft = Boolean(current.id && sorting.builtInIds.has(current.id))
  const patch = (value: Partial<SlashCommand>) => onDraftChange({ ...current, ...value })
  const stepOrder = (delta: number) => {
    const currentOrder = Number(current.sort_order || 1)
    patch({ sort_order: Math.max(1, Math.min(100, currentOrder + delta)) })
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="flex max-h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="flex items-center justify-between gap-3 border-b border-ops-surface0 px-5 py-4">
          <div>
            <div className="text-xs font-semibold text-ops-accent">快捷命令管理</div>
            <h2 className="mt-1 text-lg font-bold text-ops-text">按系统、协议或单资产定制常用指令</h2>
          </div>
          <button onClick={onClose} className="rounded-md border border-ops-surface1 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text">
            关闭
          </button>
        </div>
        <div className="grid min-h-0 flex-1 gap-0 overflow-hidden md:grid-cols-[1fr_1.25fr]">
          <CommandManagerCatalog
            session={session}
            busy={busy}
            sortMode={sorting.sortMode}
            sortPickIds={sorting.sortPickIds}
            userCommands={sorting.userCommands}
            orderedUserCommands={sorting.orderedUserCommands}
            builtInTemplates={sorting.builtInTemplates}
            orderedBuiltInTemplates={sorting.orderedBuiltInTemplates}
            overriddenBuiltinIds={sorting.overriddenBuiltinIds}
            onBeginSort={sorting.beginSort}
            onCancelSort={sorting.cancelSort}
            onSaveSort={(mode) => void sorting.saveSort(mode)}
            onToggleSortPick={sorting.toggleSortPick}
            onNew={onNew}
            onEditCustom={onEdit}
            onViewBuiltin={onViewBuiltin}
            onEditBuiltin={onEditBuiltin}
            onCopyBuiltin={onCopy}
            onRestore={onRestore}
            onRestoreMany={onRestoreMany}
          />
          <CommandManagerEditor
            session={session}
            current={current}
            readonlyDraft={readonlyDraft}
            busy={busy}
            error={error}
            isBuiltinDraft={isBuiltinDraft}
            onPatch={patch}
            onStepOrder={stepOrder}
            onBeginEdit={onBeginEdit}
            onSave={onSave}
            onDelete={onDelete}
            onRestore={onRestore}
          />
        </div>
      </section>
    </div>
  )
}
