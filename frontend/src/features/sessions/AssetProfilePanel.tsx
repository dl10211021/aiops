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
    <div className="border-b border-ops-surface0 bg-ops-panel/95 px-4 py-2">
      <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35">
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
