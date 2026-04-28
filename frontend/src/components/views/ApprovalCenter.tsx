import { useCallback, useEffect, useMemo, useState } from 'react'
import { decideApproval, executeApproval, getApprovals } from '@/api/client'
import { useStore } from '@/store'
import type { ApprovalRequest } from '@/types'

const STATUS_OPTIONS = [
  { id: 'pending', label: '待审批' },
  { id: 'approved', label: '已批准' },
  { id: 'rejected', label: '已拒绝' },
  { id: 'timeout', label: '已超时' },
  { id: 'all', label: '全部' },
]

export default function ApprovalCenter() {
  const addToast = useStore((s) => s.addToast)
  const [status, setStatus] = useState('pending')
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await getApprovals(status, 200)
      setApprovals(res.data.approvals || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载审批队列失败')
    } finally {
      setLoading(false)
    }
  }, [status])

  useEffect(() => { void load() }, [load])

  const counts = useMemo(() => {
    const next = { pending: 0, approved: 0, rejected: 0, timeout: 0 }
    for (const item of approvals) {
      if (item.status in next) next[item.status as keyof typeof next] += 1
    }
    return next
  }, [approvals])

  const handleDecision = async (approval: ApprovalRequest, approved: boolean) => {
    const action = approved ? '批准' : '拒绝'
    const note = window.prompt(`请输入${action}原因，可留空`, '') || ''
    setBusyId(approval.id)
    try {
      await decideApproval(approval.id, approved, 'ops-admin', note)
      addToast(`审批已${action}`, 'success')
      await load()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '审批处理失败', 'error')
    } finally {
      setBusyId(null)
    }
  }

  const handleExecute = async (approval: ApprovalRequest) => {
    setBusyId(approval.id)
    try {
      await executeApproval(approval.id)
      addToast('审批动作已执行', 'success')
      await load()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '审批执行失败', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.24em] text-ops-accent">Risk Approval Queue</p>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-ops-text">审批中心</h1>
            <p className="mt-1 text-sm text-ops-subtext">所有命中后端审批策略的高危工具调用都会进入这里，可查询、批准、拒绝和审计。</p>
          </div>
          <button
            onClick={() => void load()}
            className="rounded-xl border border-ops-surface1 bg-ops-surface0 px-4 py-2 text-sm text-ops-text transition-colors hover:border-ops-accent/60"
          >
            刷新
          </button>
        </div>

        <div className="mb-5 flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((item) => (
            <button
              key={item.id}
              onClick={() => setStatus(item.id)}
              className={`rounded-full border px-4 py-2 text-sm transition-colors ${
                status === item.id
                  ? 'border-ops-accent bg-ops-accent text-ops-dark'
                  : 'border-ops-surface1 bg-ops-surface0 text-ops-subtext hover:text-ops-text'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        <div className="mb-5 grid gap-3 md:grid-cols-4">
          <Metric label="待审批" value={status === 'pending' ? approvals.length : counts.pending} tone="amber" />
          <Metric label="已批准" value={status === 'approved' ? approvals.length : counts.approved} tone="green" />
          <Metric label="已拒绝" value={status === 'rejected' ? approvals.length : counts.rejected} tone="red" />
          <Metric label="已超时" value={status === 'timeout' ? approvals.length : counts.timeout} tone="slate" />
        </div>

        <section className="ops-glass overflow-hidden rounded-3xl border">
          <div className="border-b border-ops-surface0 px-5 py-4">
            <h2 className="text-base font-bold text-ops-text">工具调用审批记录</h2>
            <p className="mt-1 text-xs text-ops-subtext">参数和上下文已由后端脱敏，审批动作会写入审计状态。</p>
          </div>
          <div className="divide-y divide-ops-surface0">
            {loading && <div className="p-8 text-center text-sm text-ops-subtext">正在加载审批队列...</div>}
            {!loading && approvals.length === 0 && (
              <div className="p-10 text-center text-sm text-ops-subtext">当前筛选条件下暂无审批记录</div>
            )}
            {!loading && approvals.map((approval) => (
              <ApprovalRow
                key={approval.id}
                approval={approval}
                busy={busyId === approval.id}
                onApprove={() => void handleDecision(approval, true)}
                onReject={() => void handleDecision(approval, false)}
                onExecute={() => void handleExecute(approval)}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

function ApprovalRow({
  approval,
  busy,
  onApprove,
  onReject,
  onExecute,
}: {
  approval: ApprovalRequest
  busy: boolean
  onApprove: () => void
  onReject: () => void
  onExecute: () => void
}) {
  const argsText = JSON.stringify(approval.args || {}, null, 2)
  const context = approval.context || {}
  const skillChange = approval.metadata?.skill_change
  const skillRollback = approval.metadata?.skill_rollback
  const canExecuteRollback = approval.status === 'approved' && approval.tool_name === 'rollback_skill' && !approval.execution
  return (
    <article className="grid gap-4 p-5 xl:grid-cols-[1fr_360px]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={approval.status} />
          <span className="font-mono text-sm text-ops-accent">{approval.tool_name}</span>
          <span className="text-xs text-ops-overlay">{approval.id}</span>
        </div>
        <p className="mt-3 text-sm text-ops-text">{approval.reason || '命中后端审批策略'}</p>
        {skillChange && (
          <div className="mt-3 rounded-2xl border border-ops-accent/25 bg-ops-accent/5 p-3 text-xs text-ops-subtext">
            <div className="grid gap-2 md:grid-cols-2">
              <Info label="技能" value={skillChange.skill_id || '-'} />
              <Info label="文件" value={skillChange.file_name || '-'} />
              <Info label="行数" value={skillChange.content_lines ?? 0} />
              <Info label="SHA256" value={(skillChange.content_sha256 || '').slice(0, 12) || '-'} />
            </div>
            {skillChange.validation?.issues?.length ? (
              <div className="mt-3 rounded-xl border border-ops-alert/30 bg-ops-alert/10 px-3 py-2 text-ops-alert">
                {skillChange.validation.issues.map((issue) => issue.message).join('；')}
              </div>
            ) : null}
            <pre className="mt-3 max-h-36 overflow-auto whitespace-pre-wrap rounded-xl bg-ops-dark/45 p-3 text-[11px] leading-relaxed">
              {skillChange.content_preview || '无内容预览'}
            </pre>
          </div>
        )}
        {skillRollback && (
          <div className="mt-3 rounded-2xl border border-ops-accent/25 bg-ops-accent/5 p-3 text-xs text-ops-subtext">
            <div className="grid gap-2 md:grid-cols-2">
              <Info label="回滚技能" value={skillRollback.skill_id || '-'} />
              <Info label="目标文件" value={skillRollback.file_name || '-'} />
              <Info label="回滚版本" value={skillRollback.version_id || '-'} />
              <Info label="版本路径" value={skillRollback.version_file || '-'} />
            </div>
          </div>
        )}
        <pre className="mt-3 max-h-44 overflow-auto rounded-2xl border border-ops-surface0 bg-ops-dark/45 p-3 text-xs leading-relaxed text-ops-subtext">
          {argsText}
        </pre>
        {approval.execution && (
          <div className="mt-3 rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-3 text-xs text-ops-subtext">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className={approval.execution.status === 'success' ? 'text-ops-success' : 'text-ops-alert'}>
                执行结果：{approval.execution.status === 'success' ? '成功' : '异常'}
              </span>
              <span className="text-ops-overlay">{approval.execution.completed_at || '-'}</span>
            </div>
            {approval.execution.artifacts && (
              <div className="mb-2 grid gap-2 md:grid-cols-2">
                <Info label="写入文件" value={approval.execution.artifacts.file_path || '-'} />
                <Info label="备份版本" value={approval.execution.artifacts.backup_path || '-'} />
                {approval.execution.artifacts.restored_version_path && (
                  <Info label="恢复版本" value={approval.execution.artifacts.restored_version_path} />
                )}
              </div>
            )}
            <pre className="max-h-28 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed">
              {approval.execution.result_preview || '无执行摘要'}
            </pre>
          </div>
        )}
      </div>
      <aside className="rounded-2xl border border-ops-surface0 bg-ops-dark/30 p-4">
        <div className="space-y-2 text-xs text-ops-subtext">
          <Info label="资产" value={context.remark || context.host || '-'} />
          <Info label="协议" value={`${context.asset_type || '-'} / ${context.protocol || '-'}`} />
          <Info label="会话" value={approval.session_id || '-'} />
          <Info label="申请时间" value={approval.requested_at || '-'} />
          <Info label="处理人" value={approval.operator || '-'} />
        </div>
        {approval.status === 'pending' ? (
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              disabled={busy}
              onClick={onApprove}
              className="rounded-xl bg-ops-success/85 px-3 py-2 text-sm font-semibold text-ops-dark transition-opacity disabled:opacity-50"
            >
              批准
            </button>
            <button
              disabled={busy}
              onClick={onReject}
              className="rounded-xl bg-ops-alert/85 px-3 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
            >
              拒绝
            </button>
          </div>
        ) : canExecuteRollback ? (
          <div className="mt-4 grid gap-2">
            <div className="rounded-xl bg-ops-surface0 px-3 py-2 text-xs text-ops-subtext">
              处理结果：已批准，等待执行
              {approval.note ? `，备注：${approval.note}` : ''}
            </div>
            <button
              disabled={busy}
              onClick={onExecute}
              className="rounded-xl bg-ops-accent px-3 py-2 text-sm font-semibold text-ops-dark transition-opacity disabled:opacity-50"
            >
              执行回滚
            </button>
          </div>
        ) : (
          <div className="mt-4 rounded-xl bg-ops-surface0 px-3 py-2 text-xs text-ops-subtext">
            处理结果：{approval.decision || approval.status}
            {approval.note ? `，备注：${approval.note}` : ''}
          </div>
        )}
      </aside>
    </article>
  )
}

function Metric({ label, value, tone }: { label: string; value: number; tone: 'amber' | 'green' | 'red' | 'slate' }) {
  const toneClass = {
    amber: 'text-ops-accent',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    slate: 'text-ops-subtext',
  }[tone]
  return (
    <div className="ops-glass rounded-2xl border p-4">
      <div className="text-xs text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: ApprovalRequest['status'] }) {
  const label = {
    pending: '待审批',
    approved: '已批准',
    rejected: '已拒绝',
    timeout: '已超时',
  }[status]
  const cls = {
    pending: 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent',
    approved: 'border-ops-success/40 bg-ops-success/10 text-ops-success',
    rejected: 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert',
    timeout: 'border-ops-surface1 bg-ops-surface0 text-ops-subtext',
  }[status]
  return <span className={`rounded-full border px-2.5 py-1 text-[11px] ${cls}`}>{label}</span>
}

function Info({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-ops-overlay">{label}</span>
      <span className="truncate text-right font-mono text-ops-text">{String(value)}</span>
    </div>
  )
}
