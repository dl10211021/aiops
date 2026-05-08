import { useState } from 'react'
import InvestigationDetail from './InvestigationDetail'
import type { Investigation, ObservabilitySystem } from './types'

export default function InvestigationCenter({
  systems,
  investigations,
  selected,
  onSelect,
  onCreate,
  onPlan,
  onDispatch,
}: {
  systems: ObservabilitySystem[]
  investigations: Investigation[]
  selected: Investigation | null
  onSelect: (id: string) => void
  onCreate: (payload: Record<string, unknown>) => Promise<void>
  onPlan: (id: string) => Promise<void>
  onDispatch: (id: string) => Promise<void>
}) {
  const [systemId, setSystemId] = useState('')
  const [symptom, setSymptom] = useState('系统慢')
  return (
    <section className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
      <div className="space-y-4">
        <div className="ops-data-panel p-5">
          <h2 className="text-base font-bold text-ops-text">发起排查</h2>
          <div className="mt-4 space-y-3">
            <select className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={systemId} onChange={(event) => setSystemId(event.target.value)}>
              <option value="">选择业务系统</option>
              {systems.map((system) => <option key={system.id} value={system.id}>{system.name} / {system.environment}</option>)}
            </select>
            <input className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={symptom} onChange={(event) => setSymptom(event.target.value)} />
            <button className="ops-primary-action w-full px-4 py-2 text-sm" onClick={() => void onCreate({ system_id: systemId, title: symptom, symptom, severity: 'warning' })}>创建排查事件</button>
          </div>
        </div>
        <div className="ops-data-panel p-3">
          {investigations.map((item) => (
            <button key={item.id} className={`mb-2 w-full rounded-lg border px-3 py-3 text-left ${selected?.id === item.id ? 'border-ops-accent bg-ops-accent/10' : 'border-ops-surface0 bg-ops-surface0/35'}`} onClick={() => onSelect(item.id)}>
              <div className="font-semibold text-ops-text">{item.title}</div>
              <div className="mt-1 text-xs text-ops-overlay">{item.status} · Agent {item.task_count || 0} · 证据 {item.evidence_count || 0}</div>
            </button>
          ))}
          {investigations.length === 0 && <div className="py-10 text-center text-sm text-ops-subtext">暂无排查事件</div>}
        </div>
      </div>
      <InvestigationDetail investigation={selected} onPlan={onPlan} onDispatch={onDispatch} />
    </section>
  )
}

