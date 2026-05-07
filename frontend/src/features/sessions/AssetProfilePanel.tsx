import type { AssetProfile, Session } from '@/types'
import {
  assetProfileSubtitle,
  assetProfileTitle,
} from './assetProfileDisplay'
import {
  ProfileDetails,
  ProfileSummaryButton,
} from './AssetProfilePanelParts'

interface AssetProfilePanelProps {
  session: Session | null
  profile: AssetProfile | null
  open: boolean
  busy: boolean
  onToggle: () => void
  onGenerate: () => void
}

export default function AssetProfilePanel({
  session,
  profile,
  open,
  busy,
  onToggle,
  onGenerate,
}: AssetProfilePanelProps) {
  const title = assetProfileTitle(profile, session)
  const subtitle = assetProfileSubtitle(profile)
  return (
    <div className="border-b border-ops-surface0/80 bg-transparent px-3 py-3">
      <div className="overflow-hidden rounded-2xl border border-ops-accent/20 bg-[linear-gradient(135deg,rgba(40,208,168,0.11),rgba(12,31,52,0.86))] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        <ProfileSummaryButton
          busy={busy}
          open={open}
          profile={profile}
          session={session}
          subtitle={subtitle}
          title={title}
          onGenerate={onGenerate}
          onToggle={onToggle}
        />
        {open && profile && <ProfileDetails profile={profile} session={session} />}
      </div>
    </div>
  )
}
