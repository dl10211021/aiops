import type { ApprovalRequest } from '@/types'
import { assetTypeLabel, protocolLabel, toolLabel } from '@/utils/assetDisplay'
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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={onClose}>
      <section className="w-full max-w-lg rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className={`text-xs font-semibold ${approved ? 'text-ops-success' : 'text-ops-alert'}`}>
            {action}敏感工具调用
          </div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">{toolLabel(approval.tool_name)}</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">{approval.reason || '命中后端审批策略'}</p>
        </div>
        <div className="space-y-4 p-5">
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-3 text-xs text-ops-subtext">
            <div className="grid gap-2">
              <ApprovalInfo label="资产" value={approval.context?.remark || approval.context?.host || '-'} />
              <ApprovalInfo label="协议" value={`${assetTypeLabel(String(approval.context?.asset_type || ''))} / ${protocolLabel(String(approval.context?.protocol || ''))}`} />
              <ApprovalInfo label="会话" value={approval.session_id || '-'} />
            </div>
          </div>
          <div>
            <label className="text-xs text-ops-subtext">操作人</label>
            <input
              value={operator}
              onChange={(event) => onOperatorChange(event.target.value)}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
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
              className="mt-1 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder={approved ? '例如：已确认变更窗口、影响范围和回滚方案' : '例如：风险不明确、缺少变更单或目标资产不匹配'}
            />
          </div>
          {approved && (
            <div className="rounded-lg border border-ops-alert/30 bg-ops-alert/10 px-3 py-2 text-xs leading-5 text-ops-alert">
              批准后工具调用会继续进入执行链；如命中硬拦截规则，后端仍会拒绝执行。
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button onClick={onClose} disabled={busy} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50">
            取消
          </button>
          <button
            onClick={onSubmit}
            disabled={busy || !operator.trim() || (approved && !note.trim())}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition-opacity disabled:opacity-50 ${
              approved ? 'bg-ops-success text-ops-dark' : 'bg-ops-alert text-white'
            }`}
          >
            {busy ? '提交中...' : `确认${action}`}
          </button>
        </div>
      </section>
    </div>
  )
}
