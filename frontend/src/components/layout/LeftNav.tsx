import { useStore } from '@/store'
import type { ViewId } from '@/types'

const NAV_ITEMS: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: 'dashboard', icon: '总', label: '总览大屏' },
  { id: 'chat', icon: '会', label: 'AI 会话' },
  { id: 'assets', icon: '资', label: '资产中心' },
  { id: 'cron', icon: '巡', label: '自动化巡检' },
  { id: 'alerts', icon: '警', label: '告警事件' },
  { id: 'approvals', icon: '审', label: '审批中心' },
  { id: 'skills', icon: '技', label: '技能市场' },
  { id: 'knowledge', icon: '知', label: '知识库' },
]

export default function LeftNav() {
  const currentView = useStore((s) => s.currentView)
  const setView = useStore((s) => s.setView)
  const openModal = useStore((s) => s.openModal)

  return (
    <nav className="w-18 bg-ops-sidebar/90 flex flex-col items-center py-4 gap-2 border-r border-ops-surface0/80 shrink-0 backdrop-blur-xl">
      {/* Logo */}
      <div className="mb-5 flex h-11 w-11 cursor-pointer items-center justify-center rounded-2xl border border-ops-accent/35 bg-ops-accent/10 text-[11px] font-black tracking-[0.18em] text-ops-accent shadow-[0_0_30px_rgba(243,177,90,0.18)]" title="SkillOps" onClick={() => setView('dashboard')}>
        OPS
      </div>

      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => setView(item.id)}
          className={`w-11 h-11 rounded-xl flex items-center justify-center text-base font-bold transition-all
            ${currentView === item.id
              ? 'bg-ops-accent text-ops-dark shadow-[0_0_26px_rgba(243,177,90,0.28)]'
              : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'}`}
          title={item.label}
        >
          {item.icon}
        </button>
      ))}

      <div className="flex-1" />

      {/* Settings */}
      <button
        onClick={() => openModal('llm-config')}
        className="w-11 h-11 rounded-xl flex items-center justify-center text-base font-bold text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="模型配置"
      >
        模
      </button>
      <button
        onClick={() => openModal('notifications')}
        className="w-11 h-11 rounded-xl flex items-center justify-center text-base font-bold text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="告警通道"
      >
        告
      </button>
      <button
        onClick={() => openModal('safety-policy')}
        className="w-11 h-11 rounded-xl flex items-center justify-center text-base font-bold text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="安全策略"
      >
        安
      </button>
    </nav>
  )
}
