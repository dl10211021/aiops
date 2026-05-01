import type { SlashCommand } from '@/types'

interface QuickCommandDockProps {
  commands: SlashCommand[]
  onSelect: (prompt: string) => void
  onManage: () => void
}

export function QuickCommandDock({ commands, onSelect, onManage }: QuickCommandDockProps) {
  return (
    <div className="mb-2 flex items-center gap-2 overflow-x-auto pb-1">
      <span className="shrink-0 text-[11px] text-ops-overlay">快捷命令</span>
      {commands.map((cmd) => (
        <button
          key={cmd.id}
          type="button"
          onClick={() => onSelect(cmd.prompt)}
          className="shrink-0 rounded-full border border-ops-surface1 bg-ops-dark/70 px-3 py-1 text-[11px] text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text"
          title={cmd.description}
        >
          {cmd.label}
        </button>
      ))}
      <button
        type="button"
        onClick={onManage}
        className="shrink-0 rounded-full border border-ops-accent/40 bg-ops-accent/10 px-3 py-1 text-[11px] font-medium text-ops-accent transition-colors hover:bg-ops-accent/15"
      >
        管理
      </button>
    </div>
  )
}

interface SlashCommandMenuProps {
  commands: SlashCommand[]
  onSelect: (prompt: string) => void
}

export function SlashCommandMenu({ commands, onSelect }: SlashCommandMenuProps) {
  return (
    <div className="mb-3 max-w-3xl overflow-hidden rounded-lg border border-ops-surface1 bg-ops-dark/95 shadow-2xl">
      <div className="border-b border-ops-surface0 px-3 py-2 text-[11px] text-ops-overlay">
        斜杠菜单
      </div>
      <div className="grid gap-1 p-2 sm:grid-cols-2">
        {commands.map((cmd) => (
          <button
            key={cmd.id}
            type="button"
            onClick={() => onSelect(cmd.prompt)}
            className="rounded-lg px-3 py-2 text-left transition-colors hover:bg-ops-surface0 focus:outline-none focus:ring-1 focus:ring-ops-accent"
          >
            <div className="font-mono text-xs text-ops-accent">{cmd.label}</div>
            <div className="mt-1 text-[11px] text-ops-subtext">{cmd.description}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
