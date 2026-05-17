import { useEffect, useMemo, useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import { EvidenceReferenceChip } from './EvidenceReferenceChip'
import { useStore } from '@/store'
import {
  appendObservabilityEvidence,
  appendObservabilityRootCause,
  bindObservabilityAsset,
  createObservabilityInvestigation,
  getObservableSources,
  getObservabilityDiscoveryCandidates,
  getObservabilityInvestigations,
  getObservabilityOverview,
  getObservabilityProfile,
  getObservabilityProfilePacks,
  getObservabilitySystems,
  unbindObservabilityComponent,
  updateObservabilityComponent,
} from '@/api/observability'
import { getSavedAssets } from '@/api/assets'
import type {
  Asset,
  ObservabilityComponent,
  ObservabilityDiscoveryCandidate,
  ObservabilityEvidence,
  ObservabilityInvestigation,
  ObservabilityOverview,
  ObservabilityProfile,
  ObservabilityProfilePack,
  ObservabilitySource,
  ObservabilitySystemSummary,
} from '@/types'

type MasterAgentMessage = {
  id: string
  role: 'agent' | 'user'
  content: string
  time: string
}

type MasterTaskMode = '排查' | '巡检' | '健康检查'

type ComponentEditDraft = {
  id: string
  name: string
  layer: string
  component_type: string
  workload_family: string
}

type TabId = 'systems' | 'discovery' | 'investigations' | 'sources' | 'packs'

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'systems', label: '业务画像' },
  { id: 'discovery', label: '画像发现' },
  { id: 'investigations', label: '总控任务' },
  { id: 'sources', label: '观测源' },
  { id: 'packs', label: '画像包' },
]

const MASTER_TASK_MODES: MasterTaskMode[] = ['排查', '巡检', '健康检查']

const LAYER_LABELS: Record<string, string> = {
  business: '业务',
  entry: '访问入口',
  application: '应用',
  container: '容器',
  os: 'OS',
  virtualization: '虚拟化',
  physical: '物理',
  network: '网络',
  storage: '存储',
  database: '数据库',
  big_data: '大数据',
  middleware: '中间件',
  security: '安全',
  observability: '观测',
  unknown: '未知',
}

const DEFAULT_COMPONENT_TYPE_BY_LAYER: Record<string, string> = {
  entry: 'business_entry',
  application: 'application_service',
  container: 'k8s_cluster',
  os: 'os_host',
  virtualization: 'vm',
  network: 'network_switch',
  database: 'database_instance',
  middleware: 'middleware',
  observability: 'observability_source',
}

const SOURCE_LABELS: Record<string, string> = {
  user_input: '用户输入',
  asset_binding: '资产中心',
  session_binding: '会话',
  manual_edit: '人工编辑',
  unknown_placeholder: '待补充',
  prometheus_target: 'Prometheus 发现',
}

export default function ObservabilityCenter() {
  const [activeTab, setActiveTab] = useState<TabId>('systems')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState<ObservabilityOverview | null>(null)
  const [systems, setSystems] = useState<ObservabilitySystemSummary[]>([])
  const [profile, setProfile] = useState<ObservabilityProfile | null>(null)
  const [sources, setSources] = useState<ObservabilitySource[]>([])
  const [packs, setPacks] = useState<ObservabilityProfilePack[]>([])
  const [candidates, setCandidates] = useState<ObservabilityDiscoveryCandidate[]>([])
  const [investigations, setInvestigations] = useState<ObservabilityInvestigation[]>([])
  const [savedAssets, setSavedAssets] = useState<Asset[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState('')
  const [masterAgentDraft, setMasterAgentDraft] = useState('global 门户访问变慢，先按最近 2 小时只读排查。')
  const [masterTaskMode, setMasterTaskMode] = useState<MasterTaskMode>('排查')
  const [profileEditorOpen, setProfileEditorOpen] = useState(false)
  const [profileEditDraft, setProfileEditDraft] = useState('补充业务入口、上下游依赖、数据库、中间件、网络或负责人信息。')
  const [profileEditNote, setProfileEditNote] = useState('')
  const [componentEditDraft, setComponentEditDraft] = useState<ComponentEditDraft | null>(null)
  const [masterAgentMessages, setMasterAgentMessages] = useState<MasterAgentMessage[]>([
    {
      id: 'agent-ready',
      role: 'agent',
      content: '先把会话或资产加入业务系统，我会基于业务画像派发 Prometheus、K8s、OS、DB、网络等 Agent，支持排查、巡检和健康检查。',
      time: '就绪',
    },
  ])
  const [investigationForm, setInvestigationForm] = useState({
    title: '系统慢',
    symptom: 'global 门户访问变慢，先按最近 2 小时只读排查。',
    time_window: '最近 2 小时',
    severity: 'warning',
  })
  const sessions = useStore((state) => state.sessions)
  const currentSessionId = useStore((state) => state.currentSessionId)
  const setCurrentSession = useStore((state) => state.setCurrentSession)
  const setView = useStore((state) => state.setView)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [overviewRes, systemsRes, sourcesRes, packsRes, candidatesRes, investigationsRes, assetsRes] = await Promise.all([
        getObservabilityOverview(),
        getObservabilitySystems(),
        getObservableSources(),
        getObservabilityProfilePacks(),
        getObservabilityDiscoveryCandidates(),
        getObservabilityInvestigations(),
        getSavedAssets(),
      ])
      const nextSystems = systemsRes.data.systems || []
      const nextAssets = assetsRes.data.assets || []
      setOverview(overviewRes.data.overview)
      setSystems(nextSystems)
      setSources(sourcesRes.data.sources || [])
      setPacks(packsRes.data.profile_packs || [])
      setCandidates(candidatesRes.data.candidates || [])
      setInvestigations(investigationsRes.data.investigations || [])
      setSavedAssets(nextAssets)
      if (!selectedAssetId && nextAssets[0]?.id) setSelectedAssetId(String(nextAssets[0].id))
      if (nextSystems[0]?.system?.id) {
        const profileRes = await getObservabilityProfile(nextSystems[0].system.id)
        setProfile(profileRes.data.profile)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '可观测性数据加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const selectedSystem = systems[0]
  const boundAssetComponents = useMemo(() => {
    if (!profile) return []
    return profile.components.filter((component) => component.metadata?.asset_id !== undefined)
  }, [profile])
  const boundSessionComponents = useMemo(() => {
    if (!profile) return []
    return profile.components.filter((component) => component.metadata?.session_id !== undefined)
  }, [profile])
  const profileAnalysis = useMemo(() => {
    const components = profile?.components || []
    const unknowns = profile?.unknowns || []
    const sourcesCount = profile?.observable_sources.length || 0
    const layerNames = new Set(components.map((component) => component.layer))
    const knownEntryCount = boundAssetComponents.length + boundSessionComponents.length
    const gaps: string[] = []
    if (!layerNames.has('database')) gaps.push('数据库')
    if (!layerNames.has('middleware')) gaps.push('中间件')
    if (!layerNames.has('network')) gaps.push('网络')
    if (sourcesCount === 0) gaps.push('观测源')
    if (unknowns.length > 0) gaps.push('未知节点确认')
    const readyScore = Math.min(100, Math.max(selectedSystem?.system.profile_completeness || 0, Math.round((components.length + sourcesCount + knownEntryCount) * 12)))
    return {
      summary: knownEntryCount > 0
        ? `已识别 ${knownEntryCount} 个入口、${components.length} 个组件，当前适合先做只读${masterTaskMode}。`
        : '还缺少业务入口，请先从会话或资产加入一个真实入口。',
      conclusion: gaps.length
        ? `画像还不完整，优先补齐：${gaps.slice(0, 4).join('、')}。`
        : '画像基础信息较完整，可以直接交给主 Agent 发起总控任务。',
      readyScore,
      gaps,
      nextAction: gaps.length ? '先补画像，再发起主 Agent 任务' : '可以发起主 Agent 总控任务',
    }
  }, [boundAssetComponents.length, boundSessionComponents.length, masterTaskMode, profile, selectedSystem?.system.profile_completeness])
  const updateBoundProfile = (nextProfile: ObservabilityProfile, summary: ObservabilitySystemSummary) => {
    setProfile(nextProfile)
    setSystems((items) => items.map((item) => item.system.id === summary.system.id ? summary : item))
    setSources(nextProfile.observable_sources)
  }
  const bindSelectedAsset = async () => {
    if (!selectedSystem?.system?.id || !selectedAssetId) return
    const asset = savedAssets.find((item) => String(item.id) === selectedAssetId)
    if (!asset) return
    setLoading(true)
    setError('')
    try {
      const response = await bindObservabilityAsset(selectedSystem.system.id, asset as unknown as Record<string, unknown>)
      updateBoundProfile(response.data.profile, response.data.summary)
    } catch (err) {
      setError(err instanceof Error ? err.message : '资产加入业务画像失败')
    } finally {
      setLoading(false)
    }
  }
  const unbindComponent = async (componentId: string) => {
    if (!selectedSystem?.system?.id) return
    setLoading(true)
    setError('')
    try {
      const response = await unbindObservabilityComponent(selectedSystem.system.id, componentId)
      updateBoundProfile(response.data.profile, response.data.summary)
    } catch (err) {
      setError(err instanceof Error ? err.message : '入口移除失败')
    } finally {
      setLoading(false)
    }
  }
  const startComponentEdit = (component: ObservabilityComponent) => {
    setComponentEditDraft({
      id: component.id,
      name: component.confidence === 'unknown' ? '' : component.name,
      layer: component.layer,
      component_type: component.component_type === 'unknown' ? DEFAULT_COMPONENT_TYPE_BY_LAYER[component.layer] || 'application_service' : component.component_type,
      workload_family: component.workload_family === 'unknown' ? component.layer : component.workload_family,
    })
  }
  const saveComponentEdit = async () => {
    if (!selectedSystem?.system?.id || !componentEditDraft) return
    const name = componentEditDraft.name.trim()
    if (!name) {
      setError('请填写组件名称')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await updateObservabilityComponent(selectedSystem.system.id, componentEditDraft.id, {
        name,
        layer: componentEditDraft.layer,
        component_type: componentEditDraft.component_type,
        workload_family: componentEditDraft.workload_family,
        confidence: 'confirmed',
        status: 'unknown',
        metadata: { source_note: '人工补充画像' },
      } as Partial<ObservabilityComponent>)
      updateBoundProfile(response.data.profile, response.data.summary)
      setComponentEditDraft(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '画像组件保存失败')
    } finally {
      setLoading(false)
    }
  }
  const analyzeProfileWithAI = () => {
    const unknownNames = (profile?.unknowns || []).map((item) => item.name).slice(0, 5)
    const prompt = [
      `请基于「${selectedSystem?.system?.name || '当前业务系统'}」的资产、会话和观测源分析业务画像。`,
      unknownNames.length ? `优先补全这些未知项：${unknownNames.join('、')}。` : '当前未知项较少，请检查画像是否还缺数据库、中间件、网络或观测源。',
    ].join('')
    setMasterTaskMode('健康检查')
    setMasterAgentDraft(prompt)
  }
  const openProfileEditor = () => {
    setProfileEditorOpen((open) => !open)
  }
  const saveProfileEditDraft = () => {
    setProfileEditNote(profileEditDraft.trim())
    setProfileEditorOpen(false)
  }
  const createInvestigation = async () => {
    if (!selectedSystem?.system?.id) {
      setError('请先创建或加载业务系统画像')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await createObservabilityInvestigation({
        system_id: selectedSystem.system.id,
        title: investigationForm.title,
        symptom: investigationForm.symptom,
        time_window: investigationForm.time_window,
        severity: investigationForm.severity,
      })
      setInvestigations((items) => [response.data.investigation, ...items])
    } catch (err) {
      setError(err instanceof Error ? err.message : '排查事件创建失败')
    } finally {
      setLoading(false)
    }
  }
  const sendToMasterAgent = async () => {
    const message = masterAgentDraft.trim()
    if (!message) return
    if (!selectedSystem?.system?.id) {
      setError('请先加载业务系统画像，再发起主 Agent 会话')
      return
    }
    const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    const titleText = message.length > 18 ? `${message.slice(0, 18)}...` : message
    const title = `${masterTaskMode}：${titleText}`
    setMasterAgentMessages((items) => [
      ...items,
      { id: `user-${Date.now()}`, role: 'user', content: message, time: now },
    ])
    setMasterAgentDraft('')
    setInvestigationForm((form) => ({ ...form, title, symptom: message }))
    setLoading(true)
    setError('')
    try {
      const response = await createObservabilityInvestigation({
        system_id: selectedSystem.system.id,
        title,
        symptom: message,
        time_window: investigationForm.time_window,
        severity: investigationForm.severity,
      })
      const investigation = response.data.investigation
      const tasks = investigation.tasks || []
      const agents = tasks.map((task) => task.agent_role).filter(Boolean)
      setInvestigations((items) => [investigation, ...items])
      setMasterAgentMessages((items) => [
        ...items,
        {
          id: `agent-${Date.now()}`,
          role: 'agent',
          content: agents.length
            ? `已创建总控${masterTaskMode}「${investigation.title}」，计划派发 ${tasks.length} 个 Agent 任务：${agents.slice(0, 6).join('、')}。`
            : `已创建总控${masterTaskMode}「${investigation.title}」，但当前画像还不完整，需要先补充资产、会话或观测源。`,
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : '主 Agent 会话发送失败')
      setMasterAgentMessages((items) => [
        ...items,
        {
          id: `agent-error-${Date.now()}`,
          role: 'agent',
          content: '这次没有成功创建排查任务，请检查业务系统画像和后端服务状态。',
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const appendSampleEvidence = async (investigationId: string) => {
    setLoading(true)
    setError('')
    try {
      const response = await appendObservabilityEvidence(investigationId, {
        title: 'Prometheus 基线证据待确认',
        summary: '已登记为排查证据，后续应由 Prometheus Agent 写入真实查询摘要。',
        evidence_type: 'metric',
        confidence: 'pending_review',
      })
      setInvestigations((items) => items.map((item) => (
        item.id === investigationId ? response.data.investigation : item
      )))
    } catch (err) {
      setError(err instanceof Error ? err.message : '证据追加失败')
    } finally {
      setLoading(false)
    }
  }

  const appendTaskEvidence = async (
    investigationId: string,
    task: ObservabilityInvestigation['tasks'][number],
  ) => {
    setLoading(true)
    setError('')
    try {
      const response = await appendObservabilityEvidence(investigationId, {
        title: `${task.agent_role} 输出摘要`,
        summary: task.output_summary || 'Agent 任务输出待补充。',
        evidence_type: 'agent_task_output',
        task_id: task.id,
        component_id: task.target_component_id || undefined,
        source_id: task.source_id || undefined,
        raw_ref: task.id,
        raw_excerpt: task.output_summary || '',
        confidence: task.status === 'completed' ? 'confirmed' : 'pending_review',
      })
      setInvestigations((items) => items.map((item) => (
        item.id === investigationId ? response.data.investigation : item
      )))
    } catch (err) {
      setError(err instanceof Error ? err.message : '任务证据回填失败')
    } finally {
      setLoading(false)
    }
  }

  const appendEvidenceRootCause = async (investigation: ObservabilityInvestigation) => {
    const evidenceIds = (investigation.evidence || []).map((item) => item.id)
    if (evidenceIds.length === 0) {
      setError('请先追加证据，再生成根因候选')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await appendObservabilityRootCause(investigation.id, {
        title: '待复核根因候选',
        description: '基于当前证据链生成的待复核候选，需要继续由 Summary Agent 或人工确认。',
        likelihood: 'medium',
        impact: investigation.severity || 'unknown',
        confidence: 'pending_review',
        supporting_evidence_ids: evidenceIds.slice(0, 5),
        recommended_next_steps: ['补充同时间窗口指标/日志证据', '确认是否存在发布、扩容或配置变更', '由人工确认后再进入处置建议'],
      })
      setInvestigations((items) => items.map((item) => (
        item.id === investigation.id ? response.data.investigation : item
      )))
    } catch (err) {
      setError(err instanceof Error ? err.message : '根因候选生成失败')
    } finally {
      setLoading(false)
    }
  }

  const composeInvestigationDispatchDraft = (investigation: ObservabilityInvestigation) => {
    const sessionIds = Object.keys(sessions)
    const activeSessionId = currentSessionId || sessionIds[0]
    if (!activeSessionId) {
      setError('请先建立一个会话，再生成多 Agent 协同指令草稿')
      return
    }
    if (activeSessionId !== currentSessionId) setCurrentSession(activeSessionId)
    setView('chat')
    const message = buildInvestigationDispatchDraft(investigation)
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('opscore:chat-draft', {
        detail: { sessionId: activeSessionId, message },
      }))
    }, 0)
  }

  const orderedLayers = useMemo(() => {
    if (!profile) return []
    return [...profile.components, ...profile.unknowns].reduce<Array<{ layer: string; items: typeof profile.components }>>((acc, component) => {
      let bucket = acc.find((item) => item.layer === component.layer)
      if (!bucket) {
        bucket = { layer: component.layer, items: [] }
        acc.push(bucket)
      }
      bucket.items.push(component)
      return acc
    }, [])
  }, [profile])

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="业务系统可观测性"
          title="业务可观测工作台"
          description="先接入入口，再形成业务画像，最后通过主 Agent 发起排查、巡检或健康检查。"
          actions={(
            <button className="ops-control rounded-lg px-4 py-2 text-sm font-semibold" onClick={() => void load()}>
              刷新
            </button>
          )}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        <div className="ops-data-panel grid gap-3 p-4 md:grid-cols-4">
          <ContextValue label="当前业务系统" value={selectedSystem?.system.name || '未选择'} />
          <ContextValue label="画像完整度" value={`${selectedSystem?.system.profile_completeness || 0}%`} />
          <ContextValue label="已接入口" value={`${selectedSystem?.bound_session_count || boundSessionComponents.length} 会话 / ${selectedSystem?.bound_asset_count || boundAssetComponents.length} 资产`} />
          <ContextValue label="待补全" value={`${profile?.unknowns.length || overview?.unknown_count || 0} 个未知项`} tone={(profile?.unknowns.length || overview?.unknown_count || 0) > 0 ? 'amber' : 'default'} />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[0.85fr_0.95fr_1.2fr]">
          <section className="ops-data-panel p-4">
            <SectionTitle
              title="1. 添加入口"
              subtitle="入口统一从资产中心添加，已加入的入口可以随时移除。"
            />
            <div className="mt-4 space-y-3">
              <div>
                <div className="mb-1 text-xs font-bold text-ops-overlay">资产中心</div>
                <div className="flex gap-2">
                  <select className="ops-input min-w-0 flex-1 rounded-lg px-3 py-2 text-sm" value={selectedAssetId} onChange={(event) => setSelectedAssetId(event.target.value)}>
                    {savedAssets.map((asset) => (
                      <option key={asset.id} value={String(asset.id)}>
                        {asset.remark || asset.host} · {asset.asset_type}/{asset.protocol || ''}
                      </option>
                    ))}
                  </select>
                  <button className="ops-control rounded-lg px-3 py-2 text-sm font-bold" onClick={() => void bindSelectedAsset()}>
                    加入
                  </button>
                </div>
              </div>
              <BoundEntryList
                components={[...boundAssetComponents, ...boundSessionComponents]}
                onRemove={(componentId) => void unbindComponent(componentId)}
              />
            </div>
          </section>

          <section className="ops-data-panel p-4">
            <SectionTitle
              title="2. 业务系统画像"
              subtitle={selectedSystem ? `${selectedSystem.system.name} / ${selectedSystem.system.environment}` : '中间区域直接给出画像分析和可编辑草稿'}
            />
            <div className="mt-4 space-y-3">
              <ProfileAnalysisCard analysis={profileAnalysis} />
              <ProfileLayerMap profile={profile} onEdit={startComponentEdit} />
              {componentEditDraft && (
                <div className="rounded-lg border border-ops-surface1/50 bg-ops-dark/25 p-3">
                  <div className="mb-2 text-xs font-bold text-ops-overlay">补充画像项</div>
                  <div className="grid gap-2 md:grid-cols-[1fr_120px]">
                    <input
                      className="ops-input rounded-lg px-3 py-2 text-sm"
                      value={componentEditDraft.name}
                      onChange={(event) => setComponentEditDraft((draft) => draft ? { ...draft, name: event.target.value } : draft)}
                      placeholder="例如：global 门户 nginx 入口"
                    />
                    <select
                      className="ops-input rounded-lg px-3 py-2 text-sm"
                      value={componentEditDraft.layer}
                      onChange={(event) => {
                        const layer = event.target.value
                        setComponentEditDraft((draft) => draft ? {
                          ...draft,
                          layer,
                          component_type: DEFAULT_COMPONENT_TYPE_BY_LAYER[layer] || draft.component_type,
                          workload_family: layer,
                        } : draft)
                      }}
                    >
                      {['entry', 'application', 'container', 'os', 'virtualization', 'network', 'database', 'middleware', 'observability'].map((layer) => (
                        <option key={layer} value={layer}>{LAYER_LABELS[layer]}</option>
                      ))}
                    </select>
                  </div>
                  <div className="mt-2 flex justify-end gap-2">
                    <button className="ops-control rounded-lg px-3 py-2 text-sm font-bold" onClick={() => setComponentEditDraft(null)}>
                      取消
                    </button>
                    <button className="ops-primary-action rounded-lg px-3 py-2 text-sm font-bold" onClick={() => void saveComponentEdit()}>
                      保存画像项
                    </button>
                  </div>
                </div>
              )}
              {profileEditNote && (
                <div className="rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-3 py-2">
                  <div className="mb-1 text-xs font-bold text-ops-accent">人工修正草稿</div>
                  <div className="text-sm leading-6 text-ops-subtext">{profileEditNote}</div>
                </div>
              )}
              {profileEditorOpen && (
                <div className="rounded-lg border border-ops-surface1/50 bg-ops-dark/25 p-3">
                  <div className="mb-2 text-xs font-bold text-ops-overlay">编辑画像草稿</div>
                  <textarea
                    className="ops-input min-h-28 w-full resize-none rounded-lg px-3 py-2 text-sm leading-6"
                    value={profileEditDraft}
                    onChange={(event) => setProfileEditDraft(event.target.value)}
                    placeholder="补充业务入口、依赖关系、数据库、中间件、网络、负责人。"
                  />
                  <div className="mt-2 flex justify-end gap-2">
                    <button className="ops-control rounded-lg px-3 py-2 text-sm font-bold" onClick={() => setProfileEditorOpen(false)}>
                      取消
                    </button>
                    <button className="ops-primary-action rounded-lg px-3 py-2 text-sm font-bold" onClick={saveProfileEditDraft}>
                      保存草稿
                    </button>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button className="ops-control rounded-lg px-3 py-2 text-sm font-bold" onClick={analyzeProfileWithAI}>
                  AI 分析画像
                </button>
                <button className="ops-control rounded-lg px-3 py-2 text-sm font-bold" onClick={openProfileEditor}>
                  {profileEditorOpen ? '收起编辑' : '编辑画像'}
                </button>
              </div>
            </div>
          </section>

          <section className="ops-data-panel p-4">
            <SectionTitle
              title="3. 主 Agent"
              subtitle="这里只做任务发起，不再混入画像分析和历史列表。"
            />
            <div className="mt-4 overflow-hidden rounded-lg border border-ops-surface0/80 bg-ops-dark/20">
              <div className="border-b border-ops-surface0/80 p-3">
                <div className="grid grid-cols-3 gap-1 rounded-lg bg-ops-dark/30 p-1">
                  {MASTER_TASK_MODES.map((mode) => (
                    <button
                      key={mode}
                      className={`rounded-md px-3 py-2 text-sm font-bold ${masterTaskMode === mode ? 'bg-ops-accent text-ops-dark' : 'text-ops-subtext hover:bg-ops-surface0/45'}`}
                      onClick={() => setMasterTaskMode(mode)}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
              <div className="min-h-64 max-h-72 space-y-3 overflow-y-auto px-3 py-3">
                {masterAgentMessages.map((message) => (
                  <MasterAgentBubble key={message.id} message={message} />
                ))}
              </div>
              <div className="grid gap-2 border-t border-ops-surface0/80 p-3 md:grid-cols-[1fr_auto]">
                <textarea
                  className="ops-input min-h-20 resize-none rounded-lg px-3 py-2 text-sm leading-6"
                  value={masterAgentDraft}
                  onChange={(event) => setMasterAgentDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                      event.preventDefault()
                      void sendToMasterAgent()
                    }
                  }}
                  placeholder={`输入${masterTaskMode}目标、范围和时间窗口`}
                />
                <button className="ops-primary-action rounded-lg px-4 py-2 text-sm font-bold md:self-end" onClick={() => void sendToMasterAgent()}>
                  发送
                </button>
              </div>
            </div>
          </section>
        </div>

        <div className="hidden">
          <div className="flex flex-wrap gap-2 border-b border-ops-surface0/80 p-3">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  activeTab === tab.id
                    ? 'bg-ops-accent text-ops-dark'
                    : 'ops-control'
                }`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-5">
            {activeTab === 'systems' && (
              <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
                <section>
                  <h2 className="text-base font-bold text-ops-text">业务系统列表</h2>
                  <div className="mt-4 space-y-3">
                    {systems.map((item) => (
                      <div key={item.system.id} className="rounded-lg border border-ops-surface0/80 bg-ops-surface0/35 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-bold text-ops-text">{item.system.name}</div>
                            <div className="mt-1 text-xs text-ops-subtext">{item.system.environment} · {item.system.owner || '未指定负责人'}</div>
                          </div>
                          <span className="rounded bg-ops-accent/15 px-2 py-1 font-mono text-xs text-ops-accent">
                            {item.system.profile_completeness}%
                          </span>
                        </div>
                        <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
                          <MiniStat label="组件" value={item.component_count} />
                          <MiniStat label="未知" value={item.unknown_count} />
                          <MiniStat label="关系" value={item.relationship_count} />
                          <MiniStat label="源" value={item.source_count} />
                        </div>
                      </div>
                    ))}
                    {systems.length === 0 && <div className="py-10 text-center text-sm text-ops-subtext">暂无业务系统画像</div>}
                  </div>
                </section>

                <section>
                  <h2 className="text-base font-bold text-ops-text">分层画像</h2>
                  <div className="mt-4 space-y-3">
                    {orderedLayers.map((layer) => (
                      <div key={layer.layer} className="rounded-lg border border-ops-surface0/80 bg-ops-dark/25 p-4">
                        <div className="mb-3 flex items-center justify-between">
                          <span className="text-sm font-bold text-ops-text">{LAYER_LABELS[layer.layer] || layer.layer}</span>
                          <span className="font-mono text-xs text-ops-overlay">{layer.items.length}</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {layer.items.map((component) => (
                            <span
                              key={component.id}
                              className={`rounded border px-2.5 py-1 text-xs ${
                                component.confidence === 'unknown'
                                  ? 'border-amber-300/35 bg-amber-400/10 text-amber-200'
                                  : 'border-ops-surface1/50 bg-ops-surface0/45 text-ops-subtext'
                              }`}
                            >
                              {component.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                    {!profile && <div className="py-10 text-center text-sm text-ops-subtext">正在等待画像数据</div>}
                  </div>
                </section>
              </div>
            )}

            {activeTab === 'discovery' && (
              <div>
                <SectionTitle
                  title="画像发现"
                  subtitle={`当前基线系统：${selectedSystem?.system?.name || '暂无'}。候选项必须带证据，确认后才进入业务系统拓扑。`}
                />
                <div className="mt-4 grid gap-3 xl:grid-cols-2">
                  {candidates.map((candidate) => (
                    <DiscoveryCandidateCard key={candidate.id} candidate={candidate} />
                  ))}
                </div>
                {candidates.length === 0 && <EmptyState text="暂无待确认发现候选" />}
              </div>
            )}

            {activeTab === 'investigations' && (
              <div>
                <SectionTitle
                  title="排查事件"
                  subtitle="按业务系统、症状和时间窗口生成只读排查计划，证据回收后再排序根因候选。"
                />
                <div className="mt-4 rounded-lg border border-ops-surface0/80 bg-ops-dark/20 p-4">
                  <div className="grid gap-3 lg:grid-cols-[0.7fr_1.4fr_0.45fr_0.35fr_auto]">
                    <label className="block">
                      <span className="text-xs font-bold text-ops-overlay">标题</span>
                      <input
                        className="ops-input mt-1 w-full rounded-lg px-3 py-2 text-sm"
                        value={investigationForm.title}
                        onChange={(event) => setInvestigationForm((form) => ({ ...form, title: event.target.value }))}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-bold text-ops-overlay">症状</span>
                      <input
                        className="ops-input mt-1 w-full rounded-lg px-3 py-2 text-sm"
                        value={investigationForm.symptom}
                        onChange={(event) => setInvestigationForm((form) => ({ ...form, symptom: event.target.value }))}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-bold text-ops-overlay">时间窗口</span>
                      <input
                        className="ops-input mt-1 w-full rounded-lg px-3 py-2 text-sm"
                        value={investigationForm.time_window}
                        onChange={(event) => setInvestigationForm((form) => ({ ...form, time_window: event.target.value }))}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-bold text-ops-overlay">级别</span>
                      <select
                        className="ops-input mt-1 w-full rounded-lg px-3 py-2 text-sm"
                        value={investigationForm.severity}
                        onChange={(event) => setInvestigationForm((form) => ({ ...form, severity: event.target.value }))}
                      >
                        <option value="info">info</option>
                        <option value="warning">warning</option>
                        <option value="critical">critical</option>
                        <option value="unknown">unknown</option>
                      </select>
                    </label>
                    <div className="flex items-end">
                      <button className="ops-primary-action h-10 rounded-lg px-4 text-sm font-bold" onClick={() => void createInvestigation()}>
                        创建排查
                      </button>
                    </div>
                  </div>
                </div>
                <div className="mt-4 space-y-3">
                  {investigations.map((item) => (
                    <InvestigationCard
                      key={item.id}
                      investigation={item}
                      onAppendEvidence={() => void appendSampleEvidence(item.id)}
                      onAppendTaskEvidence={(task) => void appendTaskEvidence(item.id, task)}
                      onAppendRootCause={() => void appendEvidenceRootCause(item)}
                      onComposeDispatchDraft={() => composeInvestigationDispatchDraft(item)}
                    />
                  ))}
                </div>
                {investigations.length === 0 && <EmptyState text="暂无排查事件" />}
              </div>
            )}

            {activeTab === 'sources' && (
              <div>
                <h2 className="text-base font-bold text-ops-text">观测源</h2>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  {sources.map((source) => (
                    <div key={source.id} className="rounded-lg border border-ops-surface0/80 bg-ops-surface0/35 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-bold text-ops-text">{source.name}</div>
                          <div className="mt-1 text-xs text-ops-subtext">{source.source_type} · {source.source_origin}</div>
                        </div>
                        <span className="rounded bg-ops-accent/15 px-2 py-1 text-xs text-ops-accent">{source.status}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {source.capabilities.map((capability) => (
                          <span key={capability} className="rounded bg-ops-dark/35 px-2 py-1 font-mono text-[11px] text-ops-overlay">
                            {capability}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'packs' && (
              <div>
                <h2 className="text-base font-bold text-ops-text">画像包</h2>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {packs.map((pack) => (
                    <div key={pack.id} className="rounded-lg border border-ops-surface0/80 bg-ops-surface0/35 p-4">
                      <div className="text-sm font-bold text-ops-text">{pack.name}</div>
                      <div className="mt-1 text-xs text-ops-subtext">{LAYER_LABELS[pack.layer] || pack.layer} · {pack.workload_family}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {pack.component_types.slice(0, 4).map((type) => (
                          <span key={type} className="rounded bg-ops-dark/35 px-2 py-1 font-mono text-[11px] text-ops-overlay">{type}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {loading && <div className="mt-4 text-xs text-ops-overlay">正在刷新可观测性数据...</div>}
      </div>
    </div>
  )
}

function Metric({ label, value, tone = 'green' }: { label: string; value: number; tone?: 'green' | 'amber' | 'blue' }) {
  const toneClass = tone === 'amber' ? 'text-amber-200' : tone === 'blue' ? 'text-ops-accent' : 'text-ops-success'
  return (
    <div className="ops-data-panel p-4">
      <div className="text-xs font-semibold text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-black ${toneClass}`}>{value}</div>
    </div>
  )
}

function ContextValue({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'amber' }) {
  return (
    <div className="min-w-0">
      <div className="text-xs font-semibold text-ops-overlay">{label}</div>
      <div className={`mt-1 truncate text-sm font-bold ${tone === 'amber' ? 'text-amber-200' : 'text-ops-text'}`}>{value}</div>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded bg-ops-dark/35 px-2 py-2">
      <div className="font-mono text-sm font-black text-ops-text">{value}</div>
      <div className="mt-0.5 text-[11px] text-ops-overlay">{label}</div>
    </div>
  )
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-base font-bold text-ops-text">{title}</h2>
      <p className="mt-1 max-w-3xl text-sm leading-6 text-ops-subtext">{subtitle}</p>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="mt-4 rounded-lg border border-dashed border-ops-surface1/60 bg-ops-surface0/25 p-8 text-center text-sm text-ops-subtext">
      {text}
    </div>
  )
}

function ProfileLine({
  label,
  items,
  empty,
  tone = 'default',
}: {
  label: string
  items: string[]
  empty: string
  tone?: 'default' | 'amber'
}) {
  return (
    <div className="rounded-lg border border-ops-surface0/70 bg-ops-dark/20 px-3 py-2">
      <div className="mb-2 text-xs font-bold text-ops-overlay">{label}</div>
      <div className="flex flex-wrap gap-2">
        {items.length ? items.slice(0, 8).map((item) => (
          <span
            key={item}
            className={`rounded px-2 py-1 text-xs ${
              tone === 'amber' ? 'bg-amber-400/10 text-amber-200' : 'bg-ops-surface0/55 text-ops-subtext'
            }`}
          >
            {item}
          </span>
        )) : <span className="text-xs text-ops-overlay">{empty}</span>}
      </div>
    </div>
  )
}

function BoundEntryList({
  components,
  onRemove,
}: {
  components: ObservabilityComponent[]
  onRemove: (componentId: string) => void
}) {
  if (!components.length) {
    return (
      <div className="rounded-lg border border-dashed border-ops-surface1/50 bg-ops-dark/20 px-3 py-5 text-center text-sm text-ops-overlay">
        还没有加入入口
      </div>
    )
  }
  return (
    <div className="space-y-2">
      <div className="text-xs font-bold text-ops-overlay">已加入入口</div>
      {components.map((component) => (
        <div key={component.id} className="flex items-center justify-between gap-3 rounded-lg border border-ops-surface0/70 bg-ops-dark/20 px-3 py-2">
          <div className="min-w-0">
            <div className="truncate text-sm font-bold text-ops-text">{component.name}</div>
            <div className="mt-0.5 text-xs text-ops-overlay">
              {LAYER_LABELS[component.layer] || component.layer} · {component.metadata?.asset_id ? '资产' : '会话'}
            </div>
          </div>
          <button className="ops-control rounded-lg px-2.5 py-1.5 text-xs font-bold" onClick={() => onRemove(component.id)}>
            移除
          </button>
        </div>
      ))}
    </div>
  )
}

function ProfileLayerMap({ profile, onEdit }: { profile: ObservabilityProfile | null; onEdit: (component: ObservabilityComponent) => void }) {
  const layers = ['entry', 'application', 'container', 'os', 'virtualization', 'network', 'database', 'middleware', 'observability']
  const components = profile ? [...profile.components, ...profile.unknowns] : []
  return (
    <div className="rounded-lg border border-ops-surface1/45 bg-ops-dark/20 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="text-xs font-bold text-ops-overlay">业务画像分层</div>
        <div className="text-[11px] text-ops-overlay">标签右下角为来源</div>
      </div>
      <div className="space-y-2">
        {layers.map((layer) => {
          const items = components.filter((component) => component.layer === layer)
          const knownItems = items.filter((component) => component.confidence !== 'unknown')
          const unknownItems = items.filter((component) => component.confidence === 'unknown')
          return (
            <div key={layer} className="grid gap-2 rounded bg-ops-surface0/25 px-3 py-2 text-xs md:grid-cols-[72px_1fr]">
              <div className="font-bold text-ops-text">{LAYER_LABELS[layer] || layer}</div>
              <div className="flex flex-wrap gap-2">
                {knownItems.map((item) => (
                  <button
                    key={item.id}
                    className="rounded bg-ops-accent/12 px-2 py-1 text-left text-ops-subtext hover:bg-ops-accent/18"
                    title={`${SOURCE_LABELS[item.source] || item.source} · ${item.component_type}`}
                    onClick={() => onEdit(item)}
                  >
                    <span>{item.name}</span>
                    <span className="ml-1 text-[10px] text-ops-overlay">{SOURCE_LABELS[item.source] || item.source}</span>
                  </button>
                ))}
                {unknownItems.map((item) => (
                  <button
                    key={item.id}
                    className="rounded bg-amber-400/10 px-2 py-1 text-amber-200 hover:bg-amber-400/15"
                    onClick={() => onEdit(item)}
                    title="点击补充为真实画像项"
                  >
                    {item.name} · 补充
                  </button>
                ))}
                {!items.length && <span className="text-ops-overlay">未识别</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ProfileAnalysisCard({
  analysis,
}: {
  analysis: {
    summary: string
    conclusion: string
    readyScore: number
    gaps: string[]
    nextAction: string
  }
}) {
  const readyTone = analysis.readyScore >= 70 ? 'text-ops-success' : analysis.readyScore >= 40 ? 'text-amber-200' : 'text-ops-alert'
  return (
    <div className="rounded-lg border border-ops-surface1/45 bg-ops-dark/25 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-bold text-ops-overlay">AI 画像分析</div>
          <div className="mt-2 text-sm font-bold leading-6 text-ops-text">{analysis.summary}</div>
        </div>
        <div className={`font-mono text-xl font-black ${readyTone}`}>{analysis.readyScore}%</div>
      </div>
      <div className="mt-2 text-sm leading-6 text-ops-subtext">{analysis.conclusion}</div>
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded bg-ops-accent/15 px-2 py-1 text-xs font-bold text-ops-accent">{analysis.nextAction}</span>
        {analysis.gaps.slice(0, 3).map((gap) => (
          <span key={gap} className="rounded bg-amber-400/10 px-2 py-1 text-xs text-amber-200">{gap}</span>
        ))}
      </div>
    </div>
  )
}

function InvestigationSummary({ investigation }: { investigation: ObservabilityInvestigation }) {
  return (
    <div className="rounded-lg border border-ops-surface0/70 bg-ops-dark/20 px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-bold text-ops-text">{investigation.title}</div>
        <span className="rounded bg-ops-accent/15 px-2 py-1 text-xs text-ops-accent">{investigation.status}</span>
      </div>
      <div className="mt-1 text-xs text-ops-subtext">{investigation.symptom}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {(investigation.tasks || []).slice(0, 4).map((task) => (
          <span key={task.id} className="rounded bg-ops-surface0/55 px-2 py-1 text-xs text-ops-subtext">
            {task.agent_role} · {task.status}
          </span>
        ))}
      </div>
    </div>
  )
}

function MasterAgentBubble({ message }: { message: MasterAgentMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[92%] rounded-lg px-3 py-2 text-sm leading-6 ${
        isUser
          ? 'bg-ops-accent text-ops-dark'
          : 'bg-transparent text-ops-subtext'
      }`}
      >
        <div className={`mb-1 text-[11px] font-bold ${isUser ? 'text-ops-dark/70' : 'text-ops-overlay'}`}>
          {isUser ? '运维人员' : '主 Agent'} · {message.time}
        </div>
        <div>{message.content}</div>
      </div>
    </div>
  )
}

function DiscoveryCandidateCard({ candidate }: { candidate: ObservabilityDiscoveryCandidate }) {
  const proposedName = candidate.proposed_component?.name || candidate.proposed_relationship?.relationship_type || candidate.candidate_type
  return (
    <div className="rounded-lg border border-ops-surface0/80 bg-ops-surface0/35 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-bold text-ops-text">{candidate.title}</div>
          <div className="mt-1 text-xs text-ops-subtext">{candidate.candidate_type} · {candidate.confidence} · {proposedName}</div>
        </div>
        <span className="rounded bg-amber-400/10 px-2 py-1 text-xs text-amber-200">{candidate.status}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-ops-subtext">{candidate.summary}</p>
      <div className="mt-4">
        <div className="text-xs font-bold text-ops-overlay">证据摘要</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {candidate.evidence_summary.map((item) => (
            <span key={item} className="rounded bg-ops-dark/35 px-2 py-1 text-xs text-ops-subtext">{item}</span>
          ))}
        </div>
      </div>
      <div className="mt-4">
        <div className="text-xs font-bold text-ops-overlay">建议动作</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {candidate.suggested_actions.map((item) => (
            <span key={item} className="rounded border border-ops-surface1/50 px-2 py-1 text-xs text-ops-subtext">{item}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function InvestigationCard({
  investigation,
  onAppendEvidence,
  onAppendTaskEvidence,
  onAppendRootCause,
  onComposeDispatchDraft,
}: {
  investigation: ObservabilityInvestigation
  onAppendEvidence: () => void
  onAppendTaskEvidence: (task: ObservabilityInvestigation['tasks'][number]) => void
  onAppendRootCause: () => void
  onComposeDispatchDraft: () => void
}) {
  const [expandedEvidenceId, setExpandedEvidenceId] = useState<string | null>(null)

  return (
    <div className="rounded-lg border border-ops-surface0/80 bg-ops-surface0/35 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-bold text-ops-text">{investigation.title}</div>
          <div className="mt-1 text-xs text-ops-subtext">{investigation.time_window || '未指定时间窗口'} · {investigation.severity}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-ops-accent/15 px-2 py-1 text-xs text-ops-accent">{investigation.status}</span>
          <button className="ops-control rounded-lg px-3 py-1.5 text-xs font-bold" onClick={onAppendEvidence}>
            追加证据
          </button>
          <button className="ops-control rounded-lg px-3 py-1.5 text-xs font-bold" onClick={onAppendRootCause}>
            生成根因候选
          </button>
          <button className="ops-primary-action rounded-lg px-3 py-1.5 text-xs font-bold" onClick={onComposeDispatchDraft}>
            生成协同指令
          </button>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-ops-subtext">{investigation.symptom}</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div>
          <div className="text-xs font-bold text-ops-overlay">Agent 任务</div>
          <div className="mt-2 space-y-2">
            {(investigation.tasks?.length ? investigation.tasks : investigation.agent_plan.map((step, index) => ({
              id: `${investigation.id}-plan-${index}`,
              investigation_id: investigation.id,
              output_summary: step,
              agent_role: `Agent ${index + 1}`,
              status: 'pending',
              task_type: 'plan',
              input_json: {},
              started_at: '',
              finished_at: '',
              error_message: '',
            }))).map((task, index) => (
              <div key={task.id} className="grid gap-1 rounded bg-ops-dark/30 px-3 py-2 text-xs text-ops-subtext md:grid-cols-[24px_130px_1fr_auto_auto]">
                <span className="font-mono text-ops-accent">{index + 1}</span>
                <span className="font-bold text-ops-text">{task.agent_role}</span>
                <span>{task.output_summary}</span>
                <span className="font-mono text-ops-overlay">{task.status}</span>
                <button className="text-xs font-bold text-ops-accent hover:text-ops-accent2" onClick={() => onAppendTaskEvidence(task)}>
                  回填证据
                </button>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs font-bold text-ops-overlay">根因候选</div>
          <div className="mt-2 space-y-2">
            {investigation.root_causes?.length
              ? investigation.root_causes.map((item) => (
                <div key={item.id} className="rounded border border-ops-surface1/50 px-3 py-2 text-xs text-ops-subtext">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-bold text-ops-text">{item.title}</div>
                    <span className={`rounded px-2 py-1 font-bold ${rootCauseStatusClass(item.status)}`}>
                      {rootCauseStatusLabel(item.status)}
                    </span>
                  </div>
                  <div className="mt-1">{item.description || '等待更多证据'}</div>
                  <div className="mt-2 flex flex-wrap gap-2 font-mono text-[11px] text-ops-overlay">
                    <span>{item.likelihood} · {item.confidence}</span>
                    <span>证据 {item.supporting_evidence_ids.length}</span>
                    {item.contradicting_evidence_ids.length > 0 && <span>反证 {item.contradicting_evidence_ids.length}</span>}
                  </div>
                  {item.recommended_next_steps.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {item.recommended_next_steps.slice(0, 3).map((step) => (
                        <div key={step} className="rounded bg-ops-dark/25 px-2 py-1 text-[11px] text-ops-subtext">{step}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))
              : investigation.root_cause_candidates.map((item) => (
                <div key={item} className="rounded border border-ops-surface1/50 px-3 py-2 text-xs text-ops-subtext">{item}</div>
              ))}
          </div>
          <div className="mt-3 font-mono text-xs text-ops-overlay">evidence: {investigation.evidence_count}</div>
        </div>
      </div>
      {investigation.evidence?.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-bold text-ops-overlay">证据链</div>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            {investigation.evidence.map((evidence) => (
              <div key={evidence.id} className="rounded border border-ops-surface1/45 bg-ops-dark/20 px-3 py-2 text-xs text-ops-subtext">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-bold text-ops-text">{evidence.title}</span>
                  <span className="font-mono text-ops-overlay">{evidence.evidence_type}</span>
                </div>
                <div className="mt-1 leading-5">{evidence.summary}</div>
                <button
                  className="mt-2 text-xs font-bold text-ops-accent hover:text-ops-accent2"
                  onClick={() => setExpandedEvidenceId(expandedEvidenceId === evidence.id ? null : evidence.id)}
                >
                  {expandedEvidenceId === evidence.id ? '收起详情' : '查看详情'}
                </button>
                {expandedEvidenceId === evidence.id && (
                  <div className="mt-2 space-y-2 rounded border border-ops-surface1/40 bg-ops-dark/30 p-3">
                    {runTraceEvidenceId(evidence) && (
                      <div className="flex flex-wrap items-center gap-2">
                        <EvidenceReferenceChip
                          kind="evidence"
                          label="Run Trace 证据"
                          value={runTraceEvidenceId(evidence)}
                          title="Run Trace 工具证据引用"
                          onClick={() => setExpandedEvidenceId(evidence.id)}
                        />
                        <span className="font-mono text-[11px] text-ops-overlay">
                          {runTraceEvidenceSessionId(evidence) || '-'} · {runTraceEvidenceToolName(evidence) || '-'}
                        </span>
                      </div>
                    )}
                    <div className="grid gap-2 font-mono text-[11px] text-ops-overlay md:grid-cols-2">
                      <span>confidence: {evidence.confidence}</span>
                      <span>time: {evidence.timestamp || evidence.created_at || '-'}</span>
                    </div>
                    <div className="break-all font-mono text-[11px] text-ops-overlay">raw_ref: {evidence.raw_ref || '-'}</div>
                    <div className="whitespace-pre-wrap rounded bg-ops-dark/40 p-2 text-[11px] leading-5 text-ops-subtext">
                      {evidence.raw_excerpt || '暂无原始摘录'}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function buildInvestigationDispatchDraft(investigation: ObservabilityInvestigation): string {
  const taskLines = (investigation.tasks || []).map((task, index) => (
    `- ${index + 1}. ${task.agent_role} | ${task.task_type} | ${task.output_summary} | input=${JSON.stringify(task.input_json || {})}`
  ))
  return [
    '请基于以下可观测排查事件生成多 Agent 协同任务草稿，先确认任务内容后再调用 dispatch_sub_agents。',
    'dispatch_scope: global',
    'group_name: ',
    `investigation_id: ${investigation.id}`,
    `title: ${investigation.title}`,
    `symptom: ${investigation.symptom || '-'}`,
    `time_window: ${investigation.time_window || '最近 2 小时'}`,
    `severity: ${investigation.severity || 'unknown'}`,
    '',
    '候选任务：',
    ...(taskLines.length ? taskLines : ['- Summary Agent | correlate_evidence | 汇总时间线、证据和根因候选 | input={"read_only":true}']),
    '',
    '执行要求：',
    '- 先调用 list_active_sessions，只能从返回的在线会话里选择目标。',
    '- target_session_id 必须由 list_active_sessions 返回，不能凭空填写。',
    '- 对每个可匹配目标生成一条 tasks 记录，再调用 dispatch_sub_agents。',
    '- 所有任务保持只读排查，不做写入、重启、变更或通知外发。',
    '- 如果目标无法匹配，先说明缺少哪个会话/资产，不要扩大范围。',
  ].join('\n')
}

function runTraceEvidenceId(evidence: ObservabilityEvidence): string {
  return String(evidence.tool_evidence?.evidence_id || evidence.raw_ref || '')
}

function runTraceEvidenceSessionId(evidence: ObservabilityEvidence): string {
  return String(evidence.tool_evidence?.session_id || '')
}

function runTraceEvidenceToolName(evidence: ObservabilityEvidence): string {
  return String(evidence.tool_evidence?.tool_name || '')
}

function rootCauseStatusLabel(status: string): string {
  if (status === 'confirmed') return '已确认'
  if (status === 'rejected') return '已驳回'
  if (status === 'watching') return '观察中'
  return '待复核'
}

function rootCauseStatusClass(status: string): string {
  if (status === 'confirmed') return 'bg-emerald-400/15 text-emerald-200'
  if (status === 'rejected') return 'bg-rose-400/15 text-rose-200'
  if (status === 'watching') return 'bg-sky-400/15 text-sky-200'
  return 'bg-amber-400/15 text-amber-200'
}
