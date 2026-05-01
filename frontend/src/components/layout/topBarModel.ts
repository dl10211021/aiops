import type { ViewId } from '@/types'

export const VIEW_LABELS: Record<ViewId, string> = {
  dashboard: '总览大屏',
  bigscreen: '总览大屏',
  chat: 'AI 会话',
  assets: '资产中心',
  cron: '自动化巡检',
  alerts: '告警事件',
  approvals: '审批中心',
  skills: '技能市场',
  knowledge: '知识库',
}

export const THEME_OPTIONS = [
  { id: 'deep-command', label: '深空指挥' },
  { id: 'obsidian-enterprise', label: '黑曜企业' },
  { id: 'titanium-industrial', label: '工业钛灰' },
  { id: 'night-blueprint', label: '夜航蓝图' },
  { id: 'cyber-amber', label: '赛博琥珀' },
  { id: 'arctic-console', label: '极地控制台' },
  { id: 'quantum-teal', label: '量子青绿' },
] as const

export type OpsTheme = typeof THEME_OPTIONS[number]['id']

export function readStoredTheme(): OpsTheme {
  const stored = localStorage.getItem('ops_ui_theme')
  return THEME_OPTIONS.some((theme) => theme.id === stored) ? stored as OpsTheme : 'deep-command'
}
