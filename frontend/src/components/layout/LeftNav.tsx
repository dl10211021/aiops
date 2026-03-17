import { useStore } from '@/store'

const NAV_ITEMS: Array<{ id: 'chat' | 'assets' | 'cron' | 'skills' | 'knowledge'; icon: string; label: string }> = [
  { id: 'chat', icon: '💬', label: '对话' },
  { id: 'assets', icon: '🏦', label: '资产' },
  { id: 'skills', icon: '🧩', label: '技能' },
  { id: 'knowledge', icon: '📚', label: '知识库' },
  { id: 'cron', icon: '⏰', label: '巡检' },
]

export default function LeftNav() {
  const currentView = useStore((s) => s.currentView)
  const setView = useStore((s) => s.setView)
  const openModal = useStore((s) => s.openModal)

  return (
    <nav className="w-16 bg-ops-sidebar flex flex-col items-center py-4 gap-2 border-r border-ops-surface0 shrink-0">
      {/* Logo */}
      <div className="text-2xl mb-4 cursor-pointer" title="SkillOps" onClick={() => setView('chat')}>
        ⚡
      </div>

      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => setView(item.id)}
          className={`w-11 h-11 rounded-lg flex items-center justify-center text-lg transition-colors
            ${currentView === item.id
              ? 'bg-ops-accent/20 text-ops-accent'
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
        className="w-11 h-11 rounded-lg flex items-center justify-center text-lg text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="AI 配置"
      >
        ⚙️
      </button>
      <button
        onClick={() => openModal('notifications')}
        className="w-11 h-11 rounded-lg flex items-center justify-center text-lg text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text transition-colors"
        title="告警通道"
      >
        🔔
      </button>
    </nav>
  )
}
