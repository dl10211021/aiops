import type { AssetProfile, Session } from '@/types'
import {
  profileRiskLabel,
  profileRiskTone,
} from './assetProfileDisplay'
import {
  ProfileEvidenceSection,
  ProfileFocusSection,
  ProfileIdentitySection,
  ProfileRelationsSection,
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
          <div className="text-[10px] font-black uppercase tracking-[0.22em] text-ops-accent">Asset Profile</div>
          <div className="mt-1 text-sm font-black text-ops-text">资产情报卡</div>
        </div>
        <button
          type="button"
          onClick={onGenerate}
          disabled={!session || busy}
          className="shrink-0 rounded-xl border border-ops-accent/45 bg-ops-accent/12 px-3 py-2 text-sm font-black text-ops-accent shadow-[0_10px_26px_rgba(40,208,168,0.08)] hover:bg-ops-accent/18 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? '生成中' : profile ? '重新生成' : '生成画像'}
        </button>
      </div>

      <button
        type="button"
        onClick={onToggle}
        disabled={!profile}
        className="mt-4 block w-full min-w-0 overflow-hidden rounded-[18px] border border-ops-accent/22 bg-[radial-gradient(circle_at_18%_0%,rgba(40,208,168,0.16),transparent_13rem),linear-gradient(135deg,rgba(16,37,58,0.9),rgba(7,17,31,0.78))] px-4 py-4 text-left shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] disabled:cursor-default"
      >
        <span className="block text-[11px] font-black uppercase tracking-[0.18em] text-ops-overlay">
          {session ? `${session.protocol || session.asset_type || 'session'} · ${session.host || 'unknown'}` : 'No session'}
        </span>
        <span className="mt-2 block text-xl font-black leading-7 text-ops-text">{title}</span>
        <span className="mt-2 block text-sm leading-6 text-ops-subtext">{subtitle}</span>
        <span className="mt-4 flex flex-wrap items-center gap-2">
          {profile ? (
            <>
              <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${profileRiskTone(profile.risk_level)}`}>
                {profileRiskLabel(profile.risk_level)}
              </span>
              <span className="rounded-full border border-ops-surface1/70 bg-ops-dark/35 px-2.5 py-1 text-xs font-semibold text-ops-subtext">
                置信度 {profile.confidence}%
              </span>
              <span className="ml-auto rounded-full border border-ops-surface1/70 bg-ops-panel/45 px-2.5 py-1 text-xs font-semibold text-ops-overlay">
                {open ? '点击收起' : '点击展开'}
              </span>
            </>
          ) : (
            <span className="rounded-full border border-ops-surface1/70 bg-ops-dark/35 px-2.5 py-1 text-xs font-semibold text-ops-subtext">
              等待生成
            </span>
          )}
        </span>
      </button>

      {profile && (
        <div className="mt-3">
          <ProfileRelationsSection items={profile.relations || []} strategies={profile.relation_strategies || []} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {profile && (
          <button
            type="button"
            onClick={onToggle}
            className="ml-auto rounded-xl border border-ops-surface1/75 bg-ops-dark/35 px-3 py-2 text-sm font-semibold text-ops-subtext hover:border-ops-accent/40 hover:text-ops-text"
          >
            {open ? '收起详情' : '展开详情'}
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
    <div className="grid gap-3 border-t border-ops-surface0/80 bg-ops-dark/18 px-4 py-4">
      <ProfileIdentitySection profile={profile} session={session} />
      <ProfileEvidenceSection items={profile.evidence.slice(0, 4)} />
      <ProfileFocusSection items={profile.focus_areas.slice(0, 4)} />
    </div>
  )
}
