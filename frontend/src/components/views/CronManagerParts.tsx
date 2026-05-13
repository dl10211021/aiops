import type { CronJob, InspectionRun, SkillInfo } from '@/types'
import {
  agentProfileLabel,
  channelLabel,
  cronScheduleLabel,
  inspectionCycleLabel,
  inspectionDepthLabel,
  skillSummary,
  targetScopeLabel,
} from './cronDisplay'
import { RunHistory } from './CronRunHistory'

interface CronJobCardProps {
  busy: boolean
  cancelling: boolean
  deletingRunId?: string | null
  job: CronJob
  running: boolean
  runs: InspectionRun[]
  skills: SkillInfo[]
  onCancelRun: (job: CronJob) => void
  onDelete: (job: CronJob) => void
  onDeleteReport: (run: InspectionRun) => void
  onEdit: (job: CronJob) => void
  onOpenReport: (run: InspectionRun) => void
  onPauseResume: (job: CronJob) => void
  onRunNow: (job: CronJob) => void
}

export function CronJobCard({
  busy,
  cancelling,
  deletingRunId,
  job,
  running,
  runs,
  skills,
  onCancelRun,
  onDelete,
  onDeleteReport,
  onEdit,
  onOpenReport,
  onPauseResume,
  onRunNow,
}: CronJobCardProps) {
  return (
    <div className="ops-data-panel p-4 transition-all hover:border-ops-accent/40">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="ops-control px-2 py-0.5 text-xs text-ops-accent" title={job.cron_expr || ''}>{cronScheduleLabel(job.cron_expr)}</span>
            <span className={`rounded px-2 py-0.5 text-[11px] ${job.status === 'paused' ? 'bg-ops-alert/15 text-ops-alert' : 'bg-ops-success/15 text-ops-success'}`}>
              {job.status === 'paused' ? '已暂停' : '已调度'}
            </span>
            {running && (
              <span className="rounded bg-ops-accent/15 px-2 py-0.5 text-[11px] text-ops-accent">
                正在巡检
              </span>
            )}
            <span className="text-xs text-ops-overlay">计划 {job.id}</span>
          </div>
          <p className="text-sm text-ops-text">{job.message}</p>
          <div className="mt-3 grid gap-2 text-xs text-ops-subtext md:grid-cols-2 xl:grid-cols-4">
            <span>目标：{job.host || job.target_host || '-'}</span>
            <span>账号：{job.username || '-'}</span>
            <span>资产：{job.asset_id ? `#${job.asset_id}` : '未绑定'}</span>
            <span>模板：{job.template_id || '默认巡检'}</span>
            <span>范围：{targetScopeLabel(job.target_scope, job.scope_value)}</span>
            <span>周期：{inspectionCycleLabel(job.inspection_cycle)} / {inspectionDepthLabel(job.inspection_depth)}</span>
            <span>身份：{agentProfileLabel(job.agent_profile)}</span>
            <span>通知：{channelLabel(job.notification_channel)}</span>
            <span>重试：{job.retry_count || 0} 次</span>
            <span className="xl:col-span-2">技能：{skillSummary(job.active_skills, skills)}</span>
            <span className="xl:col-span-2">下次执行：{job.next_run || job.next_run_time || '-'}</span>
          </div>
          {job.run_state && (
            <div className="mt-3 grid gap-2 rounded border border-ops-surface0 bg-ops-dark/25 p-3 text-[11px] text-ops-subtext md:grid-cols-4">
              <CronRunStateItem
                label="运行态"
                value={job.run_state.running ? '正在巡检' : runStateStatusLabel(job.run_state.effective_status || job.run_state.latest_status)}
                tone={job.run_state.running ? 'accent' : runStateTone(job.run_state.effective_status || job.run_state.latest_status)}
              />
              <CronRunStateItem
                label="最近报告"
                value={job.run_state.latest_run_id || '-'}
              />
              <CronRunStateItem
                label="目标结果"
                value={`${job.run_state.success_count || 0}/${job.run_state.target_count || 0} 成功`}
                tone={(job.run_state.error_count || 0) > 0 ? 'alert' : 'success'}
              />
              <CronRunStateItem
                label="通知"
                value={job.run_state.notification_message || job.run_state.notification_status || '-'}
                tone={String(job.run_state.notification_status || '').toLowerCase() === 'error' ? 'alert' : 'default'}
              />
            </div>
          )}
          {running && (
            <div className="mt-3 rounded border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-xs leading-5 text-ops-accent">
              当前巡检正在执行，后端会持续写入运行记录；需要停止本次执行时可取消当前巡检。
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            disabled={busy || running}
            onClick={() => onRunNow(job)}
            className="ops-primary-action px-3 py-1.5 text-xs disabled:opacity-50"
          >
            立即执行
          </button>
          {running && (
            <button
              disabled={cancelling}
              onClick={() => onCancelRun(job)}
              className="ops-danger-action px-3 py-1.5 text-xs disabled:opacity-50"
            >
              {cancelling ? '取消中...' : '取消当前巡检'}
            </button>
          )}
          <button
            disabled={busy}
            onClick={() => onPauseResume(job)}
            className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
          >
            {job.status === 'paused' ? '恢复' : '暂停'}
          </button>
          <button onClick={() => onEdit(job)} className="ops-muted-action px-3 py-1.5 text-xs">
            编辑
          </button>
          <button onClick={() => onDelete(job)} className="ops-danger-action px-3 py-1.5 text-xs">
            删除
          </button>
        </div>
      </div>
      <RunHistory
        deletingRunId={deletingRunId}
        job={job}
        runs={runs}
        onDeleteReport={onDeleteReport}
        onOpenReport={onOpenReport}
      />
    </div>
  )
}

function CronRunStateItem({
  label,
  value,
  tone = 'default',
}: {
  label: string
  value: string
  tone?: 'default' | 'success' | 'alert' | 'accent'
}) {
  const toneClass = {
    default: 'text-ops-text',
    success: 'text-ops-success',
    alert: 'text-ops-alert',
    accent: 'text-ops-accent',
  }[tone]
  return (
    <div className="min-w-0">
      <div className="text-ops-overlay">{label}</div>
      <div className={`mt-1 truncate font-mono ${toneClass}`} title={value}>
        {value}
      </div>
    </div>
  )
}

function runStateStatusLabel(status?: string | null) {
  const normalized = String(status || '').toLowerCase()
  return {
    running: '运行中',
    completed: '完成',
    failed: '失败',
    partial: '部分完成',
    empty: '无目标',
    cancelled: '已取消',
    orphaned: '运行中断',
  }[normalized] || '暂无运行'
}

function runStateTone(status?: string | null): 'default' | 'success' | 'alert' | 'accent' {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'completed') return 'success'
  if (['failed', 'cancelled', 'orphaned'].includes(normalized)) return 'alert'
  if (['running', 'partial'].includes(normalized)) return 'accent'
  return 'default'
}

export function CronEmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="ops-data-panel p-6">
        <div className="text-sm font-semibold text-ops-text">暂无巡检计划</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-subtext">
          创建定时任务后，AI 会按计划连接资产，执行只读巡检、风险分析和报告归档。建议先从核心主机、数据库和网络设备开始。
        </p>
        <button onClick={onCreate} className="ops-primary-action mt-5 px-4 py-2 text-sm">
          新建巡检计划
        </button>
      </section>
      <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
        {[
          ['推荐频率', '核心资产每小时，普通资产每日，低风险资产每周'],
          ['巡检范围', '支持单资产、资产组、标签和业务范围'],
          ['输出结果', '运行记录、巡检报告、风险项和告警联动'],
        ].map(([title, desc]) => (
          <div key={title} className="ops-data-panel p-4">
            <div className="text-sm font-semibold text-ops-text">{title}</div>
            <p className="mt-2 text-xs leading-5 text-ops-subtext">{desc}</p>
          </div>
        ))}
      </section>
    </div>
  )
}

export function CronField({
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
        className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
      />
    </div>
  )
}
