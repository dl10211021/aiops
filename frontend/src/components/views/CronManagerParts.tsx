import type { CronJob, InspectionRun, SkillInfo } from '@/types'
import {
  agentProfileLabel,
  channelLabel,
  cronScheduleLabel,
  skillSummary,
  targetScopeLabel,
} from './cronDisplay'
import { RunHistory } from './CronRunHistory'

interface CronJobCardProps {
  busy: boolean
  job: CronJob
  runs: InspectionRun[]
  skills: SkillInfo[]
  onDelete: (job: CronJob) => void
  onEdit: (job: CronJob) => void
  onOpenReport: (run: InspectionRun) => void
  onPauseResume: (job: CronJob) => void
  onRunNow: (job: CronJob) => void
}

export function CronJobCard({
  busy,
  job,
  runs,
  skills,
  onDelete,
  onEdit,
  onOpenReport,
  onPauseResume,
  onRunNow,
}: CronJobCardProps) {
  return (
    <div className="ops-glass rounded-lg border p-4 transition-all hover:border-ops-accent/40">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded bg-ops-dark px-2 py-0.5 text-xs text-ops-accent" title={job.cron_expr || ''}>{cronScheduleLabel(job.cron_expr)}</span>
            <span className={`rounded px-2 py-0.5 text-[11px] ${job.status === 'paused' ? 'bg-ops-alert/15 text-ops-alert' : 'bg-ops-success/15 text-ops-success'}`}>
              {job.status === 'paused' ? '已暂停' : '已调度'}
            </span>
            <span className="text-xs text-ops-overlay">计划 {job.id}</span>
          </div>
          <p className="text-sm text-ops-text">{job.message}</p>
          <div className="mt-3 grid gap-2 text-xs text-ops-subtext md:grid-cols-2 xl:grid-cols-4">
            <span>目标：{job.host || job.target_host || '-'}</span>
            <span>账号：{job.username || '-'}</span>
            <span>资产：{job.asset_id ? `#${job.asset_id}` : '未绑定'}</span>
            <span>模板：{job.template_id || '默认巡检'}</span>
            <span>范围：{targetScopeLabel(job.target_scope, job.scope_value)}</span>
            <span>身份：{agentProfileLabel(job.agent_profile)}</span>
            <span>通知：{channelLabel(job.notification_channel)}</span>
            <span>重试：{job.retry_count || 0} 次</span>
            <span className="xl:col-span-2">技能：{skillSummary(job.active_skills, skills)}</span>
            <span className="xl:col-span-2">下次执行：{job.next_run || job.next_run_time || '-'}</span>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            disabled={busy}
            onClick={() => onRunNow(job)}
            className="rounded-lg bg-ops-accent/15 px-3 py-1.5 text-xs text-ops-accent hover:bg-ops-accent/25 disabled:opacity-50"
          >
            立即执行
          </button>
          <button
            disabled={busy}
            onClick={() => onPauseResume(job)}
            className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text disabled:opacity-50"
          >
            {job.status === 'paused' ? '恢复' : '暂停'}
          </button>
          <button onClick={() => onEdit(job)} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text">
            编辑
          </button>
          <button onClick={() => onDelete(job)} className="rounded-lg bg-ops-alert/10 px-3 py-1.5 text-xs text-ops-alert hover:bg-ops-alert/20">
            删除
          </button>
        </div>
      </div>
      <RunHistory runs={runs} onOpenReport={onOpenReport} />
    </div>
  )
}

export function CronEmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-6">
        <div className="text-sm font-semibold text-ops-text">暂无巡检计划</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-subtext">
          创建定时任务后，AI 会按计划连接资产，执行只读巡检、风险分析和报告归档。建议先从核心主机、数据库和网络设备开始。
        </p>
        <button onClick={onCreate} className="mt-5 rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/85">
          新建巡检计划
        </button>
      </section>
      <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
        {[
          ['推荐频率', '核心资产每小时，普通资产每日，低风险资产每周'],
          ['巡检范围', '支持单资产、资产组、标签和业务范围'],
          ['输出结果', '运行记录、巡检报告、风险项和告警联动'],
        ].map(([title, desc]) => (
          <div key={title} className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-4">
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
        className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
      />
    </div>
  )
}
