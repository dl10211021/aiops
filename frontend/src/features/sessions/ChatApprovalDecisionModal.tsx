import type { Dispatch, SetStateAction } from 'react'
import {
  ChatApprovalContextPanel,
  ChatApprovalDecisionFooter,
  ChatApprovalDecisionForm,
  ChatApprovalDecisionHeader,
} from './ChatApprovalDecisionModalParts'
import { isAutoApproveConfirmationValid } from './approvalConfirmation'
import type { ChatApprovalDecision } from './approvalTypes'

interface ChatApprovalDecisionModalProps {
  decision: ChatApprovalDecision
  onChange: Dispatch<SetStateAction<ChatApprovalDecision | null>>
  onClose: () => void
  onSubmit: () => void
}

export default function ChatApprovalDecisionModal({
  decision,
  onChange,
  onClose,
  onSubmit,
}: ChatApprovalDecisionModalProps) {
  const action = decision.approved ? '批准' : '拒绝'
  const disabled = decision.busy
    || !decision.operator.trim()
    || (decision.approved && !decision.note.trim())
    || (decision.autoAll && !isAutoApproveConfirmationValid(decision.confirmation))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={onClose}>
      <section className="w-full max-w-lg overflow-hidden rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <ChatApprovalDecisionHeader action={action} decision={decision} />
        <div className="space-y-4 p-5">
          <ChatApprovalContextPanel decision={decision} />
          <ChatApprovalDecisionForm decision={decision} onChange={onChange} />
        </div>
        <ChatApprovalDecisionFooter
          action={action}
          decision={decision}
          disabled={disabled}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      </section>
    </div>
  )
}
