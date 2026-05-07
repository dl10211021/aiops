import type { AssetProfile, AssetProfileEvidence, AssetProfileFocusArea, AssetProfileRelation, Session } from '@/types'
import { assetProfileFacts } from './assetProfileDisplay'

export function ProfileIdentitySection({
  profile,
  session,
}: {
  profile: AssetProfile
  session: Session | null
}) {
  return (
    <div className="rounded-2xl border border-ops-surface0/90 bg-ops-dark/24 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-accent">Identity</span>
        <span className="text-xs font-semibold text-ops-overlay">资产识别</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {assetProfileFacts(profile, session).map((fact) => (
          <ProfileFact key={fact.label} label={fact.label} value={fact.value} />
        ))}
      </div>
      {profile.services.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {profile.services.slice(0, 8).map((service) => (
            <span key={service} className="rounded-full border border-ops-accent/24 bg-ops-accent/8 px-2.5 py-1 text-xs font-semibold text-ops-subtext">
              {service}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function ProfileEvidenceSection({ items }: { items: AssetProfileEvidence[] }) {
  return (
    <div className="rounded-2xl border border-ops-surface0/90 bg-ops-dark/24 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-accent">Evidence</span>
        <span className="text-xs font-semibold text-ops-overlay">关键证据</span>
      </div>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={`${item.label}-${index}`} className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-ops-text">{item.label}</span>
              {item.source && <span className="text-[10px] text-ops-overlay">{item.source}</span>}
            </div>
            <div className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ProfileRelationsSection({ items }: { items: AssetProfileRelation[] }) {
  const inbound = items.filter((item) => item.direction === 'inbound' || item.direction === 'bidirectional')
  const outbound = items.filter((item) => item.direction === 'outbound' || item.direction === 'bidirectional')
  const unknown = items.filter((item) => !['inbound', 'outbound', 'bidirectional'].includes(item.direction))
  return (
    <div className="rounded-2xl border border-ops-surface0/90 bg-ops-dark/24 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-accent">Connectivity</span>
        <span className="text-xs font-semibold text-ops-overlay">互联信息</span>
      </div>
      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ops-surface1/70 bg-ops-panel/30 px-3 py-3 text-xs leading-5 text-ops-subtext">
          暂无可确认互联关系。重新生成画像后，AI 会从监听端口、连接状态、访问日志、进程、数据库连接和会话证据里提取。
        </div>
      ) : (
        <div className="space-y-3">
          <RelationGroup title="哪些业务连接它" empty="暂无明确入站关系" items={inbound} />
          <RelationGroup title="它去连接别人" empty="暂无明确出站关系" items={outbound} />
          {unknown.length > 0 && <RelationGroup title="方向待确认" empty="暂无" items={unknown} />}
        </div>
      )}
    </div>
  )
}

function RelationGroup({ title, empty, items }: { title: string; empty: string; items: AssetProfileRelation[] }) {
  return (
    <section>
      <div className="mb-1.5 text-[11px] font-black text-ops-text">{title}</div>
      {items.length === 0 ? (
        <div className="rounded-xl border border-ops-surface0 bg-ops-panel/28 px-3 py-2 text-[11px] text-ops-overlay">{empty}</div>
      ) : (
        <div className="space-y-1.5">
          {items.slice(0, 6).map((item, index) => (
            <div key={`${item.direction}-${item.peer}-${index}`} className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold text-ops-text">{item.peer}</span>
                {typeof item.confidence === 'number' && (
                  <span className="shrink-0 rounded-full border border-ops-surface1/60 bg-ops-dark/35 px-2 py-0.5 text-[10px] text-ops-overlay">
                    {item.confidence}%
                  </span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5 text-[10px] text-ops-overlay">
                {item.peer_role && <span className="rounded-full border border-ops-surface1/55 px-2 py-0.5">{item.peer_role}</span>}
                {item.endpoint && <span className="rounded-full border border-ops-surface1/55 px-2 py-0.5">{item.endpoint}</span>}
                {item.protocol && <span className="rounded-full border border-ops-accent/25 bg-ops-accent/8 px-2 py-0.5 text-ops-accent">{item.protocol}</span>}
              </div>
              {item.evidence && <div className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">{item.evidence}</div>}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export function ProfileFocusSection({ items }: { items: AssetProfileFocusArea[] }) {
  return (
    <div className="rounded-2xl border border-ops-surface0/90 bg-ops-dark/24 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-accent">Next Focus</span>
        <span className="text-xs font-semibold text-ops-overlay">后续排查重点</span>
      </div>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={`${item.title}-${index}`} className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <span className="rounded-lg border border-ops-accent/35 bg-ops-accent/8 px-1.5 py-0.5 text-[10px] font-black text-ops-accent">{item.priority}</span>
              <span className="text-sm font-semibold text-ops-text">{item.title}</span>
            </div>
            <div className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">{item.reason}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ProfileFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
      <div className="text-[11px] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold text-ops-text">{value}</div>
    </div>
  )
}
