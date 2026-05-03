import { useEffect, useMemo, useState } from 'react'
import type { MouseEvent } from 'react'
import { useStore } from '@/store'
import type { Session } from '@/types'
import type { SessionEditValues } from './SessionEditModal'
import {
  DEFAULT_SESSION_GROUP,
  groupSessionsByPrimaryGroup,
  normalizeSessionGroupName,
  sessionGroupNames,
  sessionPrimaryGroup,
} from './sessionGroups'
import { summarizeSessions } from './sessionMetrics'
import {
  disconnectSidebarSession,
  moveSessionGroupToBackend,
  saveSessionMetadataToBackend,
  syncSessionsGroupToBackend,
} from './sessionSidebarEffects'

export function useSessionSidebarModel() {
  const sessions = useStore((state) => state.sessions)
  const currentSessionId = useStore((state) => state.currentSessionId)
  const setCurrentSession = useStore((state) => state.setCurrentSession)
  const sessionGroups = useStore((state) => state.sessionGroups)
  const createSessionGroup = useStore((state) => state.createSessionGroup)
  const renameSessionGroup = useStore((state) => state.renameSessionGroup)
  const deleteSessionGroup = useStore((state) => state.deleteSessionGroup)
  const moveSessionToGroup = useStore((state) => state.moveSessionToGroup)
  const collapsedGroups = useStore((state) => state.collapsedGroups)
  const toggleGroup = useStore((state) => state.toggleGroup)
  const sidebarOpen = useStore((state) => state.sidebarOpen)
  const openModal = useStore((state) => state.openModal)
  const removeSession = useStore((state) => state.removeSession)
  const setView = useStore((state) => state.setView)
  const updateSession = useStore((state) => state.updateSession)
  const addToast = useStore((state) => state.addToast)
  const [groupDraft, setGroupDraft] = useState('')
  const [sessionSearch, setSessionSearch] = useState('')
  const [selectedGroup, setSelectedGroup] = useState(DEFAULT_SESSION_GROUP)
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingBusy, setEditingBusy] = useState(false)

  const sessionList = useMemo(() => Object.values(sessions), [sessions])
  const currentSession = currentSessionId ? sessions[currentSessionId] : null
  const editingSession = editingSessionId ? sessions[editingSessionId] || null : null
  const currentSessionGroup = currentSession ? sessionPrimaryGroup(currentSession) : DEFAULT_SESSION_GROUP

  const groupNames = useMemo(() => {
    return sessionGroupNames(sessionGroups, sessionList)
  }, [sessionGroups, sessionList])

  const grouped = useMemo(() => {
    return groupSessionsByPrimaryGroup(sessionList, groupNames)
  }, [groupNames, sessionList])

  const normalizedSessionSearch = sessionSearch.trim().toLowerCase()
  const visibleSessions = useMemo(() => {
    if (!normalizedSessionSearch) {
      return { grouped, groupNames, sessionList }
    }

    const nextGrouped: Record<string, Session[]> = {}
    const nextGroupNames: string[] = []
    const visibleIds = new Set<string>()

    for (const group of groupNames) {
      const items = grouped[group] || []
      const groupMatches = normalizeSearchValue(group).includes(normalizedSessionSearch)
      const visibleItems = groupMatches
        ? items
        : items.filter((session) => sessionMatchesSearch(session, group, normalizedSessionSearch))

      if (groupMatches || visibleItems.length > 0) {
        nextGrouped[group] = visibleItems
        nextGroupNames.push(group)
        for (const session of visibleItems) visibleIds.add(session.id)
      }
    }

    return {
      grouped: nextGrouped,
      groupNames: nextGroupNames,
      sessionList: sessionList.filter((session) => visibleIds.has(session.id)),
    }
  }, [groupNames, grouped, normalizedSessionSearch, sessionList])

  useEffect(() => {
    if (currentSession) setSelectedGroup(currentSessionGroup)
    // Only follow the selected session when the session changes; afterwards the
    // operator can select a different target group for "move current".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId])

  useEffect(() => {
    if (!groupNames.includes(selectedGroup)) setSelectedGroup(DEFAULT_SESSION_GROUP)
  }, [groupNames, selectedGroup])

  useEffect(() => {
    if (editingSessionId && !sessions[editingSessionId]) setEditingSessionId(null)
  }, [editingSessionId, sessions])

  const sessionMetrics = useMemo(() => summarizeSessions(sessionList), [sessionList])
  const selectedGroupSessions = grouped[selectedGroup] || []
  const selectedIsDefault = selectedGroup === DEFAULT_SESSION_GROUP

  const handleDisconnect = async (sid: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    await disconnectSidebarSession(sid, removeSession)
  }

  const handleEditSession = (sid: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    setEditingSessionId(sid)
  }

  const handleCreateGroup = () => {
    const name = normalizeSessionGroupName(groupDraft)
    if (!name) {
      addToast('请输入会话组名称', 'error')
      return
    }
    if (groupNames.includes(name)) {
      addToast('会话组已存在', 'info')
      setSelectedGroup(name)
      return
    }
    createSessionGroup(name)
    setSelectedGroup(name)
    setGroupDraft('')
    addToast(`已创建会话组：${name}`, 'success')
  }

  const handleRenameGroup = () => {
    const nextName = normalizeSessionGroupName(groupDraft)
    if (selectedIsDefault) {
      addToast('默认组不能重命名', 'error')
      return
    }
    if (!nextName) {
      addToast('请输入新的会话组名称', 'error')
      return
    }
    if (groupNames.includes(nextName) && nextName !== selectedGroup) {
      addToast('目标会话组已存在', 'error')
      return
    }
    const affected = selectedGroupSessions.slice()
    renameSessionGroup(selectedGroup, nextName)
    setSelectedGroup(nextName)
    setGroupDraft('')
    void syncSessionsGroupToBackend(affected, nextName, addToast)
    addToast(`已重命名为：${nextName}`, 'success')
  }

  const handleDeleteGroup = () => {
    if (selectedIsDefault) {
      addToast('默认组不能删除', 'error')
      return
    }
    const affected = selectedGroupSessions.slice()
    deleteSessionGroup(selectedGroup, DEFAULT_SESSION_GROUP)
    setSelectedGroup(DEFAULT_SESSION_GROUP)
    setGroupDraft('')
    void syncSessionsGroupToBackend(affected, DEFAULT_SESSION_GROUP, addToast)
    addToast(`已删除会话组：${selectedGroup}`, 'success')
  }

  const handleMoveCurrentSession = async () => {
    if (!currentSession || !currentSessionId) {
      addToast('请先选择一个会话', 'error')
      return
    }
    await moveSessionGroupToBackend({
      addToast,
      groupName: selectedGroup,
      moveSessionToGroup,
      sessionId: currentSessionId,
    })
  }

  const handleSelectSession = (sessionId: string, group: string) => {
    setCurrentSession(sessionId)
    setView('chat')
    setSelectedGroup(group)
  }

  const handleSaveSessionEdit = async (values: SessionEditValues) => {
    if (!editingSessionId) return
    setEditingBusy(true)
    const saved = await saveSessionMetadataToBackend({
      addToast,
      groupName: values.groupName,
      remark: values.remark,
      sessionId: editingSessionId,
      tags: values.tags,
      updateSession,
    })
    setEditingBusy(false)
    if (saved) {
      setSelectedGroup(values.groupName)
      setEditingSessionId(null)
    }
  }

  return {
    collapsedGroups,
    currentSession,
    currentSessionId,
    editingBusy,
    editingSession,
    groupDraft,
    grouped: visibleSessions.grouped,
    groupNames: visibleSessions.groupNames,
    handleCreateGroup,
    handleDeleteGroup,
    handleDisconnect,
    handleEditSession,
    handleMoveCurrentSession,
    handleRenameGroup,
    handleSaveSessionEdit,
    handleSelectSession,
    closeSessionEdit: () => setEditingSessionId(null),
    openConnectModal: () => openModal('connect'),
    allGroupNames: groupNames,
    pendingApprovalCount: sessionMetrics.pendingApproval,
    pendingInputCount: sessionMetrics.pendingInput,
    runningCount: sessionMetrics.running,
    selectedGroup,
    sessionList: visibleSessions.sessionList,
    sessionSearch,
    setGroupDraft,
    setSessionSearch,
    setSelectedGroup,
    sidebarOpen,
    totalSessionCount: sessionList.length,
    toggleGroup,
  }
}

function normalizeSearchValue(value: unknown): string {
  return String(value ?? '').trim().toLowerCase()
}

function sessionMatchesSearch(session: Session, group: string, query: string): boolean {
  const fields = [
    group,
    session.remark,
    session.host,
    session.user,
    session.asset_type,
    session.protocol,
    session.agentProfile,
    ...(session.tags || []),
    ...(session.skills || []),
  ]
  return fields.some((field) => normalizeSearchValue(field).includes(query))
}
