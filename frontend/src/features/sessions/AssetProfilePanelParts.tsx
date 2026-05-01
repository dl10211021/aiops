import type { AssetProfile, Session } from '@/types'
import {
  profileRiskLabel,
  profileRiskTone,
} from './assetProfileDisplay'
import {
  ProfileEvidenceSection,
  ProfileFocusSection,
  ProfileIdentitySection,
} from './AssetProfileDetailSections'

export function ProfileSummaryButton({
  busy,
  open,
  profile,
  session,
  subtitle,
  title,
  onGenerate,
  onToggle,
}: {
  busy: boolean
  open: boolean
  profile: AssetProfile | null
  session: Session | null
  subtitle: string
  title: string
  onGenerate: () => void
  onToggle: () => void
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
      <button
        type="button"
        onClick={onToggle}
        disabled={!profile}
        className="flex min-w-0 flex-1 items-center gap-3 text-left disabled:cursor-default"
      >
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-ops-accent/35 bg-ops-accent/10 text-sm text-ops-accent">
          画像
        </span>
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-ops-text">{title}</span>
            {profile && (
              <>
                <span className={`rounded-full border px-2 py-0.5 text-[11px] ${profileRiskTone(profile.risk_level)}`}>
                  {profileRiskLabel(profile.risk_level)}
                </span>
                <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[11px] text-ops-subtext">
                  置信度 {profile.confidence}%
                </span>
              </>
            )}
          </span>
          <span className="mt-0.5 line-clamp-1 text-xs text-ops-subtext">{subtitle}</span>
        </span>
      </button>
      <div className="flex shrink-0 items-center gap-2">
        {profile && (
          <button
            type="button"
            onClick={onToggle}
            className="rounded-md border border-ops-surface1 px-2.5 py-1.5 text-xs text-ops-subtext hover:text-ops-text"
          >
            {open ? '收起' : '展开'}
          </button>
        )}
        <button
          type="button"
          onClick={onGenerate}
          disabled={!session || busy}
          className="rounded-md border border-ops-accent/45 bg-ops-accent/10 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? '生成中' : profile ? '重新生成' : '生成画像'}
        </button>
      </div>
    </div>
  )
}

export function ProfileDetails({
  profile,
  session,
}: {
  profile: AssetProfile
  session: Session | null
}) {
  return (
    <div className="grid gap-3 border-t border-ops-surface0 px-3 py-3 lg:grid-cols-[1.1fr_1fr_1fr]">
      <ProfileIdentitySection profile={profile} session={session} />
      <ProfileEvidenceSection items={profile.evidence.slice(0, 4)} />
      <ProfileFocusSection items={profile.focus_areas.slice(0, 4)} />
    </div>
  )
}
