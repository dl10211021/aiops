import type {
  CronJob,
  InspectionReport,
  InspectionRun,
  InspectionTemplate,
  InspectionTrendPoint,
} from '@/types'
import { request } from './http'

export interface CronJobsPagination {
  page: number
  page_size: number
  total: number
  filtered_total: number
  page_count: number
}

export interface CronJobsMetrics {
  total: number
  scheduled: number
  paused: number
  failed: number
  running: number
}

export interface InspectionRunsPagination {
  page: number
  page_size: number
  total: number
  filtered_total: number
  page_count: number
}

export interface InspectionRunsMetrics {
  total: number
  completed: number
  failed: number
  partial: number
  running: number
  cancelled: number
  empty: number
}

export interface InspectionRetentionPreview {
  policy: {
    keep_latest_per_job: number
    older_than_days: number
    limit: number
    dry_run: boolean
  }
  summary: {
    total_runs: number
    candidate_count: number
    candidate_count_total: number
    skipped_running: number
    estimated_reclaimable_bytes: number
  }
  candidates: Array<{
    id: string
    job_id?: string
    status?: string
    message?: string
    target_count?: number
    started_at?: string
    completed_at?: string | null
    reason: string
    estimated_bytes: number
  }>
}

export async function getCronJobs(params: { page?: number; pageSize?: number; query?: string; status?: string } = {}) {
  const search = new URLSearchParams()
  if (params.page) search.set('page', String(params.page))
  if (params.pageSize) search.set('page_size', String(params.pageSize))
  if (params.query) search.set('query', params.query)
  if (params.status && params.status !== 'all') search.set('status', params.status)
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return request<{ jobs: CronJob[]; pagination?: CronJobsPagination; metrics?: CronJobsMetrics }>(`/cron/list${suffix}`)
}

export async function addCronJob(params: {
  cron_expr: string; message: string; host: string;
  inspection_cycle?: string; inspection_depth?: string;
  username: string; agent_profile?: string; password?: string;
  asset_id?: number | null; target_scope?: string; scope_value?: string;
  template_id?: string; notification_channel?: string; retry_count?: number;
  active_skills?: string[];
}) {
  return request('/cron/add', { method: 'POST', body: JSON.stringify(params) })
}

export async function updateCronJob(jobId: string, params: {
  cron_expr: string; message: string; host: string;
  inspection_cycle?: string; inspection_depth?: string;
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
  return request<{ result: { status: string; job_id: string; run_id: string; target_count: number } }>(
    `/cron/${jobId}/run`,
    { method: 'POST' }
  )
}

export async function startCronJobRun(jobId: string) {
  return request<{ result: { status: string; job_id: string; run_id?: string; target_count: number; message?: string } }>(
    `/cron/${jobId}/run/async`,
    { method: 'POST' }
  )
}

export async function cancelCronJobRun(jobId: string) {
  return request<{ result: { status: string; job_id: string; run_id?: string } }>(
    `/cron/${jobId}/run/cancel`,
    { method: 'POST' }
  )
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

export async function deleteInspectionRun(runId: string) {
  return request<{ run_id: string }>(`/inspection-runs/${runId}`, { method: 'DELETE' })
}

export async function listInspectionRuns(params: {
  assetId?: number
  jobId?: string
  limit?: number
  page?: number
  pageSize?: number
  query?: string
  status?: string
} = {}) {
  const search = new URLSearchParams()
  if (params.jobId) search.set('job_id', params.jobId)
  if (params.assetId) search.set('asset_id', String(params.assetId))
  if (params.limit) search.set('limit', String(params.limit))
  if (params.page) search.set('page', String(params.page))
  if (params.pageSize) search.set('page_size', String(params.pageSize))
  if (params.query) search.set('query', params.query)
  if (params.status && params.status !== 'all') search.set('status', params.status)
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return request<{
    runs: InspectionRun[]
    pagination?: InspectionRunsPagination
    metrics?: InspectionRunsMetrics
  }>(`/inspection-runs${suffix}`)
}

export async function previewInspectionRunRetention(params: {
  keepLatestPerJob?: number
  olderThanDays?: number
  limit?: number
} = {}) {
  const search = new URLSearchParams()
  if (params.keepLatestPerJob) search.set('keep_latest_per_job', String(params.keepLatestPerJob))
  if (params.olderThanDays) search.set('older_than_days', String(params.olderThanDays))
  if (params.limit) search.set('limit', String(params.limit))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return request<{ preview: InspectionRetentionPreview }>(`/inspection-runs/retention/preview${suffix}`)
}

export async function getInspectionRunReport(runId: string) {
  return request<{ report: InspectionReport }>(`/inspection-runs/${runId}/report`)
}

export async function exportInspectionRunReport(runId: string, format: 'markdown' | 'html' | 'json' = 'markdown') {
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
