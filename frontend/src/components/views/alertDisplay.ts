export type AlertMetricTone = 'amber' | 'green' | 'red' | 'slate'

export function alertSeverityLabel(severity?: string) {
  const labels: Record<string, string> = {
    critical: '严重',
    error: '错误',
    warning: '警告',
    major: '主要',
    minor: '次要',
    info: '信息',
    unknown: '未知',
  }
  const key = String(severity || 'warning').toLowerCase()
  return labels[key] || severity || '警告'
}

export function alertSourceLabel(source?: string) {
  const labels: Record<string, string> = {
    webhook: '外部 Webhook',
    alertmanager: 'Alertmanager',
    grafana: 'Grafana',
    zabbix: 'Zabbix',
    manageengine: 'ManageEngine',
    prometheus: 'Prometheus',
    hertzbeat: 'HertzBeat',
    api: 'API 接入',
    manual: '手工录入',
  }
  const key = String(source || 'webhook').toLowerCase()
  return labels[key] || source || '外部 Webhook'
}

export function alertClassLabel(value?: string) {
  const labels: Record<string, string> = {
    availability: '可用性',
    capacity: '容量',
    performance: '性能',
    network: '网络',
    database: '数据库',
    security: '安全',
    unknown: '未知',
  }
  const key = String(value || 'unknown').toLowerCase()
  return labels[key] || value || '未知'
}

export function alertNoiseActionLabel(value?: string) {
  const labels: Record<string, string> = {
    analyze: 'AI 分析',
    record_only: '仅记录',
    dedupe_escalate: '重复升级',
    close: '恢复关闭',
    unknown: '未知',
  }
  const key = String(value || 'unknown').toLowerCase()
  return labels[key] || value || '未知'
}

export function alertPriorityLabel(value?: string) {
  const key = String(value || 'p2').toLowerCase()
  return key.toUpperCase()
}

export function formatAlertDate(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export function alertSeverityToneClass(severity?: string) {
  const normalized = String(severity || 'warning').toLowerCase()
  if (normalized === 'critical' || normalized === 'error') {
    return 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert'
  }
  if (normalized === 'warning' || normalized === 'major') {
    return 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent'
  }
  return 'border-ops-success/40 bg-ops-success/10 text-ops-success'
}

export function alertStatusLabel(status?: string) {
  const label: Record<string, string> = {
    open: '未处理',
    acknowledged: '处理中',
    closed: '已关闭',
    suppressed: '已抑制',
  }
  const normalized = String(status || 'open')
  return label[normalized] || normalized
}

export function alertStatusToneClass(status?: string) {
  const cls: Record<string, string> = {
    open: 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert',
    acknowledged: 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent',
    closed: 'border-ops-success/40 bg-ops-success/10 text-ops-success',
    suppressed: 'border-ops-surface1 bg-ops-surface0 text-ops-subtext',
  }
  const normalized = String(status || 'open')
  return cls[normalized] || cls.open
}
