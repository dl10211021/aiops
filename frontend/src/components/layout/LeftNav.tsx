import { useStore } from '@/store'
import type { ReactNode } from 'react'
import type { ViewId } from '@/types'

const NAV_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'dashboard', icon: 'D', label: '总览' },
  { id: 'chat', icon: 'C', label: '会话' },
  { id: 'assets', icon: 'A', label: '资产' },
  { id: 'canvas', icon: 'V', label: '画板' },
  { id: 'cron', icon: 'T', label: '巡检' },
  { id: 'alerts', icon: 'L', label: '告警' },
  { id: 'approvals', icon: 'P', label: '审批' },
]

const KNOWLEDGE_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'skills', icon: 'S', label: 'Skills' },
  { id: 'knowledge', icon: 'K', label: '知识库' },
]

const SETTINGS_ITEMS: Array<{ id: string; icon: string; label: string; modal: string }> = [
  { id: 'safety', icon: 'R', label: '安全', modal: 'safety-policy' },
  { id: 'model', icon: 'M', label: '模型', modal: 'llm-config' },
  { id: 'notify', icon: 'N', label: '通知', modal: 'notifications' },
]

export default function LeftNav() {
  const currentView = useStore((s) => s.currentView)
  const setView = useStore((s) => s.setView)
  const openModal = useStore((s) => s.openModal)

  return (
    <nav className="min-h-0 w-[118px] overflow-y-auto border-r border-ops-surface0/80 bg-ops-sidebar px-2.5 py-3 backdrop-blur-xl">
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
            active={false}
            icon={item.icon}
            label={item.label}
            onClick={() => openModal(item.modal)}
          />
        ))}
      </NavGroup>
    </nav>
  )
}

function NavGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-3 space-y-1">
      <div className="px-1.5 pb-1 text-[10px] font-bold text-ops-overlay">{label}</div>
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
      className={`mb-1 flex min-h-[38px] w-full items-center gap-2 rounded-lg px-1.5 py-1.5 text-left transition-all
        ${active
          ? 'border border-ops-accent/35 bg-ops-accent/14 text-ops-accent'
          : 'border border-transparent text-ops-subtext hover:bg-ops-surface0/70 hover:text-ops-text'}`}
      title={label}
    >
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md border border-ops-surface1/60 bg-ops-dark/35 text-[11px] font-black">
        {icon}
      </span>
      <span className="min-w-0 whitespace-nowrap text-[12px] font-semibold leading-tight">{label}</span>
    </button>
  )
}
