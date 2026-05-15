import { assetTypeLabel, protocolLabel, toolLabel } from '@/utils/assetDisplay'
import type { ApprovalRequest } from '@/types'
import { ApprovalSourceSummary } from '@/features/sessions/ApprovalSourceSummary'
import { ToolPolicyRuntimeGrid } from '@/features/sessions/ToolPolicyRuntimeSummary'
import { approvalPolicyActionTone } from './approvalDisplay'
import { ApprovalInfo, ApprovalStatusBadge } from './ApprovalCenterShared'

export function ApprovalRow({
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
  const toolPolicy = approval.metadata?.tool_policy
  const policyActions = approval.metadata?.policy?.actions || []
  const primaryAction = approval.metadata?.policy?.primary_action
  const canExecuteRollback = approval.status === 'approved' && approval.tool_name === 'rollback_skill' && !approval.execution
  return (
    <article className="grid gap-4 px-5 py-4 xl:grid-cols-[1fr_340px]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <ApprovalStatusBadge status={approval.status} />
          <span title={approval.tool_name} className="text-sm font-semibold text-ops-accent">{toolLabel(approval.tool_name)}</span>
          {primaryAction && (
            <span className={`rounded-full border px-2.5 py-1 text-[11px] ${approvalPolicyActionTone(primaryAction.severity)}`}>
              {primaryAction.label}
            </span>
          )}
          <span className="text-xs text-ops-overlay">{approval.id}</span>
        </div>
        <div className="mt-3">
          <ApprovalSourceSummary
            source={approval.metadata?.approval_source || null}
            sources={approval.metadata?.approval_sources || null}
            reason={approval.reason}
          />
        </div>
        {toolPolicy && (
          <div className="mt-3">
            <ToolPolicyRuntimeGrid policy={toolPolicy} />
          </div>
        )}
        {policyActions.length > 0 && (
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {policyActions.map((action) => (
              <div key={action.id} className={`rounded-lg border px-3 py-2 text-xs ${approvalPolicyActionTone(action.severity)}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{action.label}</span>
                  <span className="font-mono text-[10px] opacity-75">{action.id}</span>
                </div>
                {action.description && <p className="mt-1 leading-5 opacity-85">{action.description}</p>}
              </div>
            ))}
          </div>
        )}
        {skillChange && (
          <div className="mt-3 rounded-lg border border-ops-accent/25 bg-ops-accent/5 p-3 text-xs text-ops-subtext">
            <div className="grid gap-2 md:grid-cols-2">
              <ApprovalInfo label="技能" value={skillChange.skill_id || '-'} />
              <ApprovalInfo label="文件" value={skillChange.file_name || '-'} />
              <ApprovalInfo label="行数" value={skillChange.content_lines ?? 0} />
              <ApprovalInfo label="SHA256" value={(skillChange.content_sha256 || '').slice(0, 12) || '-'} />
            </div>
            {skillChange.validation?.issues?.length ? (
              <div className="mt-3 rounded-lg border border-ops-alert/30 bg-ops-alert/10 px-3 py-2 text-ops-alert">
                {skillChange.validation.issues.map((issue) => issue.message).join('；')}
              </div>
            ) : null}
            <pre className="mt-3 max-h-36 overflow-auto whitespace-pre-wrap rounded-lg bg-ops-dark/45 p-3 text-[11px] leading-relaxed">
              {skillChange.content_preview || '无内容预览'}
            </pre>
          </div>
        )}
        {skillRollback && (
          <div className="mt-3 rounded-lg border border-ops-accent/25 bg-ops-accent/5 p-3 text-xs text-ops-subtext">
            <div className="grid gap-2 md:grid-cols-2">
              <ApprovalInfo label="回滚技能" value={skillRollback.skill_id || '-'} />
              <ApprovalInfo label="目标文件" value={skillRollback.file_name || '-'} />
              <ApprovalInfo label="回滚版本" value={skillRollback.version_id || '-'} />
              <ApprovalInfo label="版本路径" value={skillRollback.version_file || '-'} />
            </div>
          </div>
        )}
        <pre className="ops-data-panel mt-3 max-h-44 overflow-auto p-3 text-xs leading-relaxed text-ops-subtext">
          {argsText}
        </pre>
        {approval.execution && (
          <div className="ops-data-panel mt-3 p-3 text-xs text-ops-subtext">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className={approval.execution.status === 'success' ? 'text-ops-success' : 'text-ops-alert'}>
                执行结果：{approval.execution.status === 'success' ? '成功' : '异常'}
              </span>
              <span className="text-ops-overlay">{approval.execution.completed_at || '-'}</span>
            </div>
            {approval.execution.artifacts && (
              <div className="mb-2 grid gap-2 md:grid-cols-2">
                <ApprovalInfo label="写入文件" value={approval.execution.artifacts.file_path || '-'} />
                <ApprovalInfo label="备份版本" value={approval.execution.artifacts.backup_path || '-'} />
                {approval.execution.artifacts.restored_version_path && (
                  <ApprovalInfo label="恢复版本" value={approval.execution.artifacts.restored_version_path} />
                )}
              </div>
            )}
            {approval.execution.metadata?.type === 'database_statement' && (
              <div className="mb-2 grid gap-2 md:grid-cols-4">
                <ApprovalInfo label="SQL 类型" value={String(approval.execution.metadata.statement_type || '-').toUpperCase()} />
                <ApprovalInfo label="结果集" value={approval.execution.metadata.has_result_set ? '有' : '无'} />
                <ApprovalInfo label="已提交" value={approval.execution.metadata.committed ? '是' : '否'} />
                <ApprovalInfo
                  label="影响行数"
                  value={approval.execution.metadata.affected_rows !== undefined ? String(approval.execution.metadata.affected_rows) : '-'}
                />
              </div>
            )}
            <pre className="max-h-28 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed">
              {approval.execution.result_preview || '无执行摘要'}
            </pre>
          </div>
        )}
      </div>
      <aside className="ops-data-panel p-4">
        <div className="space-y-2 text-xs text-ops-subtext">
          <ApprovalInfo label="资产" value={context.remark || context.host || '-'} />
          <ApprovalInfo label="协议" value={`${assetTypeLabel(String(context.asset_type || ''))} / ${protocolLabel(String(context.protocol || ''))}`} />
          <ApprovalInfo label="会话" value={approval.session_id || '-'} />
          <ApprovalInfo label="申请时间" value={approval.requested_at || '-'} />
          <ApprovalInfo label="处理人" value={approval.operator || '-'} />
        </div>
        {approval.status === 'pending' ? (
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              disabled={busy}
              onClick={onApprove}
              className="ops-primary-action bg-ops-success px-3 py-2 text-sm disabled:opacity-50"
            >
              批准
            </button>
            <button
              disabled={busy}
              onClick={onReject}
              className="ops-danger-action px-3 py-2 text-sm disabled:opacity-50"
            >
              拒绝
            </button>
          </div>
        ) : canExecuteRollback ? (
          <div className="mt-4 grid gap-2">
            <div className="ops-data-panel px-3 py-2 text-xs text-ops-subtext">
              处理结果：已批准，等待执行
              {approval.note ? `，备注：${approval.note}` : ''}
            </div>
            <button
              disabled={busy}
              onClick={onExecute}
              className="ops-primary-action px-3 py-2 text-sm disabled:opacity-50"
            >
              执行回滚
            </button>
          </div>
        ) : (
          <div className="ops-data-panel mt-4 px-3 py-2 text-xs text-ops-subtext">
            处理结果：{approval.decision || approval.status}
            {approval.note ? `，备注：${approval.note}` : ''}
          </div>
        )}
      </aside>
    </article>
  )
}
