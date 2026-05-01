import type { ToolApproval } from '@/types'
import {
  ToolApprovalActions,
  ToolApprovalCardHeader,
  ToolApprovalDecisionActions,
  ToolApprovalPayload,
  ToolApprovalReason,
  ToolApprovalResolution,
  getToolApprovalDisplay,
} from './ToolApprovalCardParts'

interface ToolApprovalCardProps {
  approval: ToolApproval
  approvalRows: Array<{ label: string; value: string; wide?: boolean }>
  approvalActions: NonNullable<ToolApproval['actions']>
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
}

export default function ToolApprovalCard({
  approval,
  approvalRows,
  approvalActions,
  onApproval,
}: ToolApprovalCardProps) {
  const { decisionLabel, decisionText, resolvedTone, statusTone } = getToolApprovalDisplay(approval)

  return (
    <div className={`overflow-hidden rounded-lg border ${resolvedTone}`}>
      <ToolApprovalCardHeader
        approval={approval}
        decisionLabel={decisionLabel}
        statusTone={statusTone}
      />

      <div className="space-y-3 px-4 py-3 text-xs text-ops-subtext">
        <ToolApprovalReason reason={approval.reason} />
        <ToolApprovalResolution
          approval={approval}
          decisionLabel={decisionLabel}
          decisionText={decisionText}
        />
        <ToolApprovalActions actions={approvalActions} />
        <ToolApprovalPayload args={approval.args} rows={approvalRows} />
      </div>

      <ToolApprovalDecisionActions approval={approval} onApproval={onApproval} />
    </div>
  )
}
