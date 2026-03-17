import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getSkillRegistry, updateSessionSkills } from '@/api/client'
import type { SkillInfo } from '@/types'

export default function DynamicSkillsModal() {
  const closeModal = useStore((s) => s.closeModal)
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)
  const updateSession = useStore((s) => s.updateSession)
  const addToast = useStore((s) => s.addToast)

  const session = currentSessionId ? sessions[currentSessionId] : null
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set(session?.skills || []))

  useEffect(() => {
    getSkillRegistry().then((r) => {
      setSkills(r.data.registry?.filter((s) => !s.is_market) || [])
    }).catch(() => {})
  }, [])

  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelected(next)
  }

  const handleSave = async () => {
    if (!currentSessionId) return
    try {
      const arr = Array.from(selected)
      await updateSessionSkills(currentSessionId, arr)
      updateSession(currentSessionId, { skills: arr })
      addToast('技能已更新', 'success')
      closeModal()
    } catch {
      addToast('更新失败', 'error')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[450px]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">🧩 动态技能挂载</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>
        <p className="text-xs text-ops-subtext mb-3">
          勾选要挂载到当前会话的技能包，AI 将立即获得对应能力
        </p>
        <div className="flex flex-wrap gap-2 max-h-60 overflow-y-auto">
          {skills.map((sk) => (
            <button key={sk.id} onClick={() => toggle(sk.id)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${selected.has(sk.id) ? 'bg-ops-accent/20 text-ops-accent border border-ops-accent/40' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text border border-transparent'}`}>
              {sk.name || sk.id}
            </button>
          ))}
          {skills.length === 0 && <p className="text-xs text-ops-overlay">暂无可用技能</p>}
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={handleSave} className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80">保存</button>
        </div>
      </div>
    </div>
  )
}
