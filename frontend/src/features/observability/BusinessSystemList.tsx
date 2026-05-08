import { useState } from 'react'
import type { ObservabilitySystem } from './types'

export default function BusinessSystemList({
  systems,
  loading,
  selectedId,
  onSelect,
  onCreate,
  onRefresh,
}: {
  systems: ObservabilitySystem[]
  loading: boolean
  selectedId: string | null
  onSelect: (system: ObservabilitySystem) => void
  onCreate: (payload: Record<string, unknown>) => Promise<void>
  onRefresh: () => void
}) {
  const [name, setName] = useState('集团global协作门户')
  const [environment, setEnvironment] = useState('测试环境')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    try {
      await onCreate({
        name,
        environment,
        criticality: 'medium',
        known_components: [
          { name: 'registry 测试环境', component_type: 'container_registry', workload_family: 'container' },
          { name: 'k8s-master 测试环境', component_type: 'k8s_cluster', workload_family: 'container' },
          { name: 'k8s-worker-1 测试环境', component_type: 'os_host', workload_family: 'os' },
          { name: 'k8s-worker-2 测试环境', component_type: 'os_host', workload_family: 'os' },
          { name: '中间件服务器 测试环境', component_type: 'middleware', workload_family: 'middleware' },
        ],
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="ops-data-panel overflow-hidden">
        <div className="ops-data-toolbar m-3 mb-0 flex items-center justify-between px-4 py-3">
          <div>
            <h2 className="text-base font-bold text-ops-text">业务系统</h2>
            <p className="mt-1 text-xs text-ops-subtext">面向业务的画像入口，允许不完整架构先进入排查。</p>
          </div>
          <button onClick={onRefresh} className="ops-control rounded-lg px-3 py-1.5 text-xs font-semibold">刷新</button>
        </div>
        <div className="overflow-x-auto p-3">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="text-xs text-ops-overlay">
              <tr>
                {['业务系统', '环境', '组件数', '未知节点', '待确认关系', '绑定资产', '绑定会话', '观测源', '画像完整度', '操作'].map((item) => (
                  <th key={item} className="px-3 py-2 font-semibold">{item}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {systems.map((system) => (
                <tr key={system.id} className={`border-t border-ops-surface0/70 ${selectedId === system.id ? 'bg-ops-accent/10' : ''}`}>
                  <td className="px-3 py-3">
                    <div className="font-semibold text-ops-text">{system.name}</div>
                    <div className="text-xs text-ops-overlay">{system.owner || '未设置负责人'}</div>
                  </td>
                  <td className="px-3 py-3 text-ops-subtext">{system.environment}</td>
                  <td className="px-3 py-3 font-mono text-ops-text">{system.component_count || 0}</td>
                  <td className="px-3 py-3 font-mono text-ops-alert">{system.unknown_count || 0}</td>
                  <td className="px-3 py-3 font-mono text-ops-subtext">{system.pending_relationship_count || 0}</td>
                  <td className="px-3 py-3 font-mono text-ops-subtext">{system.bound_asset_count || 0}</td>
                  <td className="px-3 py-3 font-mono text-ops-subtext">{system.bound_session_count || 0}</td>
                  <td className="px-3 py-3 font-mono text-ops-subtext">{system.observable_source_count || 0}</td>
                  <td className="px-3 py-3">
                    <div className="h-2 w-28 rounded-full bg-ops-surface0">
                      <div className="h-2 rounded-full bg-ops-accent" style={{ width: `${system.profile_completeness || 0}%` }} />
                    </div>
                    <div className="mt-1 text-xs text-ops-overlay">{system.profile_completeness || 0}%</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button className="ops-control rounded-lg px-2.5 py-1 text-xs" onClick={() => onSelect(system)}>查看画像</button>
                      <button className="ops-control rounded-lg px-2.5 py-1 text-xs" onClick={() => onSelect(system)}>AI发现</button>
                      <button className="ops-control rounded-lg px-2.5 py-1 text-xs" onClick={() => onSelect(system)}>发起排查</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && systems.length === 0 && (
                <tr><td colSpan={10} className="px-3 py-12 text-center text-sm text-ops-subtext">暂无业务系统</td></tr>
              )}
            </tbody>
          </table>
          {loading && <div className="px-3 py-6 text-sm text-ops-overlay">正在加载业务系统...</div>}
        </div>
      </div>

      <div className="ops-data-panel p-5">
        <h2 className="text-base font-bold text-ops-text">快速创建</h2>
        <div className="mt-4 space-y-3">
          <label className="block text-xs font-semibold text-ops-subtext">业务系统</label>
          <input className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={name} onChange={(event) => setName(event.target.value)} />
          <label className="block text-xs font-semibold text-ops-subtext">环境</label>
          <input className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={environment} onChange={(event) => setEnvironment(event.target.value)} />
          <button disabled={busy} onClick={() => void submit()} className="ops-primary-action w-full px-4 py-2 text-sm disabled:opacity-60">创建测试画像</button>
        </div>
      </div>
    </section>
  )
}

