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
    <div className="px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-ops-overlay">资产画像</div>
        </div>
        <button
          type="button"
          onClick={onGenerate}
          disabled={!session || busy}
          className="shrink-0 rounded-md border border-ops-accent/45 bg-ops-accent/10 px-3 py-2 text-sm font-semibold text-ops-accent hover:bg-ops-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? '生成中' : profile ? '重新生成' : '生成画像'}
        </button>
      </div>

      <button
        type="button"
        onClick={onToggle}
        disabled={!profile}
        className="mt-4 block w-full min-w-0 rounded-lg border border-ops-surface0 bg-ops-panel/35 px-4 py-4 text-left disabled:cursor-default"
      >
        <span className="block text-xl font-semibold leading-7 text-ops-text">{title}</span>
        <span className="mt-2 block text-sm leading-6 text-ops-subtext">{subtitle}</span>
      </button>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {profile ? (
          <>
            <span className={`rounded-full border px-2.5 py-1 text-xs ${profileRiskTone(profile.risk_level)}`}>
              {profileRiskLabel(profile.risk_level)}
            </span>
            <span className="rounded-full border border-ops-surface1 px-2.5 py-1 text-xs text-ops-subtext">
              置信度 {profile.confidence}%
            </span>
          </>
        ) : (
          <span className="rounded-full border border-ops-surface1 px-2.5 py-1 text-xs text-ops-subtext">
            等待生成
          </span>
        )}
        {profile && (
          <button
            type="button"
            onClick={onToggle}
            className="ml-auto rounded-md border border-ops-surface1 px-3 py-2 text-sm text-ops-subtext hover:text-ops-text"
          >
            {open ? '收起' : '展开'}
          </button>
        )}
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
    <div className="grid gap-4 border-t border-ops-surface0 px-4 py-4">
      <ProfileIdentitySection profile={profile} session={session} />
      <ProfileEvidenceSection items={profile.evidence.slice(0, 4)} />
      <ProfileFocusSection items={profile.focus_areas.slice(0, 4)} />
    </div>
  )
}
