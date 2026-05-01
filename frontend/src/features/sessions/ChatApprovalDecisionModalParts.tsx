import type { Dispatch, SetStateAction } from 'react'
import { toolLabel } from '@/utils/assetDisplay'
import { approvalArgumentRows } from './approvalRows'
import type { ChatApprovalDecision } from './approvalTypes'
import { policyActionTone } from './policyTones'

export function ChatApprovalDecisionHeader({
  action,
  decision,
}: {
  action: string
  decision: ChatApprovalDecision
}) {
  return (
    <div className="border-b border-ops-surface0 px-5 py-4">
      <div className={`text-xs font-semibold ${decision.approved ? 'text-ops-success' : 'text-ops-alert'}`}>
        {decision.autoAll ? '本会话自动批准确认' : `${action}敏感工具调用`}
      </div>
      <h2 className="mt-1 text-lg font-bold text-ops-text">{action}执行申请</h2>
      <p className="mt-1 text-sm leading-6 text-ops-subtext">
        处理结果会写入审批审计，并保留在当前聊天记录中。
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span title={decision.approval.toolName} className="rounded-full border border-ops-surface1 bg-ops-dark/55 px-2.5 py-1 text-xs font-semibold text-ops-text">
          {toolLabel(decision.approval.toolName)}
        </span>
        <span className="rounded-full border border-yellow-300/30 bg-yellow-300/10 px-2.5 py-1 text-xs text-yellow-100">
          {decision.approval.primaryAction?.label || '敏感操作'}
        </span>
      </div>
    </div>
  )
}

export function ChatApprovalContextPanel({ decision }: { decision: ChatApprovalDecision }) {
  const approvalRows = approvalArgumentRows(decision.approval)
  const approvalActions = decision.approval.actions || []
  return (
    <>
      {decision.approval.reason && (
        <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/8 px-3 py-2 text-xs leading-5 text-yellow-100">
          {decision.approval.reason}
        </div>
      )}
      {approvalActions.length > 0 && (
        <div className="grid gap-2 md:grid-cols-2">
          {approvalActions.slice(0, 4).map((policyAction) => (
            <div key={policyAction.id} className={`rounded-md border px-3 py-2 ${policyActionTone(policyAction.severity)}`}>
              <div className="text-xs font-semibold">{policyAction.label}</div>
              {policyAction.description && <div className="mt-1 line-clamp-2 text-[11px] leading-4 opacity-85">{policyAction.description}</div>}
            </div>
          ))}
        </div>
      )}
      {approvalRows.length > 0 && (
        <div className="grid gap-2 rounded-lg border border-ops-surface0 bg-ops-dark/25 p-3 md:grid-cols-2">
          {approvalRows.slice(0, 4).map((row) => (
            <div key={row.label} className={row.wide ? 'md:col-span-2' : ''}>
              <div className="text-[11px] text-ops-overlay">{row.label}</div>
              <div className="mt-1 max-h-20 overflow-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-text">
                {row.value}
              </div>
            </div>
          ))}
        </div>
      )}
      {decision.autoAll && (
        <div className="rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-xs leading-5 text-ops-alert">
          自动批准会让本会话后续需要审批的工具调用继续放行。请确认你处于变更窗口，并理解后续操作风险。
        </div>
      )}
    </>
  )
}

export function ChatApprovalDecisionForm({
  decision,
  onChange,
}: {
  decision: ChatApprovalDecision
  onChange: Dispatch<SetStateAction<ChatApprovalDecision | null>>
}) {
  return (
    <>
      <div>
        <label className="text-xs text-ops-subtext">操作人</label>
        <input
          value={decision.operator}
          disabled={decision.busy}
          onChange={(event) => onChange((current) => current ? { ...current, operator: event.target.value } : current)}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-60"
          placeholder="请输入操作人"
        />
      </div>

      <div>
        <label className="text-xs text-ops-subtext">
          {decision.approved ? '批准原因（必填）' : '拒绝原因'}
        </label>
        <textarea
          value={decision.note}
          disabled={decision.busy}
          onChange={(event) => onChange((current) => current ? { ...current, note: event.target.value } : current)}
          rows={4}
          className="mt-1 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-60"
          placeholder={decision.approved ? '例如：已确认变更窗口、影响范围和回滚方案' : '例如：风险不明确、缺少变更单或目标资产不匹配'}
        />
      </div>

      {decision.autoAll && (
        <div>
          <label className="text-xs text-ops-subtext">确认文本</label>
          <input
            value={decision.confirmation}
            disabled={decision.busy}
            onChange={(event) => onChange((current) => current ? { ...current, confirmation: event.target.value } : current)}
            className="mt-1 w-full rounded-lg border border-ops-alert/40 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-alert disabled:opacity-60"
            placeholder="请输入：全部批准"
          />
        </div>
      )}
    </>
  )
}

export function ChatApprovalDecisionFooter({
  action,
  decision,
  disabled,
  onClose,
  onSubmit,
}: {
  action: string
  decision: ChatApprovalDecision
  disabled: boolean
  onClose: () => void
  onSubmit: () => void
}) {
  return (
    <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
      <button onClick={onClose} disabled={decision.busy} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50">
        取消
      </button>
      <button
        onClick={onSubmit}
        disabled={disabled}
        className={`rounded-lg px-4 py-2 text-sm font-semibold transition-opacity disabled:opacity-50 ${
          decision.approved ? 'bg-ops-success text-ops-dark' : 'bg-ops-alert text-white'
        }`}
      >
        {decision.busy ? '提交中...' : `确认${action}`}
      </button>
    </div>
  )
}
