import type { AssetProfile, Session } from '@/types'
import { assetTypeLabel, protocolLabel } from '@/utils/assetDisplay'

export function assetProfileTitle(profile: AssetProfile | null, session: Session | null) {
  return profile?.role_label || (session ? '尚未生成资产画像' : '未选择会话')
}

export function assetProfileSubtitle(profile: AssetProfile | null) {
  return profile?.purpose || '生成后，AI 会把当前资产的角色、用途、证据和后续排查重点沉淀到独立画像记忆。'
}

export function profileRiskLabel(risk?: string) {
  if (risk === 'normal') return '运行正常'
  if (risk === 'high') return '高风险'
  return '需要关注'
}

export function profileRiskTone(risk?: string) {
  if (risk === 'normal') return 'border-ops-success/35 bg-ops-success/10 text-ops-success'
  if (risk === 'high') return 'border-ops-alert/45 bg-ops-alert/10 text-ops-alert'
  return 'border-yellow-300/35 bg-yellow-300/10 text-yellow-100'
}

export function assetProfileFacts(profile: AssetProfile, session: Session | null) {
  return [
    { label: '目标', value: profile.remark || profile.host || '-' },
    { label: '类型', value: assetTypeLabel(profile.asset_type || session?.asset_type || '') },
    { label: '协议', value: protocolLabel(profile.protocol || session?.protocol || '') },
    { label: '更新', value: profile.updated_at || '-' },
  ]
}
