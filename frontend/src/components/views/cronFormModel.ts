import type { Asset, CronJob } from '@/types'
import type { CronForm } from './cronTypes'

export function cronFormFromJob(job: CronJob): CronForm {
  return {
    id: job.id,
    cron_expr: job.cron_expr || '0 9 * * *',
    message: job.message || '',
    inspection_cycle: job.inspection_cycle || 'daily',
    inspection_depth: job.inspection_depth || 'standard',
    host: job.host || job.target_host || '',
    username: job.username || 'root',
    agent_profile: job.agent_profile || 'default',
    password: '',
    asset_id: job.asset_id ? String(job.asset_id) : '',
    target_scope: job.target_scope || 'asset',
    scope_value: job.scope_value || '',
    template_id: job.template_id || '',
    notification_channel: job.notification_channel || 'auto',
    retry_count: String(job.retry_count ?? 0),
    active_skills: job.active_skills || [],
  }
}

export function cronPayloadFromForm(form: CronForm) {
  return {
    cron_expr: form.cron_expr,
    message: form.message,
    inspection_cycle: form.inspection_cycle || 'daily',
    inspection_depth: form.inspection_depth || 'standard',
    host: form.host,
    username: form.username,
    agent_profile: form.agent_profile,
    password: form.password || undefined,
    asset_id: form.asset_id ? Number(form.asset_id) : null,
    target_scope: form.target_scope,
    scope_value: form.scope_value || undefined,
    template_id: form.template_id || undefined,
    notification_channel: form.notification_channel || 'auto',
    retry_count: Math.max(0, Number(form.retry_count || 0)),
    active_skills: form.active_skills,
  }
}

export function applySelectedAssetToCronForm(current: CronForm, assetId: string, assets: Asset[]): CronForm {
  const asset = assets.find((item) => String(item.id) === assetId)
  return {
    ...current,
    asset_id: assetId,
    host: asset?.host || current.host,
    username: asset?.username || current.username,
    agent_profile: asset?.agent_profile || current.agent_profile,
    target_scope: 'asset',
    scope_value: assetId ? assetId : current.scope_value,
    active_skills: asset?.skills || current.active_skills,
  }
}

export function toggleCronFormSkill(current: CronForm, skillId: string): CronForm {
  const selected = new Set(current.active_skills)
  if (selected.has(skillId)) selected.delete(skillId)
  else selected.add(skillId)
  return { ...current, active_skills: Array.from(selected) }
}
