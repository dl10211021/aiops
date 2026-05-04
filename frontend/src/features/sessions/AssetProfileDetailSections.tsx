import type { AssetProfile, AssetProfileEvidence, AssetProfileFocusArea, Session } from '@/types'
import { assetProfileFacts } from './assetProfileDisplay'

export function ProfileIdentitySection({
  profile,
  session,
}: {
  profile: AssetProfile
  session: Session | null
}) {
  return (
    <div>
      <div className="mb-2 text-xs font-semibold text-ops-overlay">资产识别</div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {assetProfileFacts(profile, session).map((fact) => (
          <ProfileFact key={fact.label} label={fact.label} value={fact.value} />
        ))}
      </div>
      {profile.services.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {profile.services.slice(0, 8).map((service) => (
            <span key={service} className="rounded-full border border-ops-surface1 px-2.5 py-1 text-xs text-ops-subtext">
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
    <div>
      <div className="mb-2 text-xs font-semibold text-ops-overlay">关键证据</div>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={`${item.label}-${index}`} className="rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
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

export function ProfileFocusSection({ items }: { items: AssetProfileFocusArea[] }) {
  return (
    <div>
      <div className="mb-2 text-xs font-semibold text-ops-overlay">后续排查重点</div>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={`${item.title}-${index}`} className="rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <span className="rounded border border-ops-accent/35 px-1.5 py-0.5 text-[10px] text-ops-accent">{item.priority}</span>
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
    <div className="rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2.5">
      <div className="text-[11px] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold text-ops-text">{value}</div>
    </div>
  )
}
