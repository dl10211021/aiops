import type {
  CronJob,
  InspectionReport,
  InspectionRun,
  InspectionTemplate,
  InspectionTrendPoint,
} from '@/types'
import { request } from './http'

export async function getCronJobs() {
  return request<{ jobs: CronJob[] }>('/cron/list')
}

export async function addCronJob(params: {
  cron_expr: string; message: string; host: string;
  username: string; agent_profile?: string; password?: string;
  asset_id?: number | null; target_scope?: string; scope_value?: string;
  template_id?: string; notification_channel?: string; retry_count?: number;
  active_skills?: string[];
}) {
  return request('/cron/add', { method: 'POST', body: JSON.stringify(params) })
}

export async function updateCronJob(jobId: string, params: {
  cron_expr: string; message: string; host: string;
  username: string; agent_profile?: string; password?: string;
  asset_id?: number | null; target_scope?: string; scope_value?: string;
  template_id?: string; notification_channel?: string; retry_count?: number;
  active_skills?: string[];
}) {
  return request<{ job: CronJob }>(`/cron/${jobId}`, { method: 'PUT', body: JSON.stringify(params) })
}

export async function pauseCronJob(jobId: string) {
  return request<{ job: CronJob }>(`/cron/${jobId}/pause`, { method: 'POST' })
}

export async function resumeCronJob(jobId: string) {
  return request<{ job: CronJob }>(`/cron/${jobId}/resume`, { method: 'POST' })
}

export async function runCronJobNow(jobId: string) {
  return request<{ result: { status: string; job_id: string; run_id: string; target_count: number } }>(`/cron/${jobId}/run`, { method: 'POST' })
}

export async function deleteCronJob(jobId: string) {
  return request(`/cron/${jobId}`, { method: 'DELETE' })
}

export async function getCronJobRuns(jobId: string, limit = 5) {
  return request<{ runs: InspectionRun[] }>(`/cron/${jobId}/runs?limit=${limit}`)
}

export async function getCronJobRun(runId: string) {
  return request<{ run: InspectionRun }>(`/cron/runs/${runId}`)
}

export async function listInspectionRuns(params: { jobId?: string; assetId?: number; limit?: number } = {}) {
  const search = new URLSearchParams()
  if (params.jobId) search.set('job_id', params.jobId)
  if (params.assetId) search.set('asset_id', String(params.assetId))
  if (params.limit) search.set('limit', String(params.limit))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return request<{ runs: InspectionRun[] }>(`/inspection-runs${suffix}`)
}

export async function getInspectionRunReport(runId: string) {
  return request<{ report: InspectionReport }>(`/inspection-runs/${runId}/report`)
}

export async function exportInspectionRunReport(runId: string, format: 'markdown' | 'json' = 'markdown') {
  return request<{ format: string; content_type: string; content: string }>(
    `/inspection-runs/${runId}/export?format=${format}`
  )
}

export async function getDashboardInspectionRunTrend() {
  return request<{ points: InspectionTrendPoint[] }>('/dashboard/inspection-runs/trend')
}

export async function getInspectionTemplates() {
  return request<{ templates: InspectionTemplate[] }>('/inspection-templates')
}

export async function createInspectionTemplate(template: InspectionTemplate) {
  return request<{ template: InspectionTemplate }>('/inspection-templates', {
    method: 'POST',
    body: JSON.stringify(template),
  })
}

export async function updateInspectionTemplate(templateId: string, template: InspectionTemplate) {
  return request<{ template: InspectionTemplate }>(`/inspection-templates/${templateId}`, {
    method: 'PUT',
    body: JSON.stringify(template),
  })
}

export async function deleteInspectionTemplate(templateId: string) {
  return request(`/inspection-templates/${templateId}`, { method: 'DELETE' })
}
