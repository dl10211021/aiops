import {
  SessionActionButtons,
  SessionTitle,
  SidebarToggle,
  ThemeSelector,
} from './TopBarParts'
import { VIEW_LABELS } from './topBarModel'
import { useTopBarState } from './useTopBarState'

export default function TopBar() {
  const {
    currentView,
    isChatView,
    openModal,
    session,
    sessionAssetText,
    setTheme,
    setView,
    theme,
    toggleHeartbeat,
    togglePermission,
    toggleSidebar,
  } = useTopBarState()
  const showGlobalActions = currentView !== 'assets' && currentView !== 'config'
  const viewDescription =
    currentView === 'chat'
      ? '请选择或新建一个会话'
      : currentView === 'config'
        ? '管理安全、通知和保留策略等系统级配置'
        : '统一资产、会话、知识和审计工作流'

  return (
    <header className="ops-topbar col-span-2 grid min-h-[56px] grid-cols-[236px_minmax(0,1fr)_auto] items-center gap-3 border-b border-ops-surface0/80 px-3.5 backdrop-blur-xl">
      <div className="flex min-w-0 items-center gap-2.5 text-left" title="OpsCore AIOps">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-ops-accent/40 bg-ops-accent/12 text-[11px] font-black text-ops-accent shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
          OPS
        </span>
        <span className="min-w-0">
          <strong className="block truncate text-sm leading-tight text-ops-text">OpsCore AIOps</strong>
          <span className="block truncate text-[11px] text-ops-overlay">企业 AI 运维控制台</span>
        </span>
      </div>

      {session && isChatView ? (
        <>
          <div className="flex min-w-0 items-center gap-2">
            <SidebarToggle onToggle={toggleSidebar} />
            <SessionTitle session={session} sessionAssetText={sessionAssetText} />
          </div>
          <div className="flex min-w-0 items-center justify-end gap-2">
            <SessionActionButtons
              session={session}
              theme={theme}
              onDynamicSkills={() => openModal('dynamic-skills')}
              onSessionActions={() => openModal('session-actions')}
              onThemeChange={setTheme}
              onToggleHeartbeat={() => void toggleHeartbeat()}
              onTogglePermission={() => void togglePermission()}
            />
          </div>
        </>
      ) : (
        <>
          <div className="flex min-w-0 items-center gap-3 text-sm">
            <span className="font-semibold text-ops-text">{VIEW_LABELS[currentView] || 'OpsCore'}</span>
            <span className="hidden truncate text-xs text-ops-subtext md:block">{viewDescription}</span>
          </div>
          <div className="flex min-w-0 items-center justify-end gap-2">
            <ThemeSelector value={theme} onChange={setTheme} />
            {showGlobalActions && (
              <>
                <button
                  onClick={() => setView('approvals')}
                  className="ops-control h-8 rounded-lg px-3 text-xs font-semibold"
                >
                  审计
                </button>
                <button
                  onClick={() => openModal('connect')}
                  className="ops-control h-8 rounded-lg px-3 text-xs font-semibold"
                >
                  新建资产
                </button>
                <button
                  onClick={() => openModal('connect')}
                  className="ops-primary-action h-8 px-3 text-xs"
                >
                  新建会话
                </button>
              </>
            )}
          </div>
        </>
      )}
    </header>
  )
}
