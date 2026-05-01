import { useEffect, useState } from 'react'
import { updateHeartbeat, updatePermission } from '@/api/sessions'
import { useStore } from '@/store'
import { assetTypeLabel, protocolLabel } from '@/utils/assetDisplay'
import { readStoredTheme, type OpsTheme } from './topBarModel'

export function useTopBarState() {
  const currentSessionId = useStore((s) => s.currentSessionId)
  const currentView = useStore((s) => s.currentView)
  const sessions = useStore((s) => s.sessions)
  const updateSession = useStore((s) => s.updateSession)
  const openModal = useStore((s) => s.openModal)
  const sidebarOpen = useStore((s) => s.sidebarOpen)
  const setSidebarOpen = useStore((s) => s.setSidebarOpen)
  const addToast = useStore((s) => s.addToast)
  const [theme, setTheme] = useState<OpsTheme>(readStoredTheme)

  const session = currentSessionId ? sessions[currentSessionId] : null
  const isChatView = currentView === 'chat'
  const sessionAssetText = session ? `${assetTypeLabel(session.asset_type)} / ${protocolLabel(session.protocol)}` : ''

  useEffect(() => {
    document.documentElement.dataset.opsTheme = theme
    localStorage.setItem('ops_ui_theme', theme)
  }, [theme])

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const togglePermission = async () => {
    if (!session) return
    try {
      const newMode = !session.isReadWriteMode
      await updatePermission(session.id, newMode)
      updateSession(session.id, { isReadWriteMode: newMode })
      addToast(newMode ? '已切换为读写模式' : '已切换为只读模式', 'info')
    } catch {
      addToast('权限切换失败', 'error')
    }
  }

  const toggleHeartbeat = async () => {
    if (!session) return
    try {
      const newState = !session.heartbeatEnabled
      await updateHeartbeat(session.id, newState)
      updateSession(session.id, { heartbeatEnabled: newState })
      addToast(newState ? '心跳巡检已开启' : '心跳巡检已关闭', 'info')
    } catch {
      addToast('心跳切换失败', 'error')
    }
  }

  return {
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
  }
}
