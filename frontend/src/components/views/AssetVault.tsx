import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import {
  applyAssetNormalization,
  deleteAsset,
  getAssetTypes,
  getAssetVerificationMatrix,
  getAssetVerificationRuns,
  getDashboardOverview,
  getProtocolVerificationOverview,
  getSavedAssets,
  previewAssetNormalization,
  verifyAsset,
} from '@/api/client'
import type { Asset, AssetVerificationMatrix, AssetVerificationRun, ProtocolVerificationOverview } from '@/types'

export default function AssetVault() {
  const assets = useStore((s) => s.assets)
  const setAssets = useStore((s) => s.setAssets)
  const openModal = useStore((s) => s.openModal)
  const addToast = useStore((s) => s.addToast)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [protocolFilter, setProtocolFilter] = useState('all')
  const [categoryLabels, setCategoryLabels] = useState<Record<string, string>>({})
  const [overview, setOverview] = useState<Record<string, number> | null>(null)
  const [verificationOverview, setVerificationOverview] = useState<ProtocolVerificationOverview | null>(null)
  const [verificationPanel, setVerificationPanel] = useState<{
    asset: Asset
    matrix: AssetVerificationMatrix | null
    runs: AssetVerificationRun[]
    loading: boolean
    running: boolean
  } | null>(null)

  const loadAssets = useCallback(async () => {
    try {
      const res = await getSavedAssets()
      setAssets(res.data.assets || [])
      getDashboardOverview().then((r) => setOverview(r.data.summary)).catch(() => setOverview(null))
      getProtocolVerificationOverview().then((r) => setVerificationOverview(r.data)).catch(() => setVerificationOverview(null))
    } catch {
      addToast('加载资产列表失败', 'error')
    }
  }, [setAssets, addToast])

  useEffect(() => { loadAssets() }, [loadAssets])
  useEffect(() => {
    getAssetTypes()
      .then((r) => {
        setCategoryLabels(Object.fromEntries((r.data.categories || []).map((c) => [c.id, c.label])))
      })
      .catch(() => setCategoryLabels({}))
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('确定要从资产中移除此资产？')) return
    try {
      await deleteAsset(id)
      setAssets(assets.filter((a) => a.id !== id))
      addToast('资产已移除', 'success')
    } catch {
      addToast('删除失败', 'error')
    }
  }

  const handleConnect = (asset: Asset) => {
    sessionStorage.setItem('prefill_asset', JSON.stringify(asset))
    openModal('connect')
  }

  const handleNormalizeAssets = async () => {
    try {
      const preview = await previewAssetNormalization()
      const summary = preview.data.summary
      const totalIssues = summary.rows_to_update + summary.duplicates_to_remove
      if (totalIssues <= 0) {
        addToast('资产数据无需规范化', 'success')
        return
      }
      const ok = confirm(
        `将规范化 ${summary.rows_to_update} 条资产，并删除 ${summary.duplicates_to_remove} 条重复资产。执行前会生成备份，是否继续？`
      )
      if (!ok) return
      const res = await applyAssetNormalization()
      addToast(`资产规范化完成，删除重复 ${res.data.removed_ids.length} 条`, 'success')
      await loadAssets()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '资产规范化失败', 'error')
    }
  }

  const openVerification = async (asset: Asset) => {
    setVerificationPanel({ asset, matrix: null, runs: [], loading: true, running: false })
    try {
      const [matrixRes, runsRes] = await Promise.all([
        getAssetVerificationMatrix(asset.id),
        getAssetVerificationRuns(asset.id, 10),
      ])
      setVerificationPanel({
        asset,
        matrix: matrixRes.data.matrix,
        runs: runsRes.data.runs || [],
        loading: false,
        running: false,
      })
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '加载验证矩阵失败', 'error')
      setVerificationPanel((current) => current ? { ...current, loading: false } : current)
    }
  }

  const runVerification = async () => {
    if (!verificationPanel) return
    const asset = verificationPanel.asset
    setVerificationPanel({ ...verificationPanel, running: true })
    try {
      const res = await verifyAsset(asset.id)
      const runs = await getAssetVerificationRuns(asset.id, 10)
      setVerificationPanel((current) => current ? {
        ...current,
        runs: runs.data.runs || [res.data.run],
        running: false,
      } : current)
      getProtocolVerificationOverview().then((r) => setVerificationOverview(r.data)).catch(() => {})
      addToast(`资产验证完成：${res.data.run.status}`, res.data.run.status === 'success' ? 'success' : 'error')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '资产验证失败', 'error')
      setVerificationPanel((current) => current ? { ...current, running: false } : current)
    }
  }

  const filtered = assets.filter((a) => {
    const q = search.toLowerCase()
    const category = String(a.extra_args?.category || 'other')
    const protocol = a.protocol || a.asset_type || 'unknown'
    const matchesSearch = !q
      || a.host.toLowerCase().includes(q)
      || (a.remark || '').toLowerCase().includes(q)
      || (a.username || '').toLowerCase().includes(q)
      || (a.asset_type || '').toLowerCase().includes(q)
      || protocol.toLowerCase().includes(q)
    const matchesCategory = categoryFilter === 'all' || category === categoryFilter
    const matchesProtocol = protocolFilter === 'all' || protocol === protocolFilter
    return matchesSearch && matchesCategory && matchesProtocol
  })

  const availableCategories = Array.from(new Set(assets.map((a) => String(a.extra_args?.category || 'other')))).sort()
  const availableProtocols = Array.from(new Set(assets.map((a) => a.protocol || a.asset_type || 'unknown'))).sort()
  const matrixByAssetId = new Map((verificationOverview?.matrix || []).map((item) => [item.asset.id, item]))

  const grouped: Record<string, Asset[]> = {}
  filtered.forEach((a) => {
    const category = String(a.extra_args?.category || 'other')
    const g = `${categoryLabels[category] || category.toUpperCase()}`
    if (!grouped[g]) grouped[g] = []
    grouped[g].push(a)
  })

  const protocolBadge = (p: string) => {
    const colors: Record<string, string> = {
      ssh: 'bg-blue-500/20 text-blue-400',
      mysql: 'bg-purple-500/20 text-purple-400',
      oracle: 'bg-purple-500/20 text-purple-400',
      postgresql: 'bg-purple-500/20 text-purple-400',
      mssql: 'bg-purple-500/20 text-purple-400',
      redis: 'bg-red-500/20 text-red-400',
      mongodb: 'bg-emerald-500/20 text-emerald-400',
      http_api: 'bg-green-500/20 text-green-400',
      winrm: 'bg-orange-500/20 text-orange-400',
      k8s: 'bg-cyan-500/20 text-cyan-400',
      redfish: 'bg-amber-500/20 text-amber-400',
      snmp: 'bg-slate-500/20 text-slate-300',
    }
    return colors[p] || 'bg-ops-surface1 text-ops-subtext'
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-ops-accent">Datacenter Inventory</p>
            <h1 className="mt-1 text-2xl font-black tracking-tight text-ops-text">资产中心</h1>
            <p className="text-sm text-ops-subtext mt-1">统一管理资产凭据、登录协议、巡检入口和 AI 会话上下文</p>
          </div>
          <div className="flex gap-2">
            <input type="text" placeholder="搜索资产、账号、协议..." value={search} onChange={(e) => setSearch(e.target.value)}
              className="bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-1.5 text-sm text-ops-text outline-none focus:border-ops-accent" />
            <button onClick={() => openModal('connect')}
              className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors">+ 新建连接</button>
            <button onClick={handleNormalizeAssets}
              className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors">规范化</button>
            <button onClick={loadAssets}
              className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors">🔄</button>
          </div>
        </div>

        {overview && (
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-5">
            <OverviewCard label="资产总数" value={overview.asset_total || 0} />
            <OverviewCard label="在线会话" value={overview.active_sessions || 0} />
            <OverviewCard label="资产分类" value={overview.asset_categories || 0} />
            <OverviewCard label="协议类型" value={overview.protocols || 0} />
            <OverviewCard label="验证就绪" value={verificationOverview?.summary.ready_assets || 0} />
          </div>
        )}

        <div className="mb-6 rounded-2xl border border-ops-surface0 bg-ops-panel/60 p-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-ops-text">资产目录过滤</div>
              <div className="text-[11px] text-ops-overlay">按分类和协议确认资产中心覆盖范围，筛选不会影响保存数据。</div>
            </div>
            {(categoryFilter !== 'all' || protocolFilter !== 'all' || search) && (
              <button
                onClick={() => { setCategoryFilter('all'); setProtocolFilter('all'); setSearch('') }}
                className="rounded-lg bg-ops-surface0 px-2.5 py-1 text-xs text-ops-subtext hover:text-ops-text"
              >
                清空过滤
              </button>
            )}
          </div>
          <FilterRow
            label="分类"
            value={categoryFilter}
            options={availableCategories.map((id) => ({ id, label: categoryLabels[id] || id.toUpperCase() }))}
            onChange={setCategoryFilter}
          />
          <FilterRow
            label="协议"
            value={protocolFilter}
            options={availableProtocols.map((id) => ({ id, label: id.toUpperCase() }))}
            onChange={setProtocolFilter}
          />
        </div>

        {Object.entries(grouped).map(([group, items]) => (
          <div key={group} className="mb-6">
            <h2 className="text-sm font-semibold text-ops-subtext mb-3">{group} ({items.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {items.map((asset) => (
                <div key={asset.id} className="ops-glass rounded-2xl border p-4 transition-all hover:-translate-y-0.5 hover:border-ops-accent/45">
                  {(() => {
                    const matrix = matrixByAssetId.get(asset.id)
                    return matrix ? <VerificationStatusStrip matrix={matrix} /> : null
                  })()}
                  <div className="flex items-start justify-between mb-2">
                    <div className="min-w-0">
                      <div className="font-medium text-ops-text text-sm truncate">{asset.remark || asset.host}</div>
                      <div className="text-xs text-ops-overlay mt-0.5">{asset.username}@{asset.host}:{asset.port}</div>
                    </div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${protocolBadge(asset.protocol || asset.asset_type)}`}>
                      {asset.asset_type.toUpperCase()} / {(asset.protocol || '').toUpperCase()}
                    </span>
                  </div>
                  <div className="mb-2 flex flex-wrap gap-1.5 text-[10px]">
                    <span className="rounded bg-ops-dark px-1.5 py-0.5 text-ops-overlay">
                      {categoryLabels[String(asset.extra_args?.category || 'other')] || String(asset.extra_args?.category || 'other').toUpperCase()}
                    </span>
                    {(asset.tags || []).slice(0, 3).map((tag) => (
                      <span key={tag} className="rounded bg-ops-surface0 px-1.5 py-0.5 text-ops-subtext">{tag}</span>
                    ))}
                  </div>
                  {asset.skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {asset.skills.slice(0, 3).map((sk) => (
                        <span key={sk} className="text-[10px] bg-ops-surface0 text-ops-subtext px-1.5 py-0.5 rounded">{sk}</span>
                      ))}
                      {asset.skills.length > 3 && <span className="text-[10px] text-ops-overlay">+{asset.skills.length - 3}</span>}
                    </div>
                  )}
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handleConnect(asset)} className="flex-1 bg-ops-accent/15 text-ops-accent text-xs py-1.5 rounded-lg hover:bg-ops-accent/25 transition-colors">✏️ 编辑 / 连接</button>
                    <button onClick={() => void openVerification(asset)} className="bg-ops-success/10 text-ops-success text-xs px-2.5 py-1.5 rounded-lg hover:bg-ops-success/20 transition-colors">验证</button>
                    <button onClick={() => handleDelete(asset.id)} className="text-ops-overlay text-xs px-2 py-1.5 rounded-lg hover:text-ops-alert hover:bg-ops-alert/10 transition-colors">🗑️</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="text-center text-ops-subtext py-20">
            <div className="text-4xl mb-3">🏦</div>
            <p>资产中暂无资产</p>
            <p className="text-xs mt-1">连接过的资产会自动保存在这里</p>
          </div>
        )}
      </div>
      {verificationPanel && (
        <VerificationPanel
          panel={verificationPanel}
          onClose={() => setVerificationPanel(null)}
          onRun={() => void runVerification()}
        />
      )}
    </div>
  )
}

function OverviewCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="ops-glass rounded-2xl border p-4">
      <div className="text-[10px] uppercase tracking-[0.18em] text-ops-overlay">{label}</div>
      <div className="mt-2 font-mono text-2xl font-semibold text-ops-text">{value}</div>
    </div>
  )
}

function FilterRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: Array<{ id: string; label: string }>
  onChange: (value: string) => void
}) {
  return (
    <div className="mb-2 flex flex-wrap items-center gap-2 last:mb-0">
      <span className="w-10 text-xs text-ops-overlay">{label}</span>
      <button
        onClick={() => onChange('all')}
        className={`rounded-full px-2.5 py-1 text-[11px] transition-colors ${value === 'all' ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
      >
        全部
      </button>
      {options.map((option) => (
        <button
          key={option.id}
          onClick={() => onChange(option.id)}
          className={`rounded-full px-2.5 py-1 text-[11px] transition-colors ${value === option.id ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

function VerificationStatusStrip({ matrix }: { matrix: AssetVerificationMatrix }) {
  const ready = matrix.status === 'ready'
  return (
    <div className="mb-3 flex items-center justify-between rounded-xl border border-ops-surface0 bg-ops-dark/35 px-2.5 py-2">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${ready ? 'bg-ops-success' : 'bg-ops-alert'}`} />
        <span className="text-[11px] text-ops-subtext">{ready ? '验证矩阵就绪' : '存在验证缺口'}</span>
      </div>
      <span className="font-mono text-[11px] text-ops-overlay">
        {matrix.coverage.supported}/{matrix.coverage.total}
      </span>
    </div>
  )
}

function VerificationPanel({
  panel,
  onClose,
  onRun,
}: {
  panel: {
    asset: Asset
    matrix: AssetVerificationMatrix | null
    runs: AssetVerificationRun[]
    loading: boolean
    running: boolean
  }
  onClose: () => void
  onRun: () => void
}) {
  const latest = panel.runs[0]
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/45" onClick={onClose}>
      <aside
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-ops-surface1 bg-ops-panel p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-ops-accent">Protocol Verification</p>
            <h2 className="mt-1 text-xl font-black text-ops-text">{panel.asset.remark || panel.asset.host}</h2>
            <p className="mt-1 text-sm text-ops-subtext">
              {panel.asset.asset_type}/{panel.asset.protocol || panel.asset.asset_type} · {panel.asset.username}@{panel.asset.host}:{panel.asset.port}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text">关闭</button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button
            onClick={onRun}
            disabled={panel.running || panel.loading}
            className="rounded-xl bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark hover:bg-ops-accent/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {panel.running ? '验证中...' : '执行只读验证'}
          </button>
          {latest && (
            <span className={`rounded-full px-3 py-1 text-xs ${latest.status === 'success' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
              最近结果：{latest.status}
            </span>
          )}
        </div>

        {panel.loading ? (
          <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-6 text-sm text-ops-subtext">正在加载验证矩阵...</div>
        ) : (
          <>
            {panel.matrix && (
              <section className="mb-5 rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-ops-text">验证矩阵</h3>
                  <span className="font-mono text-xs text-ops-overlay">{panel.matrix.coverage.supported}/{panel.matrix.coverage.total}</span>
                </div>
                <div className="space-y-2">
                  {panel.matrix.steps.map((step) => (
                    <div key={step.id} className="rounded-xl bg-ops-surface0/60 px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-ops-text">{step.label}</span>
                        <span className={`rounded px-2 py-0.5 text-[11px] ${step.status === 'supported' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
                          {step.status}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-ops-overlay">{step.description}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {panel.matrix.active_tools.slice(0, 12).map((tool) => (
                    <span key={tool} className="rounded bg-ops-surface0 px-2 py-0.5 font-mono text-[10px] text-ops-subtext">{tool}</span>
                  ))}
                </div>
              </section>
            )}

            <section className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
              <h3 className="mb-3 text-sm font-bold text-ops-text">验证历史</h3>
              <div className="space-y-3">
                {panel.runs.map((run) => (
                  <div key={run.id} className="rounded-xl border border-ops-surface0 bg-ops-panel/70 p-3">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className={`rounded px-2 py-0.5 text-[11px] ${run.status === 'success' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
                        {run.status}
                      </span>
                      <span className="font-mono text-[11px] text-ops-overlay">{run.id}</span>
                      <span className="ml-auto text-[11px] text-ops-overlay">{run.completed_at}</span>
                    </div>
                    <div className="grid gap-2">
                      {run.steps.map((step) => (
                        <div key={`${run.id}-${step.id}`} className="rounded-lg bg-ops-dark/45 px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs text-ops-text">{step.label}</span>
                            <span className={`text-[11px] ${step.status === 'success' ? 'text-ops-success' : step.status === 'skipped' ? 'text-ops-overlay' : 'text-ops-alert'}`}>
                              {step.status}
                            </span>
                          </div>
                          <p className="mt-1 text-[11px] text-ops-overlay">{step.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {panel.runs.length === 0 && (
                  <div className="py-8 text-center text-sm text-ops-subtext">暂无验证历史，点击“执行只读验证”开始。</div>
                )}
              </div>
            </section>
          </>
        )}
      </aside>
    </div>
  )
}
