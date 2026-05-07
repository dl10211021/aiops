import SessionGroupList from './SessionGroupList'
import SessionGroupManager from './SessionGroupManager'
import SessionEditModal from './SessionEditModal'
import { useSessionSidebarModel } from './useSessionSidebarModel'

export default function SessionSidebar() {
  const model = useSessionSidebarModel()

  if (!model.sidebarOpen) return null

  return (
    <aside className="ops-command-panel flex min-h-0 flex-col overflow-hidden rounded-[18px] border border-ops-surface1/75 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
      <div className="border-b border-ops-surface1/70 bg-ops-dark/45 p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <span className="block text-[11px] font-black uppercase tracking-[0.22em] text-ops-accent">Session Ops</span>
            <span className="mt-1 block text-base font-black text-ops-text">会话组</span>
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
            className="shrink-0 rounded-xl bg-ops-accent px-3.5 py-2 text-xs font-black text-ops-dark shadow-[0_12px_32px_rgba(40,208,168,0.22)] transition-colors hover:bg-ops-accent/85"
          >
            + 新建
          </button>
        </div>

        <SessionGroupManager
          groupDraft={model.groupDraft}
          onDraftChange={model.setGroupDraft}
          onCreateGroup={model.handleCreateGroup}
        />

        {model.currentSession && (
          <div className="mt-2 rounded-xl border border-ops-surface1/65 bg-ops-dark/30 px-2.5 py-2">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-[11px] font-semibold text-ops-overlay">当前会话</div>
                <div className="truncate text-xs font-black text-ops-text">
                  {model.currentSession.remark || model.currentSession.host}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  type="button"
                  onClick={(event) => model.handleEditSession(model.currentSession!.id, event)}
                  className="rounded-md border border-ops-surface1/75 bg-ops-panel/55 px-2 py-1 text-[11px] font-semibold text-ops-subtext transition-colors hover:border-ops-accent/45 hover:text-ops-text"
                >
                  编辑
                </button>
                <button
                  type="button"
                  onClick={(event) => model.handleDisconnect(model.currentSession!.id, event)}
                  className="rounded-md border border-ops-alert/35 bg-ops-alert/8 px-2 py-1 text-[11px] font-semibold text-ops-alert transition-colors hover:bg-ops-alert/14"
                >
                  断开
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="mt-2">
          <input
            value={model.sessionSearch}
            onChange={(event) => model.setSessionSearch(event.target.value)}
            placeholder="搜索会话组 / 主机 / 协议 / 标签"
            className="h-9 w-full rounded-xl border border-ops-surface1/80 bg-ops-dark/45 px-3 text-xs text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent focus:shadow-[0_0_0_3px_rgba(40,208,168,0.08)]"
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
