import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { getSkillRegistry, getSkillDetail, scanSkills, migrateSkill, createSkill } from '@/api/client'
import PageHeader from '@/components/layout/PageHeader'
import type { SkillInfo } from '@/types'
import { SkillCreateModal } from './SkillCreateModal'
import { SkillDetailDrawer } from './SkillDetailDrawer'
import {
  SkillEmptyState,
  SkillMarketHeaderActions,
  SkillSection,
} from './SkillMarketParts'
import type { SkillCreateForm } from './skillMarketModel'

export default function SkillMarket() {
  const skillRegistry = useStore((s) => s.skillRegistry)
  const setSkillRegistry = useStore((s) => s.setSkillRegistry)
  const addToast = useStore((s) => s.addToast)

  const [search, setSearch] = useState('')
  const [detailSkill, setDetailSkill] = useState<SkillInfo | null>(null)
  const [detailContent, setDetailContent] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState<SkillCreateForm>({ skill_id: '', description: '', instructions: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadSkills = useCallback(async (withLoading = true) => {
    if (withLoading) setLoading(true)
    setError('')
    try {
      const res = await getSkillRegistry()
      setSkillRegistry(res.data.registry || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载技能失败')
      addToast('加载技能失败', 'error')
    } finally {
      setLoading(false)
    }
  }, [setSkillRegistry, addToast])

  useEffect(() => { loadSkills() }, [loadSkills])

  const handleScan = async () => {
    try {
      await scanSkills()
      await loadSkills(false)
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
      await loadSkills(false)
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
  const totalInstalled = skillRegistry.filter((s) => !s.is_market).length
  const totalMarket = skillRegistry.filter((s) => s.is_market).length

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="能力库"
          title="技能市场"
          description={`管理 AI 技能包，已安装 ${totalInstalled} 个，可安装 ${totalMarket} 个。`}
          actions={(
            <SkillMarketHeaderActions
              search={search}
              onCreate={() => setShowCreate(true)}
              onScan={handleScan}
              onSearchChange={setSearch}
            />
          )}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        {loading && (
          <section className="ops-data-panel p-8 text-center text-sm text-ops-subtext">
            正在加载技能目录...
          </section>
        )}

        {!loading && <SkillSection title="已安装" skills={installed} onView={handleViewDetail} />}

        {!loading && <SkillSection title="可安装技能" skills={market} onView={handleViewDetail} onInstall={handleInstall} />}

        {!loading && filtered.length === 0 && (
          <SkillEmptyState
            search={search}
            onClearSearch={() => setSearch('')}
            onCreate={() => setShowCreate(true)}
            onScan={handleScan}
          />
        )}

        {detailSkill && (
          <SkillDetailDrawer
            content={detailContent}
            skill={detailSkill}
            onClose={() => setDetailSkill(null)}
          />
        )}

        {showCreate && (
          <SkillCreateModal
            form={createForm}
            onClose={() => setShowCreate(false)}
            onFormChange={setCreateForm}
            onSubmit={handleCreate}
          />
        )}
      </div>
    </div>
  )
}
