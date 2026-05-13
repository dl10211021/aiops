import type { SkillInfo } from '@/types'

const TARGET_SCOPE_LABELS: Record<string, string> = {
  asset: '单资产',
  tag: '资产标签',
  category: '资产分类',
  protocol: '接入协议',
  asset_type: '资产类型',
  all: '全部资产',
}

const AGENT_PROFILE_LABELS: Record<string, string> = {
  default: '标准执行',
  readonly: '只读巡检',
  readwrite: '读写处置',
  master: '编排调度',
}

const CHANNEL_LABELS: Record<string, string> = {
  auto: '自动通知',
  webhook: 'Webhook',
  email: '邮件',
  wechat: '企业微信',
  dingtalk: '钉钉',
  none: '不通知',
}

const INSPECTION_CYCLE_LABELS: Record<string, string> = {
  daily: '日巡检',
  weekly: '周巡检',
  monthly: '月巡检',
  quarterly: '季度巡检',
  yearly: '年度巡检',
  custom: '自定义',
}

const INSPECTION_DEPTH_LABELS: Record<string, string> = {
  quick: '快速',
  standard: '标准',
  deep: '深度',
}

export function cronScheduleLabel(expr?: string) {
  const value = String(expr || '').trim()
  const labels: Record<string, string> = {
    '0 9 * * *': '每天 09:00',
    '0 * * * *': '每小时',
    '*/30 * * * *': '每 30 分钟',
    '0 9 * * 1': '每周一 09:00',
  }
  return labels[value] || value || '-'
}

export function inspectionCycleLabel(cycle?: string) {
  return INSPECTION_CYCLE_LABELS[String(cycle || 'daily')] || cycle || '日巡检'
}

export function inspectionDepthLabel(depth?: string) {
  return INSPECTION_DEPTH_LABELS[String(depth || 'standard')] || depth || '标准'
}

export function targetScopeLabel(scope?: string, value?: string | null) {
  const label = TARGET_SCOPE_LABELS[String(scope || 'asset')] || scope || '单资产'
  return value ? `${label}：${value}` : label
}

export function agentProfileLabel(profile?: string) {
  return AGENT_PROFILE_LABELS[String(profile || 'default')] || profile || '标准执行'
}

export function channelLabel(channel?: string) {
  return CHANNEL_LABELS[String(channel || 'auto')] || channel || '自动通知'
}

export function skillSummary(skillIds: string[] | undefined, registry: SkillInfo[]) {
  if (!skillIds?.length) return '未挂载'
  const names = skillIds.map((id) => registry.find((skill) => skill.id === id)?.name || id)
  return names.length > 2 ? `${names.slice(0, 2).join('、')} 等 ${names.length} 个` : names.join('、')
}
