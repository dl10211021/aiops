import type { Session, SlashCommand } from '@/types'
import {
  CommandCheckbox,
  CommandOrderField,
  CommandSelectField,
  CommandTextField,
} from './CommandManagerEditorControls'

const COMMAND_SCOPE_OPTIONS = [
  { value: 'global', label: '全局' },
  { value: 'asset_type', label: '当前系统/资产类型' },
  { value: 'protocol', label: '当前协议' },
  { value: 'asset', label: '当前单资产' },
]

export function CommandBasicFields({
  current,
  readonlyDraft,
  onPatch,
}: {
  current: Partial<SlashCommand>
  readonlyDraft: boolean
  onPatch: (value: Partial<SlashCommand>) => void
}) {
  return (
    <>
      <CommandTextField
        label="显示名称"
        value={current.label || ''}
        disabled={readonlyDraft}
        placeholder="/oracle-health 实例健康"
        onChange={(label) => onPatch({ label })}
      />
      <CommandTextField
        label="分类"
        value={current.category || ''}
        disabled={readonlyDraft}
        placeholder="数据库"
        onChange={(category) => onPatch({ category })}
      />
      <CommandTextField
        label="说明"
        value={current.description || ''}
        disabled={readonlyDraft}
        placeholder="用于输入框上方和 / 菜单里的说明"
        className="md:col-span-2"
        onChange={(description) => onPatch({ description })}
      />
    </>
  )
}

export function CommandScopeFields({
  busy,
  current,
  readonlyDraft,
  session,
  onPatch,
  onStepOrder,
}: {
  busy: boolean
  current: Partial<SlashCommand>
  readonlyDraft: boolean
  session: Session | null
  onPatch: (value: Partial<SlashCommand>) => void
  onStepOrder: (delta: number) => void
}) {
  return (
    <>
      <CommandSelectField
        label="适用范围"
        value={current.scope_type || 'global'}
        disabled={readonlyDraft}
        options={COMMAND_SCOPE_OPTIONS}
        onChange={(scope_type) => onPatch({ scope_type })}
      />
      <CommandOrderField
        busy={busy}
        readonlyDraft={readonlyDraft}
        sortOrder={Number(current.sort_order || 1)}
        onStepOrder={onStepOrder}
      />
      <CommandTextField
        label="资产类型"
        value={current.asset_type || ''}
        disabled={readonlyDraft}
        placeholder={session?.asset_type || 'oracle'}
        onChange={(asset_type) => onPatch({ asset_type })}
      />
      <CommandTextField
        label="协议"
        value={current.protocol || ''}
        disabled={readonlyDraft}
        placeholder={session?.protocol || 'ssh'}
        onChange={(protocol) => onPatch({ protocol })}
      />
      <CommandTextField
        label="单资产主机"
        value={current.host || ''}
        disabled={readonlyDraft}
        placeholder={session?.host || '172.17.10.2'}
        className="md:col-span-2"
        onChange={(host) => onPatch({ host })}
      />
    </>
  )
}

export function CommandPromptField({
  current,
  readonlyDraft,
  onPatch,
}: {
  current: Partial<SlashCommand>
  readonlyDraft: boolean
  onPatch: (value: Partial<SlashCommand>) => void
}) {
  return (
    <label className="text-sm md:col-span-2">
      <span className="text-ops-subtext">Prompt 模板</span>
      <textarea
        value={current.prompt_template || current.prompt || ''}
        onChange={(event) => onPatch({ prompt_template: event.target.value })}
        disabled={readonlyDraft}
        className="mt-1 h-36 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm leading-6 text-ops-text outline-none focus:border-ops-accent disabled:cursor-default disabled:opacity-75"
        placeholder="可用变量：{target} {host} {port} {asset_type} {protocol} {tool_list} {remark} {username}"
      />
    </label>
  )
}

export function CommandToggleRow({
  current,
  readonlyDraft,
  onPatch,
}: {
  current: Partial<SlashCommand>
  readonlyDraft: boolean
  onPatch: (value: Partial<SlashCommand>) => void
}) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-ops-subtext">
      <CommandCheckbox
        checked={current.readonly !== false}
        disabled={readonlyDraft}
        label="只读命令"
        onChange={(readonly) => onPatch({ readonly })}
      />
      <CommandCheckbox
        checked={Boolean(current.pinned)}
        disabled={readonlyDraft}
        label="固定到快捷栏"
        onChange={(pinned) => onPatch({ pinned })}
      />
      <CommandCheckbox
        checked={current.enabled !== false}
        disabled={readonlyDraft}
        label="启用"
        onChange={(enabled) => onPatch({ enabled })}
      />
    </div>
  )
}
