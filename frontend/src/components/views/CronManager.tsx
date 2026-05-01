import InspectionReportModal from '@/components/inspection/InspectionReportModal'
import PageHeader from '@/components/layout/PageHeader'
import { CronActionDialog } from './CronActionDialog'
import CronJobEditorModal from './CronJobEditorModal'
import { CronEmptyState, CronJobCard } from './CronManagerParts'
import { useCronJobActions } from './useCronJobActions'
import { useCronManagerData } from './useCronManagerData'

export default function CronManager() {
  const { assets, jobs, loadJobs, runsByJob, setJobs, skills, templates } = useCronManagerData()
  const {
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
  } = useCronJobActions({ assets, loadJobs, setJobs })

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          eyebrow="自动化巡检"
          title="定时巡检"
          description="面向资产中心的自动巡检计划，支持模板、通知渠道和立即执行。"
          actions={(
            <>
            <button onClick={() => void loadJobs()} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text">
              刷新
            </button>
            <button onClick={openCreate} className="rounded-lg bg-ops-accent px-3 py-1.5 text-sm font-medium text-ops-dark hover:bg-ops-accent/80">
              + 新建计划
            </button>
            </>
          )}
        />

        {jobs.length > 0 ? (
          <div className="grid gap-3">
            {jobs.map((job) => (
              <CronJobCard
                key={job.id}
                busy={busyJobId === job.id}
                job={job}
                runs={runsByJob[job.id] || []}
                skills={skills}
                onDelete={setDeleteTarget}
                onEdit={openEdit}
                onOpenReport={openReport}
                onPauseResume={(target) => void handlePauseResume(target)}
                onRunNow={setRunNowTarget}
              />
            ))}
          </div>
        ) : (
          <CronEmptyState onCreate={openCreate} />
        )}

        {showEditor && (
          <CronJobEditorModal
            assets={assets}
            form={form}
            skills={skills}
            templates={templates}
            onClose={() => setShowEditor(false)}
            onFormChange={setForm}
            onSave={() => void handleSave()}
            onSelectAsset={selectAsset}
            onToggleSkill={toggleSkill}
          />
        )}

        {reportRunId && <InspectionReportModal runId={reportRunId} onClose={closeReport} />}
        {runNowTarget && (
          <CronActionDialog
            tone="accent"
            title="立即执行巡检计划"
            eyebrow="手动触发"
            description="系统会马上按该计划连接目标资产，执行巡检指令，并根据配置写入运行记录和发送通知。"
            job={runNowTarget}
            busy={busyJobId === runNowTarget.id}
            confirmLabel="确认执行"
            busyLabel="触发中..."
            onClose={() => setRunNowTarget(null)}
            onConfirm={() => void handleRunNowConfirmed()}
          />
        )}
        {deleteTarget && (
          <CronActionDialog
            tone="alert"
            title="删除巡检计划"
            eyebrow="删除计划"
            description="删除后该计划不会再定时触发，已有运行记录和报告不会自动删除。"
            job={deleteTarget}
            busy={busyJobId === deleteTarget.id}
            confirmLabel="确认删除"
            busyLabel="删除中..."
            onClose={() => setDeleteTarget(null)}
            onConfirm={() => void handleDeleteConfirmed()}
          />
        )}
      </div>
    </div>
  )
}
