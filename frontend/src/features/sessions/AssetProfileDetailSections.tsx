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
  const total = inbound.length + outbound.length + unknown.length
  return (
    <div className="rounded-2xl border border-ops-surface0/90 bg-ops-dark/24 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-accent">Connectivity</span>
        <span className="text-xs font-semibold text-ops-overlay">互联信息</span>
      </div>
      {items.length === 0 ? (
        <div className="space-y-3">
          <div className="relative overflow-hidden rounded-2xl border border-ops-accent/25 bg-[radial-gradient(circle_at_50%_10%,rgba(45,212,191,0.16),rgba(15,23,42,0.2)_40%,rgba(2,6,23,0.75)_100%)] p-3 shadow-[0_0_32px_rgba(45,212,191,0.08)]">
            <div className="pointer-events-none absolute inset-0 opacity-35">
              <div className="absolute left-0 right-0 top-1/2 h-px bg-gradient-to-r from-transparent via-ops-accent/60 to-transparent" />
              <div className="absolute bottom-0 left-1/2 top-0 w-px bg-gradient-to-b from-transparent via-ops-accent/25 to-transparent" />
            </div>
            <div className="relative flex items-center justify-between gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-ops-overlay">
              <span>Inbound</span>
              <span>等待画像提取</span>
              <span>Outbound</span>
            </div>
            <div className="relative mt-3 grid min-h-[220px] grid-cols-[1fr_96px_1fr] items-center gap-2">
              <RelationNodeColumn title="哪些业务连接它" empty="等待入站证据" items={[]} side="left" />
              <AssetHub inboundCount={0} outboundCount={0} />
              <RelationNodeColumn title="它去连接别人" empty="等待出站证据" items={[]} side="right" />
            </div>
          </div>
          <div className="rounded-xl border border-dashed border-ops-surface1/70 bg-ops-panel/30 px-3 py-3 text-xs leading-5 text-ops-subtext">
            暂无可确认互联关系。重新生成画像后，AI 会从监听端口、连接状态、访问日志、进程、数据库连接和会话证据里提取。
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="relative overflow-hidden rounded-2xl border border-ops-accent/25 bg-[radial-gradient(circle_at_50%_10%,rgba(45,212,191,0.18),rgba(15,23,42,0.2)_40%,rgba(2,6,23,0.75)_100%)] p-3 shadow-[0_0_32px_rgba(45,212,191,0.08)]">
            <div className="pointer-events-none absolute inset-0 opacity-40">
              <div className="absolute left-0 right-0 top-1/2 h-px bg-gradient-to-r from-transparent via-ops-accent/60 to-transparent" />
              <div className="absolute bottom-0 left-1/2 top-0 w-px bg-gradient-to-b from-transparent via-ops-accent/25 to-transparent" />
            </div>
            <div className="relative flex items-center justify-between gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-ops-overlay">
              <span>Inbound</span>
              <span>{total} 条关系</span>
              <span>Outbound</span>
            </div>
            <div className="relative mt-3 grid min-h-[240px] grid-cols-[1fr_96px_1fr] items-center gap-2">
              <RelationNodeColumn
                title="哪些业务连接它"
                empty="暂无入站"
                items={inbound}
                side="left"
              />
              <AssetHub inboundCount={inbound.length} outboundCount={outbound.length} />
              <RelationNodeColumn
                title="它去连接别人"
                empty="暂无出站"
                items={outbound}
                side="right"
              />
            </div>
            {unknown.length > 0 && (
              <div className="relative mt-3 rounded-xl border border-amber-300/20 bg-amber-300/5 px-3 py-2">
                <div className="text-[11px] font-black text-amber-200">方向待确认</div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {unknown.slice(0, 4).map((item, index) => (
                    <span key={`${item.peer}-${index}`} className="rounded-full border border-amber-200/20 px-2 py-0.5 text-[10px] text-amber-100/80">
                      {item.peer}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
          <RelationEvidenceStrip items={items} />
        </div>
      )}
    </div>
  )
}

function RelationNodeColumn({
  title,
  empty,
  items,
  side,
}: {
  title: string
  empty: string
  items: AssetProfileRelation[]
  side: 'left' | 'right'
}) {
  const visibleItems = items.slice(0, 4)
  const alignClass = side === 'left' ? 'items-end text-right' : 'items-start text-left'
  const flowClass = side === 'left' ? 'right-[-18px] bg-gradient-to-r' : 'left-[-18px] bg-gradient-to-l'
  return (
    <section className={`flex min-w-0 flex-col gap-2 ${alignClass}`}>
      <div className="text-[11px] font-black text-ops-text">{title}</div>
      {visibleItems.length === 0 ? (
        <div className="w-full rounded-xl border border-dashed border-ops-surface1/55 bg-ops-panel/24 px-3 py-3 text-[11px] text-ops-overlay">{empty}</div>
      ) : (
        visibleItems.map((item, index) => (
          <RelationNode key={`${side}-${item.peer}-${index}`} item={item} side={side} flowClass={flowClass} />
        ))
      )}
      {items.length > visibleItems.length && (
        <div className="rounded-full border border-ops-surface1/60 bg-ops-dark/45 px-2 py-0.5 text-[10px] text-ops-overlay">
          还有 {items.length - visibleItems.length} 条
        </div>
      )}
    </section>
  )
}

function RelationNode({
  item,
  side,
  flowClass,
}: {
  item: AssetProfileRelation
  side: 'left' | 'right'
  flowClass: string
}) {
  const directionText = side === 'left' ? '流入资产' : '资产流出'
  return (
    <div className="relative w-full rounded-2xl border border-ops-surface0/90 bg-ops-panel/62 px-3 py-2.5 shadow-[0_10px_26px_rgba(2,6,23,0.24)]">
      <div className={`absolute top-1/2 h-px w-7 -translate-y-1/2 from-transparent via-ops-accent/80 to-ops-accent/15 ${flowClass}`} />
      <div className={`absolute top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-ops-accent shadow-[0_0_16px_rgba(45,212,191,0.85)] ${side === 'left' ? 'right-[-21px]' : 'left-[-21px]'}`} />
      <div className="flex items-center justify-between gap-2">
        <span className="min-w-0 truncate text-sm font-black text-ops-text">{item.peer}</span>
        {typeof item.confidence === 'number' && (
          <span className="shrink-0 rounded-full border border-ops-accent/25 bg-ops-accent/8 px-2 py-0.5 text-[10px] font-semibold text-ops-accent">
            {item.confidence}%
          </span>
        )}
      </div>
      <div className="mt-1 flex flex-wrap gap-1.5 text-[10px] text-ops-overlay">
        <span className="rounded-full border border-ops-surface1/55 px-2 py-0.5">{directionText}</span>
        {item.peer_role && <span className="rounded-full border border-ops-surface1/55 px-2 py-0.5">{item.peer_role}</span>}
        {item.protocol && <span className="rounded-full border border-ops-accent/25 bg-ops-accent/8 px-2 py-0.5 text-ops-accent">{item.protocol}</span>}
      </div>
      {item.endpoint && <div className="mt-1 truncate font-mono text-[11px] text-ops-subtext">{item.endpoint}</div>}
    </div>
  )
}

function AssetHub({ inboundCount, outboundCount }: { inboundCount: number; outboundCount: number }) {
  return (
    <div className="relative flex h-full min-w-0 items-center justify-center">
      <div className="absolute h-24 w-24 animate-pulse rounded-full border border-ops-accent/20 bg-ops-accent/5" />
      <div className="relative flex h-20 w-20 flex-col items-center justify-center rounded-full border border-ops-accent/55 bg-ops-dark/90 text-center shadow-[0_0_34px_rgba(45,212,191,0.22)]">
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-accent">Asset</span>
        <span className="mt-1 text-lg font-black text-ops-text">{inboundCount + outboundCount}</span>
        <span className="text-[10px] text-ops-overlay">连接</span>
      </div>
    </div>
  )
}

function RelationEvidenceStrip({ items }: { items: AssetProfileRelation[] }) {
  const evidenceItems = items.filter((item) => item.evidence).slice(0, 3)
  if (evidenceItems.length === 0) {
    return (
      <div className="rounded-xl border border-ops-surface0 bg-ops-panel/28 px-3 py-2 text-[11px] leading-5 text-ops-overlay">
        当前互联图暂无证据摘要，建议重新生成画像时补充连接状态、访问日志、数据库连接或端口监听证据。
      </div>
    )
  }
  return (
    <div className="grid gap-2">
      {evidenceItems.map((item, index) => (
        <div key={`${item.peer}-evidence-${index}`} className="rounded-xl border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-black text-ops-text">{item.peer}</span>
            <span className="shrink-0 rounded-full border border-ops-surface1/55 px-2 py-0.5 text-[10px] text-ops-overlay">{relationDirectionLabel(item.direction)}</span>
          </div>
          <div className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">{item.evidence}</div>
        </div>
      ))}
    </div>
  )
}

function relationDirectionLabel(direction: string) {
  if (direction === 'inbound') return '入站'
  if (direction === 'outbound') return '出站'
  if (direction === 'bidirectional') return '双向'
  return '待确认'
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
