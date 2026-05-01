import { useCallback, useEffect, useState } from 'react'
import { getSavedAssets } from '@/api/assets'
import { getCronJobRuns, getCronJobs, getInspectionTemplates } from '@/api/cron'
import { getSkillRegistry } from '@/api/skills'
import { useStore } from '@/store'
import type { Asset, CronJob, InspectionRun, InspectionTemplate, SkillInfo } from '@/types'

export function useCronManagerData() {
  const addToast = useStore((s) => s.addToast)
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [templates, setTemplates] = useState<InspectionTemplate[]>([])
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [runsByJob, setRunsByJob] = useState<Record<string, InspectionRun[]>>({})

  const loadJobs = useCallback(async () => {
    try {
      const res = await getCronJobs()
      const nextJobs = res.data.jobs || []
      setJobs(nextJobs)
      const runPairs = await Promise.all(
        nextJobs.map(async (job) => {
          try {
            const runs = await getCronJobRuns(job.id, 3)
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
  }, [addToast])

  const loadCatalogs = useCallback(async () => {
    try {
      const [assetRes, templateRes, skillRes] = await Promise.all([
        getSavedAssets(),
        getInspectionTemplates(),
        getSkillRegistry(),
      ])
      setAssets(assetRes.data.assets || [])
      setTemplates(templateRes.data.templates || [])
      setSkills((skillRes.data.registry || []).filter((skill) => !skill.is_market))
    } catch {
      setAssets([])
      setTemplates([])
      setSkills([])
    }
  }, [])

  useEffect(() => {
    void loadJobs()
    void loadCatalogs()
  }, [loadJobs, loadCatalogs])

  return {
    assets,
    jobs,
    loadCatalogs,
    loadJobs,
    runsByJob,
    setJobs,
    skills,
    templates,
  }
}
