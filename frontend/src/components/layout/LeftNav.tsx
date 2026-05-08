import { useStore } from '@/store'
import type { ReactNode } from 'react'
import type { ViewId } from '@/types'

const NAV_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'dashboard', icon: '⌂', label: '总览' },
  { id: 'chat', icon: '◉', label: '会话' },
  { id: 'assets', icon: '▦', label: '资产' },
  { id: 'canvas', icon: '◇', label: '画板' },
  { id: 'cron', icon: '◷', label: '巡检' },
  { id: 'alerts', icon: '!', label: '告警' },
  { id: 'approvals', icon: '✓', label: '审批' },
]

const KNOWLEDGE_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'skills', icon: '✦', label: 'Skills' },
  { id: 'knowledge', icon: '文', label: '知识库' },
]

const SETTINGS_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'config', icon: '⚙', label: '配置' },
]

export default function LeftNav() {
  const currentView = useStore((s) => s.currentView)
  const setView = useStore((s) => s.setView)

  return (
    <nav className="ops-nav-rail min-h-0 w-[104px] overflow-y-auto border-r border-ops-surface0/80 px-2 py-3 backdrop-blur-xl">
      <NavGroup label="工作台">
        {NAV_ITEMS.map((item) => (
          <NavButton
            key={item.id}
            active={currentView === item.id}
            icon={item.icon}
            label={item.label}
            onClick={() => setView(item.id)}
          />
        ))}
      </NavGroup>

      <NavGroup label="能力库">
        {KNOWLEDGE_ITEMS.map((item) => (
          <NavButton
            key={item.id}
            active={currentView === item.id}
            icon={item.icon}
            label={item.label}
            onClick={() => setView(item.id)}
          />
        ))}
      </NavGroup>

      <div className="flex-1" />

      <NavGroup label="系统">
        {SETTINGS_ITEMS.map((item) => (
          <NavButton
            key={item.id}
            active={currentView === item.id}
            icon={item.icon}
            label={item.label}
            onClick={() => setView(item.id)}
          />
        ))}
      </NavGroup>
    </nav>
  )
}

function NavGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-3 space-y-1.5">
      <div className="px-1.5 pb-1 text-[10px] font-bold tracking-[0.16em] text-ops-overlay">{label}</div>
      {children}
    </div>
  )
}

function NavButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean
  icon: string
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`ops-nav-button mb-1 flex min-h-[40px] w-full items-center gap-2 rounded-xl px-1.5 py-1.5 text-left transition-all
        ${active
          ? 'is-active border border-ops-accent/35 bg-ops-accent/15 text-ops-accent shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]'
          : 'border border-transparent text-ops-subtext hover:border-ops-surface1/35 hover:bg-ops-surface0/55 hover:text-ops-text'}`}
      title={label}
    >
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg border border-ops-surface1/55 bg-ops-dark/30 text-[12px] font-black">
        {icon}
      </span>
      <span className="min-w-0 whitespace-nowrap text-[12px] font-bold leading-tight">{label}</span>
    </button>
  )
}
