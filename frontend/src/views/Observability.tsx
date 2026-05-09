import { useCallback, useEffect, useMemo, useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import { useStore } from '@/store'
import {
  bindObservabilityAsset,
  bindObservabilitySession,
  checkObservableSource,
  confirmReviewItem,
  createDiscoveryRun,
  createInvestigation,
  createObservabilityComponent,
  createObservabilityRelationship,
  createObservabilitySystem,
  createSourceFromSession,
  dispatchInvestigation,
  getDiscoveryRun,
  getInvestigation,
  getObservabilityTopology,
  listInvestigations,
  listObservableSources,
  listObservabilitySystems,
  listProfilePacks,
  planInvestigation,
  rejectReviewItem,
} from '@/features/observability/api'
import BusinessSystemList from '@/features/observability/BusinessSystemList'
import BusinessSystemProfile from '@/features/observability/BusinessSystemProfile'
import InvestigationCenter from '@/features/observability/InvestigationCenter'
import ObservableSources from '@/features/observability/ObservableSources'
import ProfileDiscovery from '@/features/observability/ProfileDiscovery'
import type {
  DiscoveryRun,
  Investigation,
  ObservableSource,
  ObservabilityArchitectureTemplate,
  ObservabilitySystem,
  ObservabilityTopology,
  ProfilePack,
} from '@/features/observability/types'

type TabId = 'systems' | 'discovery' | 'investigations' | 'sources' | 'packs'

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'systems', label: '业务系统' },
  { id: 'discovery', label: '画像发现' },
  { id: 'investigations', label: '排查事件' },
  { id: 'sources', label: '观测源' },
  { id: 'packs', label: '画像包' },
]

export default function Observability() {
  const addToast = useStore((s) => s.addToast)
  const [tab, setTab] = useState<TabId>('systems')
  const [systems, setSystems] = useState<ObservabilitySystem[]>([])
  const [selectedSystemId, setSelectedSystemId] = useState<string | null>(null)
  const [topology, setTopology] = useState<ObservabilityTopology | null>(null)
  const [sources, setSources] = useState<ObservableSource[]>([])
  const [packs, setPacks] = useState<ProfilePack[]>([])
  const [discoveryRun, setDiscoveryRun] = useState<DiscoveryRun | null>(null)
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const selectedSystem = useMemo(
    () => systems.find((system) => system.id === selectedSystemId) || systems[0] || null,
    [selectedSystemId, systems]
  )
  const selectedInvestigation = useMemo(
    () => investigations.find((item) => item.id === selectedInvestigationId) || investigations[0] || null,
    [investigations, selectedInvestigationId]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [systemsRes, sourcesRes, packsRes, investigationsRes] = await Promise.all([
        listObservabilitySystems(),
        listObservableSources(),
        listProfilePacks(),
        listInvestigations(),
      ])
      const nextSystems = systemsRes.data.systems || []
      setSystems(nextSystems)
      setSources(sourcesRes.data.sources || [])
      setPacks(packsRes.data.profile_packs || [])
      setInvestigations(investigationsRes.data.investigations || [])
      setSelectedSystemId((current) => current || nextSystems[0]?.id || null)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '加载可观测性数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const loadTopology = useCallback(async (systemId: string | null) => {
    if (!systemId) {
      setTopology(null)
      return
    }
    try {
      const res = await getObservabilityTopology(systemId)
      setTopology(res.data.topology)
    } catch (exc) {
      addToast(exc instanceof Error ? exc.message : '加载拓扑失败', 'error')
    }
  }, [addToast])

  useEffect(() => { void loadTopology(selectedSystem?.id || null) }, [loadTopology, selectedSystem?.id])

  const createSystem = async (payload: Record<string, unknown>) => {
    const res = await createObservabilitySystem(payload)
    addToast('业务系统已创建', 'success')
    setSelectedSystemId(res.data.system.id)
    await load()
  }

  const createComponent = async (payload: Record<string, unknown>) => {
    if (!selectedSystem) return
    await createObservabilityComponent(selectedSystem.id, payload)
    addToast('节点已添加', 'success')
    await load()
    await loadTopology(selectedSystem.id)
  }

  const createArchitectureTemplate = async (template: ObservabilityArchitectureTemplate) => {
    if (!selectedSystem) return
    try {
      const created: Record<string, string> = {}
      for (const node of template.nodes) {
        const res = await createObservabilityComponent(selectedSystem.id, {
          name: node.name,
          component_type: node.component_type,
          workload_family: node.workload_family,
          status: node.status || 'active',
          confidence: node.confidence || 'inferred',
          source: 'architecture_template',
          metadata: { ...(node.metadata || {}), template_id: template.id, template_title: template.title, template_layer: node.layer },
        })
        created[node.key] = res.data.component.id
      }

      for (const relationship of template.relationships) {
        const fromComponentId = created[relationship.from]
        const toComponentId = created[relationship.to]
        if (!fromComponentId || !toComponentId) continue
        await createObservabilityRelationship(selectedSystem.id, {
          from_component_id: fromComponentId,
          to_component_id: toComponentId,
          relationship_type: relationship.relationship_type,
          status: relationship.status || 'pending_review',
          confidence: relationship.confidence || 'inferred',
          source: 'architecture_template',
          metadata: { ...(relationship.metadata || {}), template_id: template.id, template_title: template.title },
        })
      }

      addToast(`${template.title} 模板已添加`, 'success')
      await load()
      await loadTopology(selectedSystem.id)
    } catch (exc) {
      addToast(exc instanceof Error ? exc.message : '添加架构模板失败', 'error')
    }
  }

  const bindAsset = async (componentId: string, assetId: string) => {
    if (!selectedSystem) return
    await bindObservabilityAsset(selectedSystem.id, { component_id: componentId, asset_id: assetId })
    addToast('资产绑定已保存', 'success')
    await load()
    await loadTopology(selectedSystem.id)
  }

  const bindSession = async (componentId: string, sessionId: string) => {
    if (!selectedSystem) return
    await bindObservabilitySession(selectedSystem.id, { component_id: componentId, session_id: sessionId })
    addToast('会话绑定已保存', 'success')
    await load()
    await loadTopology(selectedSystem.id)
  }

  const runDiscovery = async () => {
    if (!selectedSystem) return
    const res = await createDiscoveryRun(selectedSystem.id)
    const detail = await getDiscoveryRun(res.data.run.id)
    setDiscoveryRun(detail.data.run)
    addToast('发现运行已生成', 'success')
  }

  const refreshDiscovery = async (runId: string) => {
    const detail = await getDiscoveryRun(runId)
    setDiscoveryRun(detail.data.run)
    await loadTopology(selectedSystem?.id || null)
    await load()
  }

  const promoteSource = async (payload: Record<string, unknown>) => {
    await createSourceFromSession(payload)
    addToast('观测源已登记', 'success')
    await load()
    await loadTopology(selectedSystem?.id || null)
  }

  const createInvestigationAction = async (payload: Record<string, unknown>) => {
    if (!payload.system_id) {
      addToast('请选择业务系统', 'error')
      return
    }
    const res = await createInvestigation(payload)
    setSelectedInvestigationId(res.data.investigation.id)
    addToast('排查事件已创建', 'success')
    await load()
  }

  const refreshInvestigation = async (id: string) => {
    const detail = await getInvestigation(id)
    setInvestigations((current) => {
      const rest = current.filter((item) => item.id !== id)
      return [detail.data.investigation, ...rest]
    })
    setSelectedInvestigationId(id)
  }

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="业务系统可观测性"
          title="可观测性"
          description="以业务系统画像为中心，绑定资产、会话和观测源，把 AI 发现、证据链和根因候选放到同一个排查工作间。"
          actions={<button onClick={() => void load()} className="ops-control rounded-lg px-4 py-2 text-sm font-semibold">刷新</button>}
        />

        {error && <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">{error}</div>}

        <div className="mb-4 flex flex-wrap gap-2">
          {TABS.map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`rounded-lg border px-4 py-2 text-sm font-semibold ${tab === item.id ? 'border-ops-accent bg-ops-accent/15 text-ops-accent' : 'border-ops-surface0 bg-ops-surface0/45 text-ops-subtext hover:text-ops-text'}`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {tab === 'systems' && (
          <BusinessSystemList
            systems={systems}
            loading={loading}
            selectedId={selectedSystem?.id || null}
            onSelect={(system) => { setSelectedSystemId(system.id); setTab('systems') }}
            onCreate={createSystem}
            onRefresh={() => void load()}
          />
        )}
        {tab === 'systems' && selectedSystem && (
          <div className="mt-4">
            <BusinessSystemProfile
              system={selectedSystem}
              topology={topology}
              onAddComponent={createComponent}
              onCreateTemplate={createArchitectureTemplate}
              onBindAsset={bindAsset}
              onBindSession={bindSession}
            />
          </div>
        )}
        {tab === 'discovery' && (
          <ProfileDiscovery
            system={selectedSystem}
            run={discoveryRun}
            onRun={runDiscovery}
            onConfirm={async (itemId) => {
              await confirmReviewItem(itemId)
              addToast('关系已确认', 'success')
              if (discoveryRun) await refreshDiscovery(discoveryRun.id)
            }}
            onReject={async (itemId) => {
              await rejectReviewItem(itemId)
              addToast('关系已拒绝', 'success')
              if (discoveryRun) await refreshDiscovery(discoveryRun.id)
            }}
          />
        )}
        {tab === 'investigations' && (
          <InvestigationCenter
            systems={systems}
            investigations={investigations}
            selected={selectedInvestigation}
            onSelect={setSelectedInvestigationId}
            onCreate={createInvestigationAction}
            onPlan={async (id) => { await planInvestigation(id); addToast('任务计划已生成', 'success'); await refreshInvestigation(id) }}
            onDispatch={async (id) => { await dispatchInvestigation(id); addToast('Agent 调度已完成', 'success'); await refreshInvestigation(id) }}
          />
        )}
        {tab === 'sources' && (
          <ObservableSources
            sources={sources}
            systems={systems}
            selectedSystemId={selectedSystem?.id || null}
            onPromoteSession={promoteSource}
            onCheck={async (sourceId) => { await checkObservableSource(sourceId); addToast('观测源状态已刷新', 'success'); await load() }}
          />
        )}
        {tab === 'packs' && (
          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {packs.map((pack) => (
              <div key={pack.id} className="ops-data-panel p-4">
                <div className="font-semibold text-ops-text">{pack.name}</div>
                <div className="mt-1 font-mono text-xs text-ops-overlay">{pack.id} · {pack.workload_family}</div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {(pack.component_types || []).slice(0, 5).map((item) => <span key={item} className="rounded bg-ops-surface0 px-2 py-0.5 text-[11px] text-ops-subtext">{item}</span>)}
                </div>
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
