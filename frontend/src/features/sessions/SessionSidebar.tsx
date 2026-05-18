import { lazy, Suspense, useEffect, useRef, useState, useTransition } from 'react'
import SessionGroupList from './SessionGroupList'
import SessionGroupManager from './SessionGroupManager'
import SessionEditModal from './SessionEditModal'
import { useSessionSidebarModel } from './useSessionSidebarModel'

const SessionTerminalModal = lazy(() => import('./SessionTerminalModal'))

export default function SessionSidebar() {
  const model = useSessionSidebarModel()

  if (!model.sidebarOpen) return null

  return (
    <aside className="ops-command-panel ops-session-sidebar flex min-h-0 flex-col overflow-hidden rounded-[18px] border border-ops-surface1/75 bg-ops-panel shadow-[var(--ops-panel-shadow)]">
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
            {model.terminalMinimized && model.terminalSession && (
              <button
                type="button"
                onClick={model.restoreTerminal}
                className="mt-1 inline-flex items-center gap-1 rounded-lg border border-ops-accent/35 bg-ops-accent/10 px-2 py-1 text-[11px] font-semibold text-ops-accent transition-colors hover:bg-ops-accent/15"
                title="还原最小化终端"
              >
                终端已最小化 ({model.terminalSessions.length})
              </button>
            )}
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

        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => model.handleSetAllSessionsPermission(false)}
            className="h-8 rounded-lg border border-amber-400/35 bg-amber-400/8 px-2 text-[11px] font-semibold text-amber-100 transition-colors hover:bg-amber-400/14"
            title="将全部活跃会话切换为只读"
          >
            全部只读
          </button>
          <button
            type="button"
            onClick={() => model.handleSetAllSessionsPermission(true)}
            className="h-8 rounded-lg border border-ops-success/35 bg-ops-success/8 px-2 text-[11px] font-semibold text-ops-success transition-colors hover:bg-ops-success/14"
            title="将全部活跃会话切换为读写"
          >
            全部读写
          </button>
        </div>
        <PermissionScopePreview
          label="全局影响"
          total={model.totalSessionCount}
          readonly={model.readonlyCount}
          readwrite={model.readwriteCount}
        />
        <MultiAgentTargetBar
          count={model.multiAgentTargetCount}
          scope={model.multiAgentDraftScope}
          groups={model.multiAgentTargetGroups}
          readonlyCount={model.multiAgentTargetReadonlyCount}
          readwriteCount={model.multiAgentTargetReadwriteCount}
          onCompose={model.handleComposeMultiAgentDraft}
          onClear={model.handleClearMultiAgentTargets}
        />

        <div className="mt-2">
          <SessionSearchBox
            value={model.sessionSearch}
            onChange={model.setSessionSearch}
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
        onOpenTerminal={model.handleOpenTerminal}
        onDeleteGroup={model.handleDeleteGroup}
        onRenameGroup={model.handleRenameGroup}
        onSelectGroup={model.setSelectedGroup}
        onSelectGroupTargets={model.handleSelectGroupTargets}
        onSelectSession={model.handleSelectSession}
        onSetGroupPermission={model.handleSetGroupPermission}
        onToggleMultiAgentTarget={model.handleToggleMultiAgentTarget}
        onToggleGroup={model.toggleGroup}
        multiAgentTargetIds={model.multiAgentTargetIds}
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

      {model.terminalSession && !model.terminalMinimized && (
        <Suspense fallback={<TerminalModalFallback />}>
          <SessionTerminalModal
            sessions={model.terminalSessions}
            activeSessionId={model.activeTerminalSessionId || model.terminalSession.id}
            onSelectSession={model.handleSelectTerminal}
            onCloseSession={model.handleCloseTerminalTab}
            onClose={model.closeTerminal}
            onMinimize={model.minimizeTerminal}
          />
        </Suspense>
      )}

      {model.terminalSession && model.terminalMinimized && (
        <div className="fixed bottom-4 right-4 z-[93] flex items-center gap-2 rounded-xl border border-ops-surface1/80 bg-ops-panel/95 px-3 py-2 shadow-[0_16px_50px_rgba(0,0,0,0.45)] backdrop-blur-sm">
          <div className="min-w-0">
            <div className="text-[11px] font-semibold text-ops-text">SSH Terminal</div>
            <div className="max-w-[220px] truncate text-[10px] text-ops-overlay">
              {model.terminalSession.user}@{model.terminalSession.host}
            </div>
            <div className="text-[10px] text-ops-overlay/80">{model.terminalSessions.length} 个终端</div>
          </div>
          <button
            type="button"
            onClick={model.restoreTerminal}
            className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-2 py-1 text-xs text-ops-subtext transition-colors hover:text-ops-text"
          >
            还原
          </button>
          <button
            type="button"
            onClick={model.closeTerminal}
            className="rounded-md px-2 py-1 text-xs text-ops-overlay transition-colors hover:bg-ops-surface0 hover:text-ops-text"
          >
            关闭当前
          </button>
        </div>
      )}
    </aside>
  )
}

function MultiAgentTargetBar({
  count,
  scope,
  groups,
  readonlyCount,
  readwriteCount,
  onCompose,
  onClear,
}: {
  count: number
  scope: string
  groups: string[]
  readonlyCount: number
  readwriteCount: number
  onCompose: () => void
  onClear: () => void
}) {
  if (count <= 0) return null
  const scopeText = scope === 'group' ? `分组 ${groups[0] || ''}` : '全局'
  return (
    <div className="mt-1.5 grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-1.5 rounded-lg border border-ops-accent/30 bg-ops-accent/8 px-2 py-1 text-[10px] text-ops-subtext">
      <span className="truncate" title={`已选 ${count} 个多 Agent 目标，范围：${scopeText}`}>
        已选 {count} 个目标 · {scopeText}
        <span className="ml-1 text-ops-overlay">权限：只读 {readonlyCount} / 读写 {readwriteCount}</span>
      </span>
      <button
        type="button"
        onClick={onCompose}
        className="rounded-md border border-ops-accent/40 bg-ops-accent/12 px-1.5 py-0.5 font-semibold text-ops-accent transition-colors hover:bg-ops-accent/18"
        title="生成多 Agent 协同指令草稿"
      >
        生成指令
      </button>
      <button
        type="button"
        onClick={onClear}
        className="rounded-md border border-ops-surface1/65 bg-ops-dark/35 px-1.5 py-0.5 font-semibold text-ops-overlay transition-colors hover:text-ops-text"
        title="清空多 Agent 目标"
      >
        清空
      </button>
    </div>
  )
}

function PermissionScopePreview({
  label,
  total,
  readonly,
  readwrite,
}: {
  label: string
  total: number
  readonly: number
  readwrite: number
}) {
  if (total <= 0) return null
  return (
    <div
      className="mt-1.5 flex flex-wrap items-center gap-1.5 rounded-lg border border-ops-surface1/60 bg-ops-dark/28 px-2 py-1 text-[10px] text-ops-overlay"
      title={`将影响 ${total} 个会话：只读 ${readonly}，读写 ${readwrite}`}
    >
      <span className="font-semibold text-ops-subtext">{label}</span>
      <span className="rounded-md bg-ops-surface0/65 px-1.5 py-0.5">{total} 个</span>
      <span className="rounded-md bg-amber-400/8 px-1.5 py-0.5 text-amber-100">只读 {readonly}</span>
      <span className="rounded-md bg-ops-success/8 px-1.5 py-0.5 text-ops-success">读写 {readwrite}</span>
    </div>
  )
}

function TerminalModalFallback() {
  return (
    <div className="fixed inset-0 z-[92] flex items-center justify-center bg-black/55 text-sm text-ops-subtext">
      <div className="rounded-xl border border-ops-surface1/80 bg-ops-panel/95 px-4 py-3 shadow-[0_16px_50px_rgba(0,0,0,0.45)]">
        正在加载终端...
      </div>
    </div>
  )
}

function SessionSearchBox({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  const [draft, setDraft] = useState(value)
  const [, startTransition] = useTransition()
  const onChangeRef = useRef(onChange)

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    setDraft(value)
  }, [value])

  useEffect(() => {
    if (draft === value) return
    const timer = window.setTimeout(() => {
      startTransition(() => onChangeRef.current(draft))
    }, 180)
    return () => window.clearTimeout(timer)
  }, [draft, startTransition, value])

  return (
    <input
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        if (draft !== value) startTransition(() => onChangeRef.current(draft))
      }}
      placeholder="搜索会话组 / 主机 / 协议 / 标签"
      className="h-9 w-full rounded-xl border border-ops-surface1/80 bg-ops-dark/45 px-3 text-xs text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent focus:shadow-[0_0_0_3px_rgba(40,208,168,0.08)]"
      aria-label="搜索会话"
    />
  )
}
