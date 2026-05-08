import type { ViewId } from '@/types'

export const VIEW_LABELS: Record<ViewId, string> = {
  dashboard: '总览',
  bigscreen: '总览',
  chat: 'AI 会话',
  observability: '可观测性',
  assets: '资产中心',
  canvas: '实时画板',
  cron: '巡检任务',
  alerts: '告警',
  approvals: '审批',
  skills: 'Skills',
  knowledge: '知识库',
  config: '系统配置',
}

export const THEME_OPTIONS = [
  { id: 'deep-command', label: '深空指挥' },
  { id: 'titanium', label: '企业浅色' },
  { id: 'arctic', label: '夜间高对比' },
] as const

export type OpsTheme = typeof THEME_OPTIONS[number]['id']

export function readStoredTheme(): OpsTheme {
  const stored = localStorage.getItem('ops_ui_theme')
  return THEME_OPTIONS.some((theme) => theme.id === stored) ? stored as OpsTheme : 'deep-command'
}
