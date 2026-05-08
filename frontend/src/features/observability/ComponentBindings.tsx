import { useState } from 'react'
import type { ObservabilityComponent, ObservabilitySystem } from './types'

export default function ComponentBindings({
  system,
  component,
  onBindAsset,
  onBindSession,
}: {
  system: ObservabilitySystem | null
  component: ObservabilityComponent | null
  onBindAsset: (componentId: string, assetId: string) => Promise<void>
  onBindSession: (componentId: string, sessionId: string) => Promise<void>
}) {
  const [assetId, setAssetId] = useState('asset-registry')
  const [sessionId, setSessionId] = useState('session-prometheus')
  if (!system || !component) {
    return <div className="ops-data-panel p-5 text-sm text-ops-subtext">选择节点后可绑定资产和会话。</div>
  }
  return (
    <div className="ops-data-panel p-5">
      <h3 className="text-base font-bold text-ops-text">{component.name}</h3>
      <div className="mt-2 space-y-1 text-xs text-ops-subtext">
        <div>类型：{component.component_type}</div>
        <div>族类：{component.workload_family}</div>
        <div>状态：{component.status || 'unknown'} / {component.confidence || 'unknown'}</div>
      </div>
      <div className="mt-5 space-y-3">
        <label className="block text-xs font-semibold text-ops-subtext">资产 ID</label>
        <input className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={assetId} onChange={(event) => setAssetId(event.target.value)} />
        <button className="ops-control w-full rounded-lg px-3 py-2 text-sm font-semibold" onClick={() => void onBindAsset(component.id, assetId)}>绑定资产</button>
        <label className="block text-xs font-semibold text-ops-subtext">会话 ID</label>
        <input className="ops-control w-full rounded-lg px-3 py-2 text-sm" value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
        <button className="ops-control w-full rounded-lg px-3 py-2 text-sm font-semibold" onClick={() => void onBindSession(component.id, sessionId)}>绑定会话</button>
      </div>
    </div>
  )
}

