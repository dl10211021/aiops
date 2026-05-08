import { useState } from 'react'
import type { ObservableSource, ObservabilitySystem } from './types'

export default function ObservableSources({
  sources,
  systems,
  selectedSystemId,
  onPromoteSession,
  onCheck,
}: {
  sources: ObservableSource[]
  systems: ObservabilitySystem[]
  selectedSystemId: string | null
  onPromoteSession: (payload: Record<string, unknown>) => Promise<void>
  onCheck: (sourceId: string) => Promise<void>
}) {
  const [sessionId, setSessionId] = useState('prometheus-session')
  const [systemId, setSystemId] = useState(selectedSystemId || '')
  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="ops-data-panel overflow-hidden">
        <div className="ops-data-toolbar m-3 mb-0 px-4 py-3">
          <h2 className="text-base font-bold text-ops-text">观测源</h2>
          <p className="mt-1 text-xs text-ops-subtext">会话、监控、日志、网络和安全数据都以证据源登记。</p>
        </div>
        <div className="overflow-x-auto p-3">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-xs text-ops-overlay">
              <tr>{['名称', '类型', '来源', '能力', '状态', '最近检查', '操作'].map((item) => <th key={item} className="px-3 py-2">{item}</th>)}</tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id} className="border-t border-ops-surface0/70">
                  <td className="px-3 py-3 font-semibold text-ops-text">{source.name}</td>
                  <td className="px-3 py-3 text-ops-subtext">{source.source_type}</td>
                  <td className="px-3 py-3 text-ops-subtext">{source.source_origin || '-'}</td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(source.capabilities || []).slice(0, 5).map((capability) => <span key={capability} className="rounded bg-ops-surface0 px-2 py-0.5 text-[11px] text-ops-subtext">{capability}</span>)}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-ops-subtext">{source.status || 'unknown'}</td>
                  <td className="px-3 py-3 text-xs text-ops-overlay">{source.last_checked_at || '-'}</td>
                  <td className="px-3 py-3"><button className="ops-control rounded-lg px-2.5 py-1 text-xs" onClick={() => void onCheck(source.id)}>检查</button></td>
                </tr>
              ))}
              {sources.length === 0 && <tr><td colSpan={7} className="px-3 py-12 text-center text-sm text-ops-subtext">暂无观测源</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <div className="ops-data-panel p-5">
        <h3 className="text-base font-bold text-ops-text">从会话登记观测源</h3>
        <div className="mt-4 space-y-3">
          <label className="block text-xs font-semibold text-ops-subtext">Prometheus 会话 ID</label>
          <input className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
          <label className="block text-xs font-semibold text-ops-subtext">绑定业务系统</label>
          <select className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={systemId} onChange={(event) => setSystemId(event.target.value)}>
            <option value="">暂不绑定</option>
            {systems.map((system) => <option key={system.id} value={system.id}>{system.name} / {system.environment}</option>)}
          </select>
          <button
            className="ops-primary-action w-full px-4 py-2 text-sm"
            onClick={() => void onPromoteSession({ session_id: sessionId, source_type: 'prometheus', name: 'Prometheus 会话', system_id: systemId })}
          >
            登记 Prometheus 源
          </button>
        </div>
      </div>
    </section>
  )
}

