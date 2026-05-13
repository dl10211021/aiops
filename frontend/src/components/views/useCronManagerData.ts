import { useCallback, useEffect, useState } from 'react'
import { getSavedAssets } from '@/api/assets'
import { getCronJobRuns, getCronJobs, getInspectionTemplates, type CronJobsMetrics, type CronJobsPagination } from '@/api/cron'
import { getNotificationConfig } from '@/api/notifications'
import { getSkillRegistry } from '@/api/skills'
import { useStore } from '@/store'
import type { Asset, CronJob, InspectionRun, InspectionTemplate, SkillInfo } from '@/types'

function orderCronJobs(nextJobs: CronJob[], currentJobs: CronJob[]) {
  const previousOrder = new Map(currentJobs.map((job, index) => [job.id, index]))
  return [...nextJobs].sort((left, right) => {
    const leftOrder = previousOrder.get(left.id)
    const rightOrder = previousOrder.get(right.id)
    if (leftOrder !== undefined && rightOrder !== undefined) return leftOrder - rightOrder
    if (leftOrder !== undefined) return -1
    if (rightOrder !== undefined) return 1
    return left.id.localeCompare(right.id)
  })
}

export function useCronManagerData() {
  const addToast = useStore((s) => s.addToast)
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [jobPage, setJobPage] = useState(1)
  const [jobPageSize, setJobPageSize] = useState(20)
  const [jobQuery, setJobQuery] = useState('')
  const [jobStatus, setJobStatus] = useState('all')
  const [jobPagination, setJobPagination] = useState<CronJobsPagination>({
    page: 1,
    page_size: 20,
    total: 0,
    filtered_total: 0,
    page_count: 1,
  })
  const [jobMetrics, setJobMetrics] = useState<CronJobsMetrics>({
    total: 0,
    scheduled: 0,
    paused: 0,
    failed: 0,
    running: 0,
  })
  const [assets, setAssets] = useState<Asset[]>([])
  const [templates, setTemplates] = useState<InspectionTemplate[]>([])
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [notificationConfig, setNotificationConfig] = useState<Record<string, unknown>>({})
  const [runsByJob, setRunsByJob] = useState<Record<string, InspectionRun[]>>({})

  const loadJobs = useCallback(async () => {
    try {
      const res = await getCronJobs({
        page: jobPage,
        pageSize: jobPageSize,
        query: jobQuery.trim(),
        status: jobStatus,
      })
      const nextJobs = res.data.jobs || []
      setJobs((currentJobs) => orderCronJobs(nextJobs, currentJobs))
      setJobPagination(res.data.pagination || {
        page: 1,
        page_size: nextJobs.length || jobPageSize,
        total: nextJobs.length,
        filtered_total: nextJobs.length,
        page_count: 1,
      })
      setJobMetrics(res.data.metrics || {
        total: nextJobs.length,
        scheduled: nextJobs.filter((job) => job.status !== 'paused').length,
        paused: nextJobs.filter((job) => job.status === 'paused').length,
        failed: 0,
        running: 0,
      })
      const runPairs = await Promise.all(
        nextJobs.map(async (job) => {
          try {
            const runs = await getCronJobRuns(job.id, 20)
            return [job.id, runs.data.runs || []] as const
          } catch {
            return [job.id, []] as const
          }
        })
      )
      setRunsByJob(Object.fromEntries(runPairs))
    } catch {
      addToast('加载巡检计划失败', 'error')
    }
  }, [addToast, jobPage, jobPageSize, jobQuery, jobStatus])

  const loadCatalogs = useCallback(async () => {
    try {
      const notificationRequest = getNotificationConfig().catch(() => ({
        data: {} as Record<string, unknown>,
      }))
      const [assetRes, templateRes, skillRes, notificationRes] = await Promise.all([
        getSavedAssets(),
        getInspectionTemplates(),
        getSkillRegistry(),
        notificationRequest,
      ])
      setAssets(assetRes.data.assets || [])
      setTemplates(templateRes.data.templates || [])
      setSkills((skillRes.data.registry || []).filter((skill) => !skill.is_market))
      setNotificationConfig(notificationRes.data || {})
    } catch {
      setAssets([])
      setTemplates([])
      setSkills([])
      setNotificationConfig({})
    }
  }, [])

  useEffect(() => {
    void loadJobs()
    void loadCatalogs()
  }, [loadJobs, loadCatalogs])

  const hasRunningRun = jobs.length > 0
    ? jobs.some((job) => (job.run_state ? job.run_state.running : runsByJob[job.id]?.[0]?.status === 'running'))
    : Object.values(runsByJob).some((runs) => runs[0]?.status === 'running')

  useEffect(() => {
    if (!hasRunningRun) return undefined
    const timer = window.setInterval(() => {
      void loadJobs()
    }, 4000)
    return () => window.clearInterval(timer)
  }, [hasRunningRun, loadJobs])

  return {
    assets,
    jobMetrics,
    jobPage,
    jobPageSize,
    jobPagination,
    jobQuery,
    jobStatus,
    jobs,
    loadCatalogs,
    loadJobs,
    notificationConfig,
    runsByJob,
    setJobPage,
    setJobPageSize,
    setJobQuery,
    setJobStatus,
    setJobs,
    skills,
    templates,
  }
}
