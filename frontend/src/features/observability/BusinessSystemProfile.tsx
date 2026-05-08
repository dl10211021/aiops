import { useState } from 'react'
import ComponentBindings from './ComponentBindings'
import LayeredTopology from './LayeredTopology'
import type { ObservabilityComponent, ObservabilitySystem, ObservabilityTopology } from './types'

export default function BusinessSystemProfile({
  system,
  topology,
  onAddComponent,
  onBindAsset,
  onBindSession,
}: {
  system: ObservabilitySystem | null
  topology: ObservabilityTopology | null
  onAddComponent: (payload: Record<string, unknown>) => Promise<void>
  onBindAsset: (componentId: string, assetId: string) => Promise<void>
  onBindSession: (componentId: string, sessionId: string) => Promise<void>
}) {
  const [selected, setSelected] = useState<ObservabilityComponent | null>(null)
  const [name, setName] = useState('未知数据库')
  const [componentType, setComponentType] = useState('unknown')
  if (!system) return <div className="ops-data-panel p-6 text-sm text-ops-subtext">请选择业务系统。</div>
  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <div className="ops-data-panel mb-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-black text-ops-text">{system.name}</h2>
              <p className="mt-1 text-sm text-ops-subtext">{system.environment} · 完整度 {system.profile_completeness || 0}% · 未知节点 {system.unknown_count || 0}</p>
            </div>
            <div className="flex gap-2">
              <input className="ops-control w-36 rounded-lg px-3 py-2 text-sm" value={name} onChange={(event) => setName(event.target.value)} />
              <select className="ops-control rounded-lg px-3 py-2 text-sm" value={componentType} onChange={(event) => setComponentType(event.target.value)}>
                <option value="unknown">unknown</option>
                <option value="database_instance">database_instance</option>
                <option value="network_switch">network_switch</option>
                <option value="os_host">os_host</option>
                <option value="application_service">application_service</option>
              </select>
              <button className="ops-control rounded-lg px-3 py-2 text-sm font-semibold" onClick={() => void onAddComponent({ name, component_type: componentType, workload_family: componentType === 'unknown' ? 'unknown' : 'application', confidence: componentType === 'unknown' ? 'unknown' : 'confirmed' })}>添加节点</button>
            </div>
          </div>
        </div>
        <LayeredTopology topology={topology} selectedComponentId={selected?.id || null} onSelect={setSelected} />
      </div>
      <ComponentBindings system={system} component={selected} onBindAsset={onBindAsset} onBindSession={onBindSession} />
    </section>
  )
}

