import { useState, type Dispatch, type SetStateAction } from 'react'
import {
  addCronJob,
  deleteCronJob,
  pauseCronJob,
  resumeCronJob,
  runCronJobNow,
  updateCronJob,
} from '@/api/client'
import { useStore } from '@/store'
import type { Asset, CronJob, InspectionRun } from '@/types'
import {
  applySelectedAssetToCronForm,
  cronFormFromJob,
  cronPayloadFromForm,
  toggleCronFormSkill,
} from './cronFormModel'
import { emptyCronForm, type CronForm } from './cronTypes'

export function useCronJobActions({
  assets,
  loadJobs,
  setJobs,
}: {
  assets: Asset[]
  loadJobs: () => Promise<void>
  setJobs: Dispatch<SetStateAction<CronJob[]>>
}) {
  const addToast = useStore((s) => s.addToast)
  const [showEditor, setShowEditor] = useState(false)
  const [form, setForm] = useState<CronForm>(emptyCronForm)
  const [busyJobId, setBusyJobId] = useState<string | null>(null)
  const [reportRunId, setReportRunId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CronJob | null>(null)
  const [runNowTarget, setRunNowTarget] = useState<CronJob | null>(null)

  const openCreate = () => {
    setForm(emptyCronForm)
    setShowEditor(true)
  }

  const openEdit = (job: CronJob) => {
    setForm(cronFormFromJob(job))
    setShowEditor(true)
  }

  const selectAsset = (assetId: string) => {
    setForm((current) => applySelectedAssetToCronForm(current, assetId, assets))
  }

  const toggleSkill = (skillId: string) => {
    setForm((current) => toggleCronFormSkill(current, skillId))
  }

  const handleSave = async () => {
    const scopeRequiresHost = form.target_scope === 'asset' && !form.asset_id
    if (!form.cron_expr || !form.message || (scopeRequiresHost && (!form.host || !form.username))) {
      addToast(scopeRequiresHost ? '单资产任务请填写目标主机和用户名' : '请填写 Cron 和巡检指令', 'error')
      return
    }
    try {
      if (form.id) {
        await updateCronJob(form.id, cronPayloadFromForm(form))
        addToast('巡检计划已更新', 'success')
      } else {
        await addCronJob(cronPayloadFromForm(form))
        addToast('巡检计划已添加', 'success')
      }
      setShowEditor(false)
      setForm(emptyCronForm)
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存失败', 'error')
    }
  }

  const handleDeleteConfirmed = async () => {
    if (!deleteTarget) return
    setBusyJobId(deleteTarget.id)
    try {
      await deleteCronJob(deleteTarget.id)
      setJobs((current) => current.filter((job) => job.id !== deleteTarget.id))
      setDeleteTarget(null)
      addToast('巡检计划已删除', 'success')
    } catch {
      addToast('删除失败', 'error')
    } finally {
      setBusyJobId(null)
    }
  }

  const handlePauseResume = async (job: CronJob) => {
    setBusyJobId(job.id)
    try {
      if (job.status === 'paused') {
        await resumeCronJob(job.id)
        addToast('巡检计划已恢复', 'success')
      } else {
        await pauseCronJob(job.id)
        addToast('巡检计划已暂停', 'success')
      }
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '操作失败', 'error')
    } finally {
      setBusyJobId(null)
    }
  }

  const handleRunNowConfirmed = async () => {
    if (!runNowTarget) return
    setBusyJobId(runNowTarget.id)
    try {
      await runCronJobNow(runNowTarget.id)
      setRunNowTarget(null)
      addToast('巡检计划已手动触发', 'success')
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '立即执行失败', 'error')
    } finally {
      setBusyJobId(null)
    }
  }

  const openReport = (run: InspectionRun) => {
    setReportRunId(run.id)
  }

  const closeReport = () => {
    setReportRunId(null)
  }

  return {
    busyJobId,
    closeReport,
    deleteTarget,
    form,
    handleDeleteConfirmed,
    handlePauseResume,
    handleRunNowConfirmed,
    handleSave,
    openCreate,
    openEdit,
    openReport,
    reportRunId,
    runNowTarget,
    selectAsset,
    setDeleteTarget,
    setRunNowTarget,
    setShowEditor,
    setForm,
    showEditor,
    toggleSkill,
  }
}
