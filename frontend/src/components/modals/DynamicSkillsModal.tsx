import { useState, useEffect, useMemo } from 'react'
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
  const [searchQuery, setSearchQuery] = useState('')

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
      addToast('技能挂载已更新', 'success')
      closeModal()
    } catch {
      addToast('更新失败', 'error')
    }
  }

  const filteredSkills = useMemo(() => {
    if (!searchQuery.trim()) return skills;
    const lowerQ = searchQuery.toLowerCase();
    return skills.filter(sk => 
      sk.name?.toLowerCase().includes(lowerQ) || 
      sk.id.toLowerCase().includes(lowerQ) ||
      sk.description?.toLowerCase().includes(lowerQ)
    );
  }, [skills, searchQuery]);

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>      
      <div className="bg-ops-panel rounded-xl p-6 w-[480px]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">🧩 动态技能配置</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>     
        </div>
        <p className="text-xs text-ops-subtext mb-3">
          勾选需要为当前会话挂载的专业技能，AI 将根据这些指引执行操作。
        </p>

        <input 
          type="text" 
          placeholder="搜索技能名称或描述..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mb-4 outline-none focus:border-ops-accent"
        />

        <div className="flex flex-wrap gap-2 max-h-60 overflow-y-auto">
          {filteredSkills.map((sk) => (
            <button key={sk.id} onClick={() => toggle(sk.id)}
              className={`text-[11px] px-3 py-1.5 rounded-lg transition-colors ${selected.has(sk.id) ? 'bg-ops-accent/20 text-ops-accent border border-ops-accent/40' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text border border-transparent'}`}>
              {sk.name || sk.id}
            </button>
          ))}
          {filteredSkills.length === 0 && skills.length > 0 && <p className="text-xs text-ops-overlay w-full text-center py-4">没有匹配的技能</p>}
          {skills.length === 0 && <p className="text-xs text-ops-overlay">没有可用的技能</p>}
        </div>
        
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={handleSave} className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80">更新会话</button>
        </div>
      </div>
    </div>
  )
}
