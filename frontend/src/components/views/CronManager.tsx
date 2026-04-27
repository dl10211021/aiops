import { useCallback, useEffect, useState } from 'react'
import { useStore } from '@/store'
import {
  addCronJob,
  deleteCronJob,
  exportInspectionRunReport,
  getCronJobRuns,
  getCronJobs,
  getInspectionRunReport,
  getInspectionTemplates,
  getSavedAssets,
  pauseCronJob,
  resumeCronJob,
  runCronJobNow,
  updateCronJob,
} from '@/api/client'
import type { Asset, CronJob, InspectionReport, InspectionRun, InspectionTemplate } from '@/types'

type CronForm = {
  id?: string
  cron_expr: string
  message: string
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
}

const emptyForm: CronForm = {
  cron_expr: '0 9 * * *',
  message: '执行一次标准只读巡检，输出健康状态、异常项、风险等级和建议。',
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
}

export default function CronManager() {
  const addToast = useStore((s) => s.addToast)
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [templates, setTemplates] = useState<InspectionTemplate[]>([])
  const [runsByJob, setRunsByJob] = useState<Record<string, InspectionRun[]>>({})
  const [showEditor, setShowEditor] = useState(false)
  const [form, setForm] = useState<CronForm>(emptyForm)
  const [busyJobId, setBusyJobId] = useState<string | null>(null)
  const [reportRunId, setReportRunId] = useState<string | null>(null)
  const [report, setReport] = useState<InspectionReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState('')

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
      const [assetRes, templateRes] = await Promise.all([
        getSavedAssets(),
        getInspectionTemplates(),
      ])
      setAssets(assetRes.data.assets || [])
      setTemplates(templateRes.data.templates || [])
    } catch {
      setAssets([])
      setTemplates([])
    }
  }, [])

  useEffect(() => {
    void loadJobs()
    void loadCatalogs()
  }, [loadJobs, loadCatalogs])

  const openCreate = () => {
    setForm(emptyForm)
    setShowEditor(true)
  }

  const openEdit = (job: CronJob) => {
    setForm({
      id: job.id,
      cron_expr: job.cron_expr || '0 9 * * *',
      message: job.message || '',
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
    })
    setShowEditor(true)
  }

  const selectAsset = (assetId: string) => {
    const asset = assets.find((item) => String(item.id) === assetId)
    setForm((current) => ({
      ...current,
      asset_id: assetId,
      host: asset?.host || current.host,
      username: asset?.username || current.username,
      agent_profile: asset?.agent_profile || current.agent_profile,
      target_scope: 'asset',
      scope_value: assetId ? assetId : current.scope_value,
    }))
  }

  const payload = () => ({
    cron_expr: form.cron_expr,
    message: form.message,
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
  })

  const handleSave = async () => {
    const scopeRequiresHost = form.target_scope === 'asset' && !form.asset_id
    if (!form.cron_expr || !form.message || (scopeRequiresHost && (!form.host || !form.username))) {
      addToast(scopeRequiresHost ? '单资产任务请填写目标主机和用户名' : '请填写 Cron 和巡检指令', 'error')
      return
    }
    try {
      if (form.id) {
        await updateCronJob(form.id, payload())
        addToast('巡检计划已更新', 'success')
      } else {
        await addCronJob(payload())
        addToast('巡检计划已添加', 'success')
      }
      setShowEditor(false)
      setForm(emptyForm)
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存失败', 'error')
    }
  }

  const handleDelete = async (jobId: string) => {
    if (!confirm('确定要删除此巡检计划？')) return
    try {
      await deleteCronJob(jobId)
      setJobs(jobs.filter((j) => j.id !== jobId))
      addToast('巡检计划已删除', 'success')
    } catch {
      addToast('删除失败', 'error')
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

  const handleRunNow = async (job: CronJob) => {
    if (!confirm(`将立即触发巡检计划 ${job.id}，可能连接真实资产并发送通知，是否继续？`)) return
    setBusyJobId(job.id)
    try {
      await runCronJobNow(job.id)
      addToast('巡检计划已手动触发', 'success')
      await loadJobs()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '立即执行失败', 'error')
    } finally {
      setBusyJobId(null)
    }
  }

  const openReport = async (run: InspectionRun) => {
    setReportRunId(run.id)
    setReport(null)
    setReportError('')
    setReportLoading(true)
    try {
      const res = await getInspectionRunReport(run.id)
      setReport(res.data.report)
    } catch (e: unknown) {
      setReportError(e instanceof Error ? e.message : '加载巡检报告失败')
    } finally {
      setReportLoading(false)
    }
  }

  const closeReport = () => {
    setReportRunId(null)
    setReport(null)
    setReportError('')
  }

  const handleExportReport = async (format: 'markdown' | 'json') => {
    if (!reportRunId) return
    try {
      const res = await exportInspectionRunReport(reportRunId, format)
      downloadText(
        `inspection-${reportRunId}.${format === 'json' ? 'json' : 'md'}`,
        res.data.content,
        res.data.content_type
      )
      addToast('巡检报告已生成下载', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '导出巡检报告失败', 'error')
    }
  }

  const cronPresets = [
    { label: '每天 09:00', expr: '0 9 * * *' },
    { label: '每小时', expr: '0 * * * *' },
    { label: '每30分钟', expr: '*/30 * * * *' },
    { label: '每周一 09:00', expr: '0 9 * * 1' },
  ]

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-ops-accent">Inspection Automation</p>
            <h1 className="mt-1 text-2xl font-black tracking-tight text-ops-text">定时巡检</h1>
            <p className="mt-1 text-sm text-ops-subtext">面向资产中心的自动巡检计划，支持模板、通知渠道和立即执行。</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => void loadJobs()} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text">
              刷新
            </button>
            <button onClick={openCreate} className="rounded-lg bg-ops-accent px-3 py-1.5 text-sm font-medium text-ops-dark hover:bg-ops-accent/80">
              + 新建计划
            </button>
          </div>
        </div>

        {jobs.length > 0 ? (
          <div className="grid gap-3">
            {jobs.map((job) => (
              <div key={job.id} className="ops-glass rounded-2xl border p-4 transition-all hover:border-ops-accent/40">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="rounded bg-ops-dark px-2 py-0.5 font-mono text-xs text-ops-accent">{job.cron_expr || 'unknown'}</span>
                      <span className={`rounded px-2 py-0.5 text-[11px] ${job.status === 'paused' ? 'bg-ops-alert/15 text-ops-alert' : 'bg-ops-success/15 text-ops-success'}`}>
                        {job.status === 'paused' ? '已暂停' : '已调度'}
                      </span>
                      <span className="text-xs text-ops-overlay">{job.id}</span>
                    </div>
                    <p className="text-sm text-ops-text">{job.message}</p>
                    <div className="mt-3 grid gap-2 text-xs text-ops-subtext md:grid-cols-2 xl:grid-cols-4">
                      <span>目标：{job.host || job.target_host || '-'}</span>
                      <span>账号：{job.username || '-'}</span>
                      <span>资产：{job.asset_id || '未绑定'}</span>
                      <span>模板：{job.template_id || '默认'}</span>
                      <span>范围：{job.target_scope || 'asset'} {job.scope_value || ''}</span>
                      <span>角色：{job.agent_profile || 'default'}</span>
                      <span>通知：{job.notification_channel || 'auto'}</span>
                      <span>重试：{job.retry_count || 0}</span>
                      <span>下次：{job.next_run || job.next_run_time || '-'}</span>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <button
                      disabled={busyJobId === job.id}
                      onClick={() => void handleRunNow(job)}
                      className="rounded-lg bg-ops-accent/15 px-3 py-1.5 text-xs text-ops-accent hover:bg-ops-accent/25 disabled:opacity-50"
                    >
                      立即执行
                    </button>
                    <button
                      disabled={busyJobId === job.id}
                      onClick={() => void handlePauseResume(job)}
                      className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text disabled:opacity-50"
                    >
                      {job.status === 'paused' ? '恢复' : '暂停'}
                    </button>
                    <button onClick={() => openEdit(job)} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text">
                      编辑
                    </button>
                    <button onClick={() => void handleDelete(job.id)} className="rounded-lg bg-ops-alert/10 px-3 py-1.5 text-xs text-ops-alert hover:bg-ops-alert/20">
                      删除
                    </button>
                  </div>
                </div>
                <RunHistory runs={runsByJob[job.id] || []} onOpenReport={openReport} />
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-ops-surface0 bg-ops-panel/60 py-20 text-center text-ops-subtext">
            <div className="mb-3 text-4xl">CR</div>
            <p>暂无巡检计划</p>
            <p className="mt-1 text-xs">创建定时任务后，AI 将按计划连接资产并执行运维巡检。</p>
          </div>
        )}

        {showEditor && (
          <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/55 p-4" onClick={() => setShowEditor(false)}>
            <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-ops-surface1 bg-ops-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-bold text-ops-text">{form.id ? '编辑巡检计划' : '新建巡检计划'}</h2>
                <button onClick={() => setShowEditor(false)} className="text-sm text-ops-overlay hover:text-ops-text">关闭</button>
              </div>
              <div className="grid gap-4">
                <div>
                  <label className="text-xs text-ops-subtext">绑定资产</label>
                  <select
                    value={form.asset_id}
                    onChange={(e) => selectAsset(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                  >
                    <option value="">不绑定，手动填写目标</option>
                    {assets.map((asset) => (
                      <option key={asset.id} value={asset.id}>
                        #{asset.id} {asset.remark || asset.host} - {asset.username}@{asset.host}:{asset.port} ({asset.asset_type}/{asset.protocol || asset.asset_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-ops-subtext">Cron 表达式</label>
                  <input
                    value={form.cron_expr}
                    onChange={(e) => setForm({ ...form, cron_expr: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-sm text-ops-text outline-none focus:border-ops-accent"
                  />
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {cronPresets.map((p) => (
                      <button
                        key={p.expr}
                        onClick={() => setForm({ ...form, cron_expr: p.expr })}
                        className="rounded bg-ops-surface0 px-2 py-0.5 text-[10px] text-ops-subtext hover:text-ops-text"
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-ops-subtext">巡检指令</label>
                  <textarea
                    value={form.message}
                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                    rows={4}
                    className="mt-1 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    placeholder="例如：执行一次 Linux/K8s/MySQL 标准只读巡检..."
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <Field label="目标主机" value={form.host} onChange={(host) => setForm({ ...form, host })} placeholder="192.168.1.1" />
                  <Field label="用户名" value={form.username} onChange={(username) => setForm({ ...form, username })} />
                  <Field label="Agent 角色" value={form.agent_profile} onChange={(agent_profile) => setForm({ ...form, agent_profile })} />
                  <Field label="密码/凭据覆盖" type="password" value={form.password} onChange={(password) => setForm({ ...form, password })} placeholder="留空则使用后端任务保存凭据" />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="text-xs text-ops-subtext">目标范围</label>
                    <select
                      value={form.target_scope}
                      onChange={(e) => setForm({ ...form, target_scope: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      <option value="asset">单资产</option>
                      <option value="tag">资产标签</option>
                      <option value="category">资产分类</option>
                      <option value="protocol">登录协议</option>
                      <option value="asset_type">资产类型</option>
                      <option value="all">全部资产</option>
                    </select>
                  </div>
                  <Field label="范围值" value={form.scope_value} onChange={(scope_value) => setForm({ ...form, scope_value })} placeholder="资产ID、标签、分类或协议" />
                  <div>
                    <label className="text-xs text-ops-subtext">巡检模板</label>
                    <select
                      value={form.template_id}
                      onChange={(e) => setForm({ ...form, template_id: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      <option value="">默认内置巡检</option>
                      {templates.map((template) => (
                        <option key={template.id} value={template.id}>{template.name || template.id}</option>
                      ))}
                    </select>
                  </div>
                  <Field label="通知渠道" value={form.notification_channel} onChange={(notification_channel) => setForm({ ...form, notification_channel })} placeholder="auto / webhook / email" />
                  <Field label="失败重试次数" value={form.retry_count} onChange={(retry_count) => setForm({ ...form, retry_count })} placeholder="0" type="number" />
                </div>
              </div>
              <div className="mt-5 flex justify-end gap-2">
                <button onClick={() => setShowEditor(false)} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
                <button onClick={() => void handleSave()} className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark hover:bg-ops-accent/80">
                  保存
                </button>
              </div>
            </div>
          </div>
        )}

        {reportRunId && (
          <ReportModal
            report={report}
            loading={reportLoading}
            error={reportError}
            onClose={closeReport}
            onExport={handleExportReport}
          />
        )}
      </div>
    </div>
  )
}

function RunHistory({ runs, onOpenReport }: { runs: InspectionRun[]; onOpenReport: (run: InspectionRun) => void }) {
  const latest = runs[0]
  if (!latest) {
    return (
      <div className="mt-4 rounded-xl border border-ops-surface0 bg-ops-dark/25 px-3 py-2 text-xs text-ops-overlay">
        暂无运行记录。手动执行或等待定时触发后会显示目标结果。
      </div>
    )
  }
  const tone = latest.status === 'completed'
    ? 'text-ops-success bg-ops-success/10'
    : latest.status === 'partial'
      ? 'text-ops-accent bg-ops-accent/10'
      : 'text-ops-alert bg-ops-alert/10'
  return (
    <div className="mt-4 rounded-xl border border-ops-surface0 bg-ops-dark/25 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-[11px] ${tone}`}>{latest.status}</span>
          <span className="font-mono text-[11px] text-ops-overlay">{latest.id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-ops-overlay">{latest.completed_at}</span>
          <button
            onClick={() => onOpenReport(latest)}
            className="rounded-lg bg-ops-accent/15 px-2.5 py-1 text-[11px] text-ops-accent hover:bg-ops-accent/25"
          >
            查看报告
          </button>
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {latest.targets.slice(0, 6).map((target) => (
          <div key={`${target.asset_id || target.host}-${target.host}`} className="rounded-lg bg-ops-surface0/60 px-2.5 py-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-ops-text">{target.host}</span>
              <span className={target.status === 'success' ? 'text-ops-success' : 'text-ops-alert'}>{target.status}</span>
            </div>
            <div className="mt-1 truncate text-[11px] text-ops-overlay">
              #{target.asset_id || '-'} {target.asset_type || '-'} / {target.protocol || '-'}
            </div>
          </div>
        ))}
      </div>
      {latest.targets.length > 6 && (
        <div className="mt-2 text-[11px] text-ops-overlay">还有 {latest.targets.length - 6} 个目标未展开显示</div>
      )}
    </div>
  )
}

function ReportModal({
  report,
  loading,
  error,
  onClose,
  onExport,
}: {
  report: InspectionReport | null
  loading: boolean
  error: string
  onClose: () => void
  onExport: (format: 'markdown' | 'json') => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-2xl border border-ops-surface1 bg-ops-panel shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ops-surface0 px-5 py-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-ops-accent">Inspection Report</p>
            <h2 className="mt-1 text-lg font-bold text-ops-text">巡检报告</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              disabled={!report}
              onClick={() => onExport('markdown')}
              className="rounded-lg bg-ops-accent/15 px-3 py-1.5 text-xs text-ops-accent hover:bg-ops-accent/25 disabled:opacity-50"
            >
              导出 MD
            </button>
            <button
              disabled={!report}
              onClick={() => onExport('json')}
              className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text disabled:opacity-50"
            >
              导出 JSON
            </button>
            <button onClick={onClose} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text">
              关闭
            </button>
          </div>
        </div>

        <div className="max-h-[calc(92vh-76px)] overflow-y-auto p-5">
          {loading && <div className="py-16 text-center text-sm text-ops-subtext">正在加载巡检报告...</div>}
          {error && (
            <div className="rounded-xl border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
              {error}
            </div>
          )}
          {!loading && !error && report && (
            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-4">
                <ReportMetric label="目标数" value={report.summary.target_count} />
                <ReportMetric label="成功" value={report.summary.success_count} tone="green" />
                <ReportMetric label="失败" value={report.summary.error_count} tone="red" />
                <ReportMetric label="成功率" value={`${report.summary.success_rate}%`} tone="amber" />
              </div>

              <section className="rounded-2xl border border-ops-surface0 bg-ops-dark/25 p-4">
                <div className="grid gap-2 text-xs text-ops-subtext md:grid-cols-2">
                  <Info label="Run ID" value={report.run_id} />
                  <Info label="Job ID" value={report.job_id} />
                  <Info label="状态" value={report.status} />
                  <Info label="范围" value={`${report.target_scope} / ${report.scope_value || '-'}`} />
                  <Info label="开始" value={report.started_at || '-'} />
                  <Info label="完成" value={report.completed_at || '-'} />
                </div>
                <div className="mt-3 rounded-xl bg-ops-surface0/55 px-3 py-2 text-sm text-ops-subtext">
                  {report.message}
                </div>
              </section>

              <section className="rounded-2xl border border-ops-surface0 bg-ops-dark/25">
                <div className="border-b border-ops-surface0 px-4 py-3 text-sm font-semibold text-ops-text">目标结果</div>
                <div className="divide-y divide-ops-surface0">
                  {report.targets.length === 0 && (
                    <div className="p-8 text-center text-sm text-ops-subtext">报告中暂无目标结果</div>
                  )}
                  {report.targets.map((target, index) => (
                    <div key={`${target.asset_id || index}-${target.host}`} className="p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          <span className={`rounded px-2 py-0.5 text-[11px] ${target.status === 'success' ? 'bg-ops-success/10 text-ops-success' : 'bg-ops-alert/10 text-ops-alert'}`}>
                            {target.status}
                          </span>
                          <span className="truncate font-semibold text-ops-text">{target.host || '-'}</span>
                        </div>
                        <span className="font-mono text-[11px] text-ops-overlay">#{target.asset_id || '-'} {target.asset_type || '-'} / {target.protocol || '-'}</span>
                      </div>
                      {target.error && (
                        <div className="mt-3 rounded-xl border border-ops-alert/30 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
                          {target.error}
                        </div>
                      )}
                      {target.result && (
                        <pre className="mt-3 max-h-56 overflow-auto rounded-xl border border-ops-surface0 bg-ops-dark/55 p-3 text-xs leading-relaxed text-ops-subtext">
                          {String(target.result)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ReportMetric({ label, value, tone = 'default' }: { label: string; value: string | number; tone?: 'default' | 'green' | 'red' | 'amber' }) {
  const toneClass = {
    default: 'text-ops-text',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    amber: 'text-ops-accent',
  }[tone]
  return (
    <div className="rounded-2xl border border-ops-surface0 bg-ops-dark/25 p-4">
      <div className="text-xs text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <div>
      <label className="text-xs text-ops-subtext">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
      />
    </div>
  )
}

function Info({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-ops-overlay">{label}</span>
      <span className="truncate text-right font-mono text-ops-text">{String(value)}</span>
    </div>
  )
}

function downloadText(filename: string, content: string, contentType: string) {
  const blob = new Blob([content], { type: contentType || 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
