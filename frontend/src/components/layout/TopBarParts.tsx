import type { Session } from '@/types'
import { THEME_OPTIONS, type OpsTheme } from './topBarModel'

export function SidebarToggle({ onToggle }: { onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-base text-ops-subtext hover:bg-ops-surface0/70 hover:text-ops-text"
      title="切换侧栏"
    >
      ☰
    </button>
  )
}

export function ThemeSelector({
  value,
  onChange,
}: {
  value: OpsTheme
  onChange: (theme: OpsTheme) => void
}) {
  return (
    <label className="hidden h-8 shrink-0 items-center gap-1.5 rounded-full border border-ops-surface1/60 bg-ops-surface0/55 px-2 text-[11px] text-ops-overlay lg:flex">
      <span>主题</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as OpsTheme)}
        className="w-28 bg-transparent text-xs font-semibold text-ops-subtext outline-none"
        title="切换界面主题"
      >
        {THEME_OPTIONS.map((theme) => (
          <option key={theme.id} value={theme.id}>{theme.label}</option>
        ))}
      </select>
    </label>
  )
}

export function SessionTitle({
  session,
  sessionAssetText,
}: {
  session: Session
  sessionAssetText: string
}) {
  return (
    <div className="flex min-w-0 flex-1 items-center gap-2 text-sm">
      <span className={`inline-flex h-2.5 w-2.5 rounded-full ${session.isStreaming ? 'animate-pulse bg-ops-accent' : 'bg-ops-success'}`} />
      <span className="min-w-0 max-w-[16rem] truncate font-semibold text-ops-text">
        {session.remark || session.host}
      </span>
      <span
        title={`${session.user}@${session.host} (${session.asset_type}/${session.protocol})`}
        className="hidden min-w-0 max-w-[24rem] truncate rounded-full border border-ops-surface1/60 bg-ops-dark/45 px-2.5 py-1 text-[11px] text-ops-subtext lg:inline-block"
      >
        {session.user}@{session.host} · {sessionAssetText}
      </span>
      {session.isStreaming && (
        <span className="rounded-full border border-ops-accent/35 bg-ops-accent/10 px-2 py-0.5 text-[11px] font-semibold text-ops-accent">
          执行中
        </span>
      )}
    </div>
  )
}

export function SessionActionButtons({
  session,
  theme,
  onDynamicSkills,
  onSessionActions,
  onThemeChange,
  onToggleHeartbeat,
  onTogglePermission,
}: {
  session: Session
  theme: OpsTheme
  onDynamicSkills: () => void
  onSessionActions: () => void
  onThemeChange: (theme: OpsTheme) => void
  onToggleHeartbeat: () => void
  onTogglePermission: () => void
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
      <ThemeSelector value={theme} onChange={onThemeChange} />

      <button
        onClick={onTogglePermission}
        className={`h-8 rounded-full border px-3 text-xs font-semibold transition-colors ${
          session.isReadWriteMode
            ? 'border-ops-alert/40 bg-ops-alert/15 text-ops-alert'
            : 'border-ops-surface1/60 bg-ops-surface0/60 text-ops-subtext hover:text-ops-text'
        }`}
        title={session.isReadWriteMode ? '当前权限：读写模式' : '当前权限：只读模式'}
      >
        {session.isReadWriteMode ? '读写' : '只读'}
      </button>

      <button
        onClick={onToggleHeartbeat}
        className={`h-8 rounded-full border px-3 text-xs font-semibold transition-colors ${
          session.heartbeatEnabled
            ? 'border-ops-success/40 bg-ops-success/15 text-ops-success'
            : 'border-ops-surface1/60 bg-ops-surface0/60 text-ops-subtext hover:text-ops-text'
        }`}
        title={session.heartbeatEnabled ? '当前巡检：已开启' : '当前巡检：已关闭'}
      >
        巡检{session.heartbeatEnabled ? '开' : '关'}
      </button>

      <button
        onClick={onDynamicSkills}
        className="h-8 rounded-full border border-ops-surface1/60 bg-ops-surface0/60 px-3 text-xs font-semibold text-ops-subtext transition-colors hover:text-ops-text"
        title="管理当前会话技能"
      >
        技能 {session.skills.length}
      </button>

      <button
        onClick={onSessionActions}
        className="grid h-8 w-8 place-items-center rounded-full border border-ops-surface1/60 bg-ops-surface0/60 text-xs font-semibold text-ops-subtext transition-colors hover:text-ops-text"
        title="更多会话操作"
      >
        ...
      </button>
    </div>
  )
}
