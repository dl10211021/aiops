import type { SlashCommand } from '@/types'
import { displayCommandLabel } from './slashCommands'

interface QuickCommandDockProps {
  commands: SlashCommand[]
  onSelect: (prompt: string) => void
  onManage: () => void
  onOpenRealtimeCanvas?: () => void
}

export function QuickCommandDock({ commands, onSelect, onManage, onOpenRealtimeCanvas }: QuickCommandDockProps) {
  return (
    <div className="mb-2 flex items-center gap-2 overflow-x-auto pb-1">
      <span className="shrink-0 text-[11px] text-ops-overlay">快捷命令</span>
      {onOpenRealtimeCanvas && (
        <button
          type="button"
          onClick={onOpenRealtimeCanvas}
          className="shrink-0 rounded-full border border-ops-accent/50 bg-ops-accent/14 px-3 py-1 text-[11px] font-semibold text-ops-accent transition-colors hover:bg-ops-accent/20"
          title="打开交互式实时画板，选择监控点、刷新间隔和运行时长"
        >
          实时画板
        </button>
      )}
      {commands.map((cmd) => (
        <button
          key={cmd.id}
          type="button"
          onClick={() => onSelect(cmd.prompt)}
          className="shrink-0 rounded-full border border-ops-surface1 bg-ops-dark/70 px-3 py-1 text-[11px] text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text"
          title={cmd.description}
        >
          {displayCommandLabel(cmd.label)}
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
  activeIndex: number
  onSelect: (prompt: string) => void
  onActiveIndexChange: (index: number) => void
}

export function SlashCommandMenu({
  activeIndex,
  commands,
  onActiveIndexChange,
  onSelect,
}: SlashCommandMenuProps) {
  return (
    <div className="mb-3 max-w-3xl overflow-hidden rounded-lg border border-ops-surface1 bg-ops-dark/95 shadow-2xl">
      <div className="flex items-center justify-between border-b border-ops-surface0 px-3 py-2 text-[11px] text-ops-overlay">
        <span>快捷命令选择</span>
        <span>↑↓ 选择，Enter 确认</span>
      </div>
      <div className="max-h-64 overflow-y-auto p-2" role="listbox" aria-label="快捷命令选择">
        {commands.map((cmd, index) => (
          <button
            key={cmd.id}
            type="button"
            onClick={() => onSelect(cmd.prompt)}
            onMouseEnter={() => onActiveIndexChange(index)}
            role="option"
            aria-selected={index === activeIndex}
            className={`mb-1 w-full rounded-lg px-3 py-2 text-left transition-colors focus:outline-none focus:ring-1 focus:ring-ops-accent ${
              index === activeIndex
                ? 'bg-ops-accent/15 ring-1 ring-ops-accent/45'
                : 'hover:bg-ops-surface0'
            }`}
          >
            <div className="text-xs font-semibold text-ops-accent">{displayCommandLabel(cmd.label)}</div>
            <div className="mt-1 text-[11px] text-ops-subtext">{cmd.description}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
