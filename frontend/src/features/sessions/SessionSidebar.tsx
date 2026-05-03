import SessionGroupList from './SessionGroupList'
import SessionGroupManager from './SessionGroupManager'
import SessionEditModal from './SessionEditModal'
import { useSessionSidebarModel } from './useSessionSidebarModel'

export default function SessionSidebar() {
  const model = useSessionSidebarModel()

  if (!model.sidebarOpen) return null

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-ops-surface1/80 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
      <div className="border-b border-ops-surface1/75 bg-ops-surface0/80 p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <span className="block text-sm font-semibold text-ops-text">会话组</span>
            <span className="text-[11px] text-ops-overlay">
              {model.sessionSearch.trim()
                ? `${model.sessionList.length}/${model.totalSessionCount} 会话`
                : `${model.totalSessionCount} 会话`}
              {model.runningCount > 0 ? ` / ${model.runningCount} 执行中` : ''}
              {model.pendingApprovalCount > 0 ? ` / ${model.pendingApprovalCount} 个待审批` : ''}
              {model.pendingInputCount > 0 ? ` / ${model.pendingInputCount} 个待输入` : ''}
            </span>
          </div>
          <button
            onClick={model.openConnectModal}
            className="shrink-0 rounded-lg bg-ops-accent px-3 py-1.5 text-xs font-bold text-ops-dark transition-colors hover:bg-ops-accent/85"
          >
            + 新建
          </button>
        </div>

        <SessionGroupManager
          groupDraft={model.groupDraft}
          onDraftChange={model.setGroupDraft}
          onCreateGroup={model.handleCreateGroup}
        />

        <div className="mt-2">
          <input
            value={model.sessionSearch}
            onChange={(event) => model.setSessionSearch(event.target.value)}
            placeholder="搜索会话组 / 主机 / 协议 / 标签"
            className="h-8 w-full rounded-md border border-ops-surface1 bg-ops-dark/35 px-2.5 text-xs text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
            aria-label="搜索会话"
          />
        </div>
      </div>

      <SessionGroupList
        collapsedGroups={model.collapsedGroups}
        currentSessionId={model.currentSessionId}
        grouped={model.grouped}
        groupNames={model.groupNames}
        selectedGroup={model.selectedGroup}
        sessionList={model.sessionList}
        onDisconnect={model.handleDisconnect}
        onEdit={model.handleEditSession}
        onDeleteGroup={model.handleDeleteGroup}
        onRenameGroup={model.handleRenameGroup}
        onSelectGroup={model.setSelectedGroup}
        onSelectSession={model.handleSelectSession}
        onToggleGroup={model.toggleGroup}
        searching={Boolean(model.sessionSearch.trim())}
      />

      {model.editingSession && (
        <SessionEditModal
          busy={model.editingBusy}
          groupNames={model.allGroupNames}
          session={model.editingSession}
          onClose={model.closeSessionEdit}
          onSave={model.handleSaveSessionEdit}
        />
      )}
    </aside>
  )
}
