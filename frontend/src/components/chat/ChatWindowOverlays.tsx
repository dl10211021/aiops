import ChatApprovalDecisionModal from '@/features/sessions/ChatApprovalDecisionModal'
import CommandManagerModal from '@/features/sessions/CommandManagerModal'
import MessageEditModal from '@/features/sessions/MessageEditModal'
import ReadWriteConfirmModal from '@/features/sessions/ReadWriteConfirmModal'
import type { useMessageHistoryActions } from '@/features/sessions/useMessageHistoryActions'
import type { useSessionCommands } from '@/features/sessions/useSessionCommands'
import type { useToolApprovalDecision } from '@/features/sessions/useToolApprovalDecision'
import type { Session } from '@/types'

type ReadWriteConfirmation = {
  sessionId: string
  message: string
  remember: boolean
}

export function ChatWindowOverlays({
  commandManager,
  messageHistoryActions,
  readWriteConfirm,
  session,
  toolApprovalDecision,
  onConfirmReadWriteSend,
  onReadWriteConfirmChange,
  onReadWriteConfirmClose,
}: {
  commandManager: ReturnType<typeof useSessionCommands>
  messageHistoryActions: ReturnType<typeof useMessageHistoryActions>
  readWriteConfirm: ReadWriteConfirmation | null
  session: Session
  toolApprovalDecision: ReturnType<typeof useToolApprovalDecision>
  onConfirmReadWriteSend: () => void
  onReadWriteConfirmChange: (confirmation: ReadWriteConfirmation) => void
  onReadWriteConfirmClose: () => void
}) {
  return (
    <>
      {readWriteConfirm && (
        <ReadWriteConfirmModal
          confirmation={readWriteConfirm}
          onRememberChange={(remember) => onReadWriteConfirmChange({ ...readWriteConfirm, remember })}
          onClose={onReadWriteConfirmClose}
          onConfirm={onConfirmReadWriteSend}
        />
      )}
      {toolApprovalDecision.decision && (
        <ChatApprovalDecisionModal
          decision={toolApprovalDecision.decision}
          onChange={toolApprovalDecision.setDecision}
          onClose={toolApprovalDecision.closeDecision}
          onSubmit={toolApprovalDecision.submitDecision}
        />
      )}
      {messageHistoryActions.editingMessage && (
        <MessageEditModal
          message={messageHistoryActions.editingMessage}
          content={messageHistoryActions.editingContent}
          busy={messageHistoryActions.editingBusy}
          onContentChange={messageHistoryActions.setEditingContent}
          onClose={messageHistoryActions.closeEditMessage}
          onSave={() => void messageHistoryActions.saveEditedMessage()}
        />
      )}
      {commandManager.managerOpen && (
        <CommandManagerModal
          session={session}
          commands={commandManager.customCommands}
          availableCommands={commandManager.availableCommands}
          draft={commandManager.draft}
          readonlyDraft={commandManager.readonlyDraft}
          busy={commandManager.busy}
          error={commandManager.error}
          onClose={commandManager.closeManager}
          onDraftChange={commandManager.setDraft}
          onNew={commandManager.newCommand}
          onEdit={commandManager.editCustomCommand}
          onEditBuiltin={commandManager.editBuiltinCommand}
          onViewBuiltin={commandManager.viewBuiltinCommand}
          onCopy={commandManager.copyCommand}
          onBeginEdit={commandManager.beginEdit}
          onRestore={commandManager.restoreBuiltinCommand}
          onRestoreMany={commandManager.restoreBuiltinCommands}
          onSaveOrder={commandManager.saveOrder}
          onSave={commandManager.saveDraft}
          onDelete={commandManager.removeCustomCommand}
        />
      )}
    </>
  )
}
