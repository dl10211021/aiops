import type { SafetyPolicyAction, SafetyPolicyDecision, ToolApproval } from '@/types'
import { approvalArgumentRows } from './approvalRows'
import type { LatestPolicyBlock, PendingAttention } from './chatAttention'
import { TRACE_RULE_DECISION_LABELS } from './policyDecisions'
import { policyActionTone } from './policyTones'
import ToolApprovalCard from './ToolApprovalCard'
import UserInteractionCard from './UserInteractionCard'
import {
  policyDecisionLabel,
  resultReason,
  traceTargetLabel,
} from './traceUtils'

interface PendingActionDockProps {
  item: PendingAttention
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
  onInteraction: (requestId: string, value: string, label?: string) => void
  sessionMode?: 'readonly' | 'readwrite'
}

export function PendingActionDock({ item, onApproval, onInteraction, sessionMode }: PendingActionDockProps) {
  const source = sessionMode ? 'session_snapshot' : 'inferred_unknown'
  return (
    <div className="mb-3 rounded-lg border border-ops-accent/35 bg-ops-dark/80 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-ops-accent">
            {item.type === 'approval' ? '当前会话需要审批' : '当前会话需要补充输入'}
          </div>
          <div className="mt-0.5 text-[11px] text-ops-subtext">已固定到底部，处理后 AI 会继续当前任务。</div>
        </div>
        <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[11px] text-ops-overlay">待处理</span>
      </div>
      {item.type === 'approval' ? (
        <ToolApprovalCard
          approval={item.approval}
          approvalRows={approvalArgumentRows(item.approval)}
          approvalActions={item.approval.actions || []}
          onApproval={onApproval}
          sessionMode={sessionMode}
          sessionModeSource={source}
        />
      ) : (
        <UserInteractionCard interaction={item.interaction} onSubmit={onInteraction} />
      )}
    </div>
  )
}

interface PolicyBlockDockProps {
  item: LatestPolicyBlock
  onTraceActionRule: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  onDismiss: () => void
  policyRuleBusy?: string | null
}

export function PolicyBlockDock({
  item,
  onTraceActionRule,
  onDismiss,
  policyRuleBusy,
}: PolicyBlockDockProps) {
  const decision = String(item.result?.policy_decision || '')
  const target = traceTargetLabel(item.trace)
  return (
    <div className="mb-3 rounded-lg border border-ops-alert/35 bg-ops-dark/85 p-3 shadow-lg shadow-ops-dark/25">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-ops-alert/45 bg-ops-alert/10 px-2 py-0.5 text-[11px] font-semibold text-ops-alert">
              {policyDecisionLabel(decision)}
            </span>
            <span className={`rounded-full border px-2 py-0.5 text-[11px] ${policyActionTone(item.action.severity)}`}>
              {item.action.label}
            </span>
          </div>
          <div className="mt-2 text-xs font-semibold text-ops-text">刚刚有命令被安全策略拦截</div>
          <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-ops-subtext">{resultReason(item.result)}</div>
          {target && (
            <div className="mt-2 truncate rounded-md border border-ops-surface0 bg-ops-panel/50 px-2 py-1 font-mono text-[11px] text-ops-text">
              {target}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-md border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext hover:text-ops-text"
        >
          收起
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="mr-1 text-[11px] text-ops-overlay">以后遇到这类动作：</span>
        {(['allow', 'approval', 'deny'] as SafetyPolicyDecision[]).map((nextDecision) => {
          const busyKey = `${item.action.id}:${nextDecision}`
          const isBusy = policyRuleBusy === busyKey
          const tone = nextDecision === 'allow'
            ? 'border-ops-success/40 text-ops-success hover:bg-ops-success/10'
            : nextDecision === 'approval'
              ? 'border-yellow-300/35 text-yellow-100 hover:bg-yellow-300/10'
              : 'border-ops-alert/45 text-ops-alert hover:bg-ops-alert/10'
          return (
            <button
              key={nextDecision}
              type="button"
              disabled={Boolean(policyRuleBusy)}
              onClick={() => onTraceActionRule(item.action, nextDecision)}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${tone}`}
            >
              {isBusy ? '保存中' : TRACE_RULE_DECISION_LABELS[nextDecision]}
            </button>
          )
        })}
      </div>
    </div>
  )
}
