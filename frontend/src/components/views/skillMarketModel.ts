export type SkillCreateForm = {
  skill_id: string
  description: string
  instructions: string
}

export function skillCategoryLabel(category?: string) {
  const labels: Record<string, string> = {
    general: '通用技能',
    system: '系统运维',
    database: '数据库',
    db: '数据库',
    network: '网络安全',
    security: '安全审计',
    cloud: '云平台',
    storage: '存储备份',
    inspection: '巡检模板',
    troubleshooting: '故障处置',
  }
  const key = String(category || 'general').toLowerCase()
  return labels[key] || category || '通用技能'
}
