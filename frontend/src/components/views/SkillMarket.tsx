import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { getSkillRegistry, getSkillDetail, scanSkills, migrateSkill, createSkill } from '@/api/client'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { SkillInfo } from '@/types'

export default function SkillMarket() {
  const skillRegistry = useStore((s) => s.skillRegistry)
  const setSkillRegistry = useStore((s) => s.setSkillRegistry)
  const addToast = useStore((s) => s.addToast)

  const [search, setSearch] = useState('')
  const [detailSkill, setDetailSkill] = useState<SkillInfo | null>(null)
  const [detailContent, setDetailContent] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ skill_id: '', description: '', instructions: '' })

  const loadSkills = useCallback(async () => {
    try {
      const res = await getSkillRegistry()
      setSkillRegistry(res.data.registry || [])
    } catch {
      addToast('加载技能失败', 'error')
    }
  }, [setSkillRegistry, addToast])

  useEffect(() => { loadSkills() }, [loadSkills])

  const handleScan = async () => {
    try {
      await scanSkills()
      await loadSkills()
      addToast('本地技能扫描完成', 'success')
    } catch {
      addToast('扫描失败', 'error')
    }
  }

  const handleViewDetail = async (skill: SkillInfo) => {
    setDetailSkill(skill)
    try {
      const res = await getSkillDetail(skill.id)
      setDetailContent(res.data.instructions || '')
    } catch {
      setDetailContent('加载详情失败')
    }
  }

  const handleInstall = async (skill: SkillInfo) => {
    if (!skill.source_path) return
    try {
      await migrateSkill(skill.source_path, skill.id)
      await loadSkills()
      addToast(`技能 ${skill.name || skill.id} 安装成功`, 'success')
    } catch {
      addToast('安装失败', 'error')
    }
  }

  const handleCreate = async () => {
    if (!createForm.skill_id || !createForm.instructions) {
      addToast('请填写完整', 'error')
      return
    }
    try {
      await createSkill(createForm)
      setShowCreate(false)
      setCreateForm({ skill_id: '', description: '', instructions: '' })
      await loadSkills()
      addToast('技能创建成功', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '创建失败', 'error')
    }
  }

  const filtered = skillRegistry.filter((s) => {
    const q = search.toLowerCase()
    return !q || s.id.toLowerCase().includes(q) || (s.name || '').toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q)
  })

  const installed = filtered.filter((s) => !s.is_market)
  const market = filtered.filter((s) => s.is_market)

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-ops-text">🧩 技能市场</h1>
            <p className="text-sm text-ops-subtext mt-1">管理 AI 技能包 — 已安装 {installed.length} 个，市场 {market.length} 个</p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="搜索技能..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-1.5 text-sm text-ops-text outline-none focus:border-ops-accent"
            />
            <button onClick={handleScan} className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors">
              🔍 扫描
            </button>
            <button onClick={() => setShowCreate(true)} className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors">
              + 创建技能
            </button>
          </div>
        </div>

        {/* Installed Skills */}
        {installed.length > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-semibold text-ops-subtext mb-3">✅ 已安装</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {installed.map((skill) => (
                <SkillCard key={skill.id} skill={skill} onView={handleViewDetail} />
              ))}
            </div>
          </div>
        )}

        {/* Market Skills */}
        {market.length > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-semibold text-ops-subtext mb-3">🛒 技能市场</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {market.map((skill) => (
                <SkillCard key={skill.id} skill={skill} onView={handleViewDetail} onInstall={handleInstall} />
              ))}
            </div>
          </div>
        )}

        {filtered.length === 0 && (
          <div className="text-center text-ops-subtext py-20">
            <div className="text-4xl mb-3">🧩</div>
            <p>暂无技能包</p>
          </div>
        )}

        {/* Detail Drawer */}
        {detailSkill && (
          <div className="fixed inset-0 bg-black/50 z-40 flex justify-end" onClick={() => setDetailSkill(null)}>
            <div className="w-[600px] bg-ops-panel h-full overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-ops-text">{detailSkill.name || detailSkill.id}</h2>
                <button onClick={() => setDetailSkill(null)} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
              </div>
              <div
                className="markdown-body text-sm"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(
                    typeof marked.parse(detailContent) === 'string'
                      ? marked.parse(detailContent) as string
                      : ''
                  ),
                }}
              />
            </div>
          </div>
        )}

        {/* Create Modal */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={() => setShowCreate(false)}>
            <div className="bg-ops-panel rounded-xl p-6 w-[500px] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-lg font-bold text-ops-text mb-4">创建新技能</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-ops-subtext">技能 ID (英文+横线)</label>
                  <input
                    value={createForm.skill_id}
                    onChange={(e) => setCreateForm({ ...createForm, skill_id: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    placeholder="my-custom-skill"
                  />
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">描述</label>
                  <input
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    placeholder="这个技能可以..."
                  />
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">技能指令 (Markdown)</label>
                  <textarea
                    value={createForm.instructions}
                    onChange={(e) => setCreateForm({ ...createForm, instructions: e.target.value })}
                    rows={8}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent resize-none"
                    placeholder="# 技能名称&#10;&#10;## 技能职责&#10;..."
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
                <button onClick={handleCreate} className="bg-ops-accent text-ops-dark px-4 py-2 rounded-lg text-sm font-medium hover:bg-ops-accent/80">创建</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SkillCard({ skill, onView, onInstall }: {
  skill: SkillInfo
  onView: (s: SkillInfo) => void
  onInstall?: (s: SkillInfo) => void
}) {
  return (
    <div className="bg-ops-panel border border-ops-surface0 rounded-xl p-4 hover:border-ops-accent/40 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0">
          <div className="font-medium text-ops-text text-sm truncate">{skill.name || skill.id}</div>
          <div className="text-xs text-ops-overlay mt-0.5">{skill.category || 'general'}</div>
        </div>
        {skill.is_market && (
          <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">市场</span>
        )}
      </div>
      <p className="text-xs text-ops-subtext line-clamp-2 mb-3">{skill.description || '暂无描述'}</p>
      <div className="flex gap-2">
        <button
          onClick={() => onView(skill)}
          className="flex-1 bg-ops-surface0 text-ops-subtext text-xs py-1.5 rounded-lg hover:text-ops-text transition-colors"
        >
          📖 详情
        </button>
        {onInstall && (
          <button
            onClick={() => onInstall(skill)}
            className="flex-1 bg-ops-accent/15 text-ops-accent text-xs py-1.5 rounded-lg hover:bg-ops-accent/25 transition-colors"
          >
            📥 安装
          </button>
        )}
      </div>
    </div>
  )
}
