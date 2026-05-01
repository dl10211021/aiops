import { useStore } from '@/store'
import type { ReactNode } from 'react'
import type { ViewId } from '@/types'

const NAV_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'dashboard', icon: '▦', label: '总览大屏' },
  { id: 'chat', icon: '◉', label: 'AI 会话' },
  { id: 'assets', icon: '▤', label: '资产中心' },
  { id: 'cron', icon: '◷', label: '自动巡检' },
  { id: 'alerts', icon: '◇', label: '告警事件' },
  { id: 'approvals', icon: '✓', label: '审批中心' },
]

const KNOWLEDGE_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'skills', icon: '✦', label: '技能市场' },
  { id: 'knowledge', icon: '▧', label: '知识库' },
]

const SETTINGS_ITEMS: Array<{ id: string; icon: string; label: string; modal: string }> = [
  { id: 'model', icon: '⌁', label: '模型配置', modal: 'llm-config' },
  { id: 'notify', icon: '◇', label: '告警通道', modal: 'notifications' },
  { id: 'safety', icon: '□', label: '安全策略', modal: 'safety-policy' },
]

export default function LeftNav() {
  const currentView = useStore((s) => s.currentView)
  const setView = useStore((s) => s.setView)
  const openModal = useStore((s) => s.openModal)

  return (
    <nav className="w-[136px] bg-ops-sidebar/90 flex flex-col py-4 px-3 gap-2 border-r border-ops-surface0/80 shrink-0 backdrop-blur-xl">
      {/* Logo */}
      <div className="mx-auto mb-5 flex h-11 w-11 cursor-pointer items-center justify-center rounded-lg border border-ops-accent/35 bg-ops-accent/10 text-[11px] font-black tracking-[0.18em] text-ops-accent shadow-[0_0_30px_rgba(243,177,90,0.18)]" title="SkillOps" onClick={() => setView('dashboard')}>
        OPS
      </div>

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
    <div className="space-y-1.5">
      <div className="px-2 text-[10px] font-semibold text-ops-overlay">{label}</div>
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
      className={`flex min-h-10 w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-all
        ${active
          ? 'bg-ops-accent text-ops-dark shadow-[0_0_18px_rgba(243,177,90,0.22)]'
          : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'}`}
      title={label}
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-ops-dark/45 text-sm font-bold">
        {icon}
      </span>
      <span className="min-w-0 whitespace-nowrap text-[12px] font-semibold leading-tight">{label}</span>
    </button>
  )
}
