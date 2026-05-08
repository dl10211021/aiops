import type { DiscoveryRun, ObservabilitySystem } from './types'

export default function ProfileDiscovery({
  system,
  run,
  onRun,
  onConfirm,
  onReject,
}: {
  system: ObservabilitySystem | null
  run: DiscoveryRun | null
  onRun: () => Promise<void>
  onConfirm: (itemId: string) => Promise<void>
  onReject: (itemId: string) => Promise<void>
}) {
  return (
    <section className="ops-data-panel p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-ops-text">画像发现</h2>
          <p className="mt-1 text-sm text-ops-subtext">{system ? `${system.name} / ${system.environment}` : '请选择业务系统后启动发现'}</p>
        </div>
        <button disabled={!system} className="ops-primary-action px-4 py-2 text-sm disabled:opacity-50" onClick={() => void onRun()}>启动 AI 发现</button>
      </div>
      <div className="mt-5 space-y-3">
        {(run?.review_items || []).map((item) => (
          <div key={item.id} className="rounded-lg border border-ops-surface0 bg-ops-surface0/35 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-semibold text-ops-text">{item.relationship_type}</div>
                <div className="mt-1 font-mono text-xs text-ops-overlay">{item.from_component_id} {'->'} {item.to_component_id}</div>
              </div>
              <div className="flex gap-2">
                <span className="rounded bg-ops-accent/10 px-2 py-1 text-xs text-ops-accent">{item.status}</span>
                <button className="ops-control rounded-lg px-3 py-1 text-xs" onClick={() => void onConfirm(item.id)}>确认</button>
                <button className="ops-control rounded-lg px-3 py-1 text-xs" onClick={() => void onReject(item.id)}>拒绝</button>
              </div>
            </div>
          </div>
        ))}
        {run && (run.review_items || []).length === 0 && <div className="py-12 text-center text-sm text-ops-subtext">暂无待确认关系</div>}
        {!run && <div className="py-12 text-center text-sm text-ops-subtext">发现结果会以 pending_review 关系展示，确认后才写入画像。</div>}
      </div>
    </section>
  )
}
