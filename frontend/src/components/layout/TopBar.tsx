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
    theme,
    toggleHeartbeat,
    togglePermission,
    toggleSidebar,
  } = useTopBarState()

  return (
    <header className="col-span-2 grid min-h-[52px] grid-cols-[256px_minmax(0,1fr)_auto] items-center gap-3 border-b border-ops-surface0/80 bg-ops-sidebar/92 px-3.5 backdrop-blur-xl">
      <div className="flex min-w-0 items-center gap-2.5 text-left" title="OpsCore AIOps">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-ops-accent/40 bg-ops-accent/12 text-[11px] font-black text-ops-accent">
          OPS
        </span>
        <span className="min-w-0">
          <strong className="block truncate text-sm leading-tight text-ops-text">OpsCore AIOps</strong>
          <span className="block truncate text-[11px] text-ops-overlay">资产 · 会话 · Skills · 安全治理</span>
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
            <span className="hidden truncate text-xs text-ops-subtext md:block">
              {currentView === 'chat' ? '请选择或新建一个会话' : '当前产品功能全部保留，只重组入口和信息层级'}
            </span>
          </div>
          <div className="flex min-w-0 items-center justify-end gap-2">
            <ThemeSelector value={theme} onChange={setTheme} />
            <button
              onClick={() => openModal('safety-policy')}
              className="h-8 rounded-lg border border-ops-surface1/70 bg-ops-surface0/65 px-3 text-xs font-semibold text-ops-subtext hover:border-ops-accent/55 hover:text-ops-text"
            >
              安全
            </button>
            <button
              onClick={() => openModal('connect')}
              className="h-8 rounded-lg bg-ops-accent px-3 text-xs font-bold text-ops-dark hover:bg-ops-accent/85"
            >
              新建会话
            </button>
          </div>
        </>
      )}
    </header>
  )
}
