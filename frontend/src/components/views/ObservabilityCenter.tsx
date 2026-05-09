import { useEffect, useMemo, useState } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import {
  getObservableSources,
  getObservabilityOverview,
  getObservabilityProfile,
  getObservabilityProfilePacks,
  getObservabilitySystems,
} from '@/api/observability'
import type {
  ObservabilityOverview,
  ObservabilityProfile,
  ObservabilityProfilePack,
  ObservabilitySource,
  ObservabilitySystemSummary,
} from '@/types'

type TabId = 'systems' | 'discovery' | 'investigations' | 'sources' | 'packs'

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'systems', label: '业务系统' },
  { id: 'discovery', label: '画像发现' },
  { id: 'investigations', label: '排查事件' },
  { id: 'sources', label: '观测源' },
  { id: 'packs', label: '画像包' },
]

const LAYER_LABELS: Record<string, string> = {
  business: '业务',
  entry: '入口',
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

export default function ObservabilityCenter() {
  const [activeTab, setActiveTab] = useState<TabId>('systems')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState<ObservabilityOverview | null>(null)
  const [systems, setSystems] = useState<ObservabilitySystemSummary[]>([])
  const [profile, setProfile] = useState<ObservabilityProfile | null>(null)
  const [sources, setSources] = useState<ObservabilitySource[]>([])
  const [packs, setPacks] = useState<ObservabilityProfilePack[]>([])

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [overviewRes, systemsRes, sourcesRes, packsRes] = await Promise.all([
        getObservabilityOverview(),
        getObservabilitySystems(),
        getObservableSources(),
        getObservabilityProfilePacks(),
      ])
      const nextSystems = systemsRes.data.systems || []
      setOverview(overviewRes.data.overview)
      setSystems(nextSystems)
      setSources(sourcesRes.data.sources || [])
      setPacks(packsRes.data.profile_packs || [])
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
          title="可观测性"
          description="按业务系统画像组织资产、会话、观测源和后续多 Agent 排查上下文。"
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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <Metric label="业务系统" value={overview?.system_count || 0} />
          <Metric label="观测源" value={overview?.source_count || 0} />
          <Metric label="画像包" value={overview?.profile_pack_count || 0} />
          <Metric label="未知节点" value={overview?.unknown_count || 0} tone="amber" />
          <Metric label="待确认关系" value={overview?.pending_review_count || 0} tone="blue" />
        </div>

        <div className="ops-data-panel mt-5 overflow-hidden">
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
              <Placeholder
                title="画像发现"
                text={`当前基线系统：${selectedSystem?.system?.name || '暂无'}。下一步会从资产、会话、Prometheus targets 和历史巡检里生成待确认组件与关系。`}
              />
            )}

            {activeTab === 'investigations' && (
              <Placeholder
                title="排查事件"
                text="后续会按业务系统、症状、时间窗口生成只读排查计划，并把各 Agent 结果沉淀成证据链和根因候选。"
              />
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

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded bg-ops-dark/35 px-2 py-2">
      <div className="font-mono text-sm font-black text-ops-text">{value}</div>
      <div className="mt-0.5 text-[11px] text-ops-overlay">{label}</div>
    </div>
  )
}

function Placeholder({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-ops-surface1/60 bg-ops-surface0/25 p-8">
      <h2 className="text-base font-bold text-ops-text">{title}</h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-ops-subtext">{text}</p>
    </div>
  )
}
