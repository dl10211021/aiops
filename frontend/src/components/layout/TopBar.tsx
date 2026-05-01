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
    <header className="min-h-12 bg-ops-panel/82 border-b border-ops-surface0/80 flex items-center px-3 py-1.5 gap-2 shrink-0 backdrop-blur-xl">
      <SidebarToggle onToggle={toggleSidebar} />

      {session && isChatView ? (
        <>
          <SessionTitle session={session} sessionAssetText={sessionAssetText} />
          <SessionActionButtons
            session={session}
            theme={theme}
            onDynamicSkills={() => openModal('dynamic-skills')}
            onSessionActions={() => openModal('session-actions')}
            onThemeChange={setTheme}
            onToggleHeartbeat={() => void toggleHeartbeat()}
            onTogglePermission={() => void togglePermission()}
          />
        </>
      ) : (
        <>
          <div className="flex min-w-0 items-center gap-3 text-sm">
            <span className="font-semibold text-ops-text">{VIEW_LABELS[currentView] || 'OpsCore'}</span>
            {currentView === 'chat' && <span className="text-sm text-ops-subtext">请选择或新建一个会话</span>}
          </div>
          <div className="flex-1" />
          <ThemeSelector value={theme} onChange={setTheme} />
        </>
      )}
    </header>
  )
}
