export type CronForm = {
  id?: string
  cron_expr: string
  message: string
  host: string
  username: string
  agent_profile: string
  password: string
  asset_id: string
  target_scope: string
  scope_value: string
  template_id: string
  notification_channel: string
  retry_count: string
  active_skills: string[]
}

export type CronPreset = {
  label: string
  expr: string
}

export const emptyCronForm: CronForm = {
  cron_expr: '0 9 * * *',
  message: '执行一次标准只读巡检，输出健康状态、异常项、风险等级和建议。',
  host: '',
  username: 'root',
  agent_profile: 'default',
  password: '',
  asset_id: '',
  target_scope: 'asset',
  scope_value: '',
  template_id: '',
  notification_channel: 'auto',
  retry_count: '0',
  active_skills: [],
}

export const cronPresets: CronPreset[] = [
  { label: '每天 09:00', expr: '0 9 * * *' },
  { label: '每小时', expr: '0 * * * *' },
  { label: '每30分钟', expr: '*/30 * * * *' },
  { label: '每周一 09:00', expr: '0 9 * * 1' },
]
