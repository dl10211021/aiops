import type { Session, SlashCommand } from '@/types'
import {
  CommandBasicFields,
  CommandEditorActions,
  CommandEditorStatus,
  CommandPromptField,
  CommandScopeFields,
  CommandToggleRow,
} from './CommandManagerEditorParts'

interface CommandManagerEditorProps {
  session: Session | null
  current: Partial<SlashCommand>
  readonlyDraft: boolean
  busy: boolean
  error: string
  isBuiltinDraft: boolean
  onPatch: (value: Partial<SlashCommand>) => void
  onStepOrder: (delta: number) => void
  onBeginEdit: () => void
  onSave: () => void
  onDelete: (commandId: string) => void
  onRestore: (commandId: string) => void
}

export default function CommandManagerEditor({
  session,
  current,
  readonlyDraft,
  busy,
  error,
  isBuiltinDraft,
  onPatch,
  onStepOrder,
  onBeginEdit,
  onSave,
  onDelete,
  onRestore,
}: CommandManagerEditorProps) {
  return (
    <div className="overflow-y-auto p-5">
      <CommandEditorStatus error={error} readonlyDraft={readonlyDraft} />
      <div className="grid gap-3 md:grid-cols-2">
        <CommandBasicFields current={current} readonlyDraft={readonlyDraft} onPatch={onPatch} />
        <CommandScopeFields
          busy={busy}
          current={current}
          readonlyDraft={readonlyDraft}
          session={session}
          onPatch={onPatch}
          onStepOrder={onStepOrder}
        />
        <CommandPromptField current={current} readonlyDraft={readonlyDraft} onPatch={onPatch} />
      </div>
      <CommandToggleRow current={current} readonlyDraft={readonlyDraft} onPatch={onPatch} />
      <CommandEditorActions
        busy={busy}
        current={current}
        isBuiltinDraft={isBuiltinDraft}
        readonlyDraft={readonlyDraft}
        onBeginEdit={onBeginEdit}
        onDelete={onDelete}
        onRestore={onRestore}
        onSave={onSave}
      />
    </div>
  )
}
