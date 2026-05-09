import type { ObservabilityComponent, ObservabilityTopology } from './types'

export default function LayeredTopology({
  topology,
  selectedComponentId,
  onSelect,
}: {
  topology: ObservabilityTopology | null
  selectedComponentId: string | null
  onSelect: (component: ObservabilityComponent) => void
}) {
  if (!topology) {
    return <div className="ops-data-panel p-6 text-sm text-ops-subtext">请选择业务系统查看分层拓扑。</div>
  }
  return (
    <div className="space-y-3">
      {topology.layers.map((layer) => (
        <div key={layer.id} className="ops-data-panel p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-bold text-ops-text">{layer.label}</h3>
            <span className="font-mono text-xs text-ops-overlay">{layer.nodes.length}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {layer.nodes.map((node) => (
              <button
                key={node.id}
                onClick={() => onSelect(node)}
                className={`rounded-lg border px-3 py-2 text-left text-xs transition ${
                  selectedComponentId === node.id
                    ? 'border-ops-accent bg-ops-accent/15 text-ops-accent'
                    : 'border-ops-surface0 bg-ops-surface0/35 text-ops-subtext hover:border-ops-surface1 hover:text-ops-text'
                }`}
              >
                <div className="font-semibold">{node.name}</div>
                <div className="mt-1 text-[11px] text-ops-overlay">{node.component_type} · {node.confidence || 'unknown'}</div>
                <div className="mt-1 text-[11px]">资产 {node.bound_asset_count || 0} / 会话 {node.bound_session_count || 0} / 源 {node.bound_source_count || 0}</div>
              </button>
            ))}
            {layer.nodes.length === 0 && <span className="text-xs text-ops-overlay">暂无节点</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
