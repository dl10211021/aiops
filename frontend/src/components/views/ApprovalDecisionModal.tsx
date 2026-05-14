import type { ApprovalRequest } from '@/types'
import { assetTypeLabel, protocolLabel, toolLabel } from '@/utils/assetDisplay'
import { ApprovalSourceSummary } from '@/features/sessions/ApprovalSourceSummary'
import { ToolPolicyRuntimeGrid } from '@/features/sessions/ToolPolicyRuntimeSummary'
import { ApprovalInfo } from './ApprovalCenterShared'

export function ApprovalDecisionModal({
  approval,
  approved,
  operator,
  note,
  busy,
  onOperatorChange,
  onNoteChange,
  onClose,
  onSubmit,
}: {
  approval: ApprovalRequest
  approved: boolean
  operator: string
  note: string
  busy: boolean
  onOperatorChange: (value: string) => void
  onNoteChange: (value: string) => void
  onClose: () => void
  onSubmit: () => void
}) {
  const action = approved ? '批准' : '拒绝'
  const toolPolicy = approval.metadata?.tool_policy
  return (
    <div className="ops-modal-backdrop" onClick={onClose}>
      <section className="ops-modal-surface w-full max-w-lg" onClick={(event) => event.stopPropagation()}>
        <div className="ops-modal-header block">
          <div className={`text-xs font-semibold ${approved ? 'text-ops-success' : 'text-ops-alert'}`}>
            {action}敏感工具调用
          </div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">{toolLabel(approval.tool_name)}</h2>
        </div>
        <div className="ops-modal-body space-y-4 p-5">
          <ApprovalSourceSummary source={approval.metadata?.approval_source || null} reason={approval.reason} />
          <div className="ops-data-panel p-3 text-xs text-ops-subtext">
            <div className="grid gap-2">
              <ApprovalInfo label="资产" value={approval.context?.remark || approval.context?.host || '-'} />
              <ApprovalInfo label="协议" value={`${assetTypeLabel(String(approval.context?.asset_type || ''))} / ${protocolLabel(String(approval.context?.protocol || ''))}`} />
              <ApprovalInfo label="会话" value={approval.session_id || '-'} />
            </div>
          </div>
          {toolPolicy && <ToolPolicyRuntimeGrid policy={toolPolicy} columns="sm:grid-cols-2" />}
          <div>
            <label className="text-xs text-ops-subtext">操作人</label>
            <input
              value={operator}
              onChange={(event) => onOperatorChange(event.target.value)}
              className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder="请输入操作人"
            />
          </div>
          <div>
            <label className="text-xs text-ops-subtext">
              {approved ? '批准原因（必填）' : '拒绝原因'}
            </label>
            <textarea
              value={note}
              onChange={(event) => onNoteChange(event.target.value)}
              rows={4}
              className="ops-control mt-1 w-full resize-none px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder={approved ? '例如：已确认变更窗口、影响范围和回滚方案' : '例如：风险不明确、缺少变更单或目标资产不匹配'}
            />
          </div>
          {approved && (
            <div className="rounded-lg border border-ops-alert/30 bg-ops-alert/10 px-3 py-2 text-xs leading-5 text-ops-alert">
              批准后工具调用会继续进入执行链；如命中硬拦截规则，后端仍会拒绝执行。
            </div>
          )}
        </div>
        <div className="ops-modal-footer">
          <button onClick={onClose} disabled={busy} className="ops-muted-action px-4 py-2 text-sm disabled:opacity-50">
            取消
          </button>
          <button
            onClick={onSubmit}
            disabled={busy || !operator.trim() || (approved && !note.trim())}
            className={`px-4 py-2 text-sm disabled:opacity-50 ${
              approved ? 'ops-primary-action bg-ops-success' : 'ops-danger-action'
            }`}
          >
            {busy ? '提交中...' : `确认${action}`}
          </button>
        </div>
      </section>
    </div>
  )
}
