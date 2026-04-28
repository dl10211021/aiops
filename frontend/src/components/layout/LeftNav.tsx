import { useStore } from '@/store'
import type { ViewId } from '@/types'

const NAV_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'dashboard', icon: '▦', label: '总览大屏' },
  { id: 'chat', icon: '◉', label: 'AI 会话' },
  { id: 'assets', icon: '▤', label: '资产中心' },
  { id: 'cron', icon: '◷', label: '自动巡检' },
  { id: 'alerts', icon: '◇', label: '告警事件' },
  { id: 'approvals', icon: '✓', label: '审批中心' },
  { id: 'skills', icon: '✦', label: '技能市场' },
  { id: 'knowledge', icon: '▧', label: '知识库' },
]

export default function LeftNav() {
  const currentView = useStore((s) => s.currentView)
  const setView = useStore((s) => s.setView)
  const openModal = useStore((s) => s.openModal)

  return (
    <nav className="w-28 bg-ops-sidebar/90 flex flex-col py-4 px-2 gap-2 border-r border-ops-surface0/80 shrink-0 backdrop-blur-xl">
      {/* Logo */}
      <div className="mx-auto mb-5 flex h-11 w-11 cursor-pointer items-center justify-center rounded-2xl border border-ops-accent/35 bg-ops-accent/10 text-[11px] font-black tracking-[0.18em] text-ops-accent shadow-[0_0_30px_rgba(243,177,90,0.18)]" title="SkillOps" onClick={() => setView('dashboard')}>
        OPS
      </div>

      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => setView(item.id)}
          className={`h-12 w-full rounded-xl flex items-center gap-2 px-2 text-left transition-all
            ${currentView === item.id
              ? 'bg-ops-accent text-ops-dark shadow-[0_0_26px_rgba(243,177,90,0.28)]'
              : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'}`}
          title={item.label}
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ops-dark/45 text-sm font-bold">
            {item.icon}
          </span>
          <span className="min-w-0 text-[12px] font-semibold leading-tight">{item.label}</span>
        </button>
      ))}

      <div className="flex-1" />

      {/* Settings */}
      <button
        onClick={() => openModal('llm-config')}
        className="h-11 w-full rounded-xl flex items-center gap-2 px-2 text-left text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="模型配置"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ops-dark/45 text-sm font-bold">⌁</span>
        <span className="text-[12px] font-semibold">模型配置</span>
      </button>
      <button
        onClick={() => openModal('notifications')}
        className="h-11 w-full rounded-xl flex items-center gap-2 px-2 text-left text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="告警通道"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ops-dark/45 text-sm font-bold">◇</span>
        <span className="text-[12px] font-semibold">告警通道</span>
      </button>
      <button
        onClick={() => openModal('safety-policy')}
        className="h-11 w-full rounded-xl flex items-center gap-2 px-2 text-left text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="安全策略"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ops-dark/45 text-sm font-bold">□</span>
        <span className="text-[12px] font-semibold">安全策略</span>
      </button>
    </nav>
  )
}
