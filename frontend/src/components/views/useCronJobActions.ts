import { useState, type Dispatch, type SetStateAction } from 'react'
import {
  addCronJob,
  cancelCronJobRun,
  deleteCronJob,
  deleteInspectionRun,
  pauseCronJob,
  resumeCronJob,
  startCronJobRun,
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
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null)
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null)
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
    if (!form.cron_expr || !form.message) {
      addToast('请填写 Cron 和巡检指令', 'error')
      return
    }
    if (assets.length === 0) {
      addToast('请先在资产中心添加资产，再创建巡检计划', 'error')
      return
    }
    if (form.target_scope === 'asset' && !form.asset_id) {
      addToast('请选择资产中心里的巡检资产', 'error')
      return
    }
    if (!['asset', 'all'].includes(form.target_scope) && !form.scope_value) {
      addToast('请选择资产范围值', 'error')
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
    const target = runNowTarget
    if (!target) return
    setRunNowTarget(null)
    setBusyJobId(target.id)
    try {
      const response = await startCronJobRun(target.id)
      const status = response.data.result?.status
      if (status === 'running') {
        addToast('该计划已有巡检正在执行，可在运行记录里查看进度', 'error')
      } else {
        addToast('巡检已在后台启动，可在运行记录里查看进度', 'success')
      }
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '立即执行失败', 'error')
    } finally {
      setBusyJobId(null)
    }
  }

  const handleCancelRunningRun = async (job: CronJob) => {
    setCancellingJobId(job.id)
    try {
      await cancelCronJobRun(job.id)
      addToast('已提交取消请求，运行记录会更新为已取消', 'success')
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '取消当前巡检失败', 'error')
    } finally {
      setCancellingJobId(null)
    }
  }

  const openReport = (run: InspectionRun) => {
    setReportRunId(run.id)
  }

  const closeReport = () => {
    setReportRunId(null)
  }

  const handleDeleteReport = async (run: InspectionRun) => {
    const ok = window.confirm(`确认删除巡检报告 ${run.id}？删除后不会影响巡检计划。`)
    if (!ok) return
    setDeletingRunId(run.id)
    try {
      await deleteInspectionRun(run.id)
      if (reportRunId === run.id) setReportRunId(null)
      addToast('巡检报告已删除', 'success')
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '删除巡检报告失败', 'error')
    } finally {
      setDeletingRunId(null)
    }
  }

  return {
    busyJobId,
    cancellingJobId,
    closeReport,
    deleteTarget,
    deletingRunId,
    form,
    handleDeleteConfirmed,
    handleCancelRunningRun,
    handleDeleteReport,
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
