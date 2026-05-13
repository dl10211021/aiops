export type CronForm = {
  id?: string
  cron_expr: string
  message: string
  inspection_cycle: string
  inspection_depth: string
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
  cycle: string
}

export type InspectionCycleOption = {
  value: string
  label: string
  cronExpr: string
  message: string
  focus: string
}

export type InspectionDepthOption = {
  value: string
  label: string
  description: string
}

export const inspectionCycleOptions: InspectionCycleOption[] = [
  {
    value: 'daily',
    label: '日巡检',
    cronExpr: '0 9 * * *',
    message: '执行日常健康巡检，输出当前健康状态、异常项、风险等级和建议。',
    focus: '当前运行状态、CPU/内存/磁盘、核心服务、最近错误日志、立即风险。',
  },
  {
    value: 'weekly',
    label: '周巡检',
    cronExpr: '0 9 * * 1',
    message: '执行周度趋势巡检，分析最近 7 天容量、错误、备份和任务执行情况。',
    focus: '7 天容量趋势、错误趋势、备份与任务执行、潜在隐患。',
  },
  {
    value: 'monthly',
    label: '月巡检',
    cronExpr: '0 9 1 * *',
    message: '执行月度治理巡检，分析容量预测、安全基线、权限、补丁版本和整改建议。',
    focus: '30 天治理复盘、容量预测、账号权限、安全基线、证书授权、SLA。',
  },
  {
    value: 'quarterly',
    label: '季度巡检',
    cronExpr: '0 9 1 1,4,7,10 *',
    message: '执行季度架构风险巡检，评估高可用、容灾、备份恢复、性能瓶颈和版本生命周期。',
    focus: '90 天风险趋势、高可用、容灾、备份恢复、性能瓶颈、架构风险。',
  },
  {
    value: 'yearly',
    label: '年度巡检',
    cronExpr: '0 9 1 1 *',
    message: '执行年度资产与合规巡检，形成重大风险、生命周期、容量预算和年度规划建议。',
    focus: '资产盘点、合规审计、重大风险、架构生命周期、预算容量规划。',
  },
  {
    value: 'custom',
    label: '自定义 Cron',
    cronExpr: '0 9 * * *',
    message: '按自定义 Cron 和指令执行只读巡检，输出证据、风险和建议。',
    focus: '以自定义指令为准。',
  },
]

export const inspectionDepthOptions: InspectionDepthOption[] = [
  { value: 'quick', label: '快速', description: '只看高信号健康项，适合高频巡检。' },
  { value: 'standard', label: '标准', description: '覆盖核心健康项、证据、风险和建议。' },
  { value: 'deep', label: '深度', description: '增加趋势、根因线索、容量预测和整改优先级。' },
]

export const emptyCronForm: CronForm = {
  cron_expr: '0 9 * * *',
  message: inspectionCycleOptions[0].message,
  inspection_cycle: 'daily',
  inspection_depth: 'standard',
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
  { label: '每天 09:00', expr: '0 9 * * *', cycle: 'daily' },
  { label: '每周一 09:00', expr: '0 9 * * 1', cycle: 'weekly' },
  { label: '每月 1 日 09:00', expr: '0 9 1 * *', cycle: 'monthly' },
  { label: '每季度首日 09:00', expr: '0 9 1 1,4,7,10 *', cycle: 'quarterly' },
  { label: '每年 1 月 1 日 09:00', expr: '0 9 1 1 *', cycle: 'yearly' },
  { label: '每小时', expr: '0 * * * *', cycle: 'custom' },
  { label: '每30分钟', expr: '*/30 * * * *', cycle: 'custom' },
]
