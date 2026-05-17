import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
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
  saveSessionGroupToBackend,
  saveSessionMetadataToBackend,
  syncSessionsGroupToBackend,
  syncSessionsPermissionToBackend,
} from './sessionSidebarEffects'

export function useSessionSidebarModel() {
  const sessions = useStore((state) => state.sessions)
  const currentSessionId = useStore((state) => state.currentSessionId)
  const setCurrentSession = useStore((state) => state.setCurrentSession)
  const sessionGroups = useStore((state) => state.sessionGroups)
  const createSessionGroup = useStore((state) => state.createSessionGroup)
  const renameSessionGroup = useStore((state) => state.renameSessionGroup)
  const deleteSessionGroup = useStore((state) => state.deleteSessionGroup)
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
  const [terminalSessionIds, setTerminalSessionIds] = useState<string[]>([])
  const [activeTerminalSessionId, setActiveTerminalSessionId] = useState<string | null>(null)
  const [terminalMinimized, setTerminalMinimized] = useState(false)
  const [editingBusy, setEditingBusy] = useState(false)
  const [multiAgentTargetIds, setMultiAgentTargetIds] = useState<Set<string>>(new Set())
  const deferredSessionSearch = useDeferredValue(sessionSearch)

  const sessionList = useStableSidebarSessionList(sessions)
  const sessionsById = useMemo(() => {
    const rows: Record<string, Session> = {}
    sessionList.forEach((session) => {
      rows[session.id] = session
    })
    return rows
  }, [sessionList])
  const currentSession = currentSessionId ? sessionsById[currentSessionId] || null : null
  const editingSession = editingSessionId ? sessionsById[editingSessionId] || null : null
  const terminalSessions = useMemo(
    () => terminalSessionIds.map((sid) => sessionsById[sid]).filter(Boolean) as Session[],
    [terminalSessionIds, sessionsById],
  )
  const terminalSession = activeTerminalSessionId ? sessionsById[activeTerminalSessionId] || null : null
  const currentSessionGroup = currentSession ? sessionPrimaryGroup(currentSession) : DEFAULT_SESSION_GROUP

  const groupNames = useMemo(() => {
    return sessionGroupNames(sessionGroups, sessionList)
  }, [sessionGroups, sessionList])

  const grouped = useMemo(() => {
    return groupSessionsByPrimaryGroup(sessionList, groupNames)
  }, [groupNames, sessionList])

  const normalizedSessionSearch = deferredSessionSearch.trim().toLowerCase()
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
    // Follow the selected session when the active session changes; operators can
    // still select another group for group-level rename/delete actions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId])

  useEffect(() => {
    if (!groupNames.includes(selectedGroup)) setSelectedGroup(DEFAULT_SESSION_GROUP)
  }, [groupNames, selectedGroup])

  useEffect(() => {
    if (editingSessionId && !sessionsById[editingSessionId]) setEditingSessionId(null)
  }, [editingSessionId, sessionsById])

  useEffect(() => {
    const availableIds = new Set(Object.keys(sessionsById))
    setMultiAgentTargetIds((current) => {
      const next = new Set([...current].filter((sid) => availableIds.has(sid)))
      return next.size === current.size ? current : next
    })
  }, [sessionsById])

  useEffect(() => {
    const availableIds = new Set(Object.keys(sessionsById))
    setTerminalSessionIds((current) => current.filter((sid) => availableIds.has(sid)))
    setActiveTerminalSessionId((current) => {
      if (!current || availableIds.has(current)) return current
      return null
    })
  }, [sessionsById])

  useEffect(() => {
    if (terminalSessionIds.length === 0) {
      if (activeTerminalSessionId !== null) setActiveTerminalSessionId(null)
      if (terminalMinimized) setTerminalMinimized(false)
      return
    }
    if (!activeTerminalSessionId || !terminalSessionIds.includes(activeTerminalSessionId)) {
      setActiveTerminalSessionId(terminalSessionIds[terminalSessionIds.length - 1] || null)
    }
  }, [activeTerminalSessionId, terminalMinimized, terminalSessionIds])

  const sessionMetrics = useMemo(() => summarizeSessions(sessionList), [sessionList])
  const multiAgentTargets = useMemo(
    () => [...multiAgentTargetIds].map((sid) => sessionsById[sid]).filter(Boolean) as Session[],
    [multiAgentTargetIds, sessionsById],
  )
  const multiAgentTargetGroups = useMemo(() => {
    return [...new Set(multiAgentTargets.map((session) => sessionPrimaryGroup(session)))]
  }, [multiAgentTargets])
  const multiAgentDraftScope = multiAgentTargetGroups.length === 1 ? 'group' : 'global'
  const handleDisconnect = useCallback(async (sid: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    await disconnectSidebarSession(sid, removeSession)
  }, [removeSession])

  const handleEditSession = useCallback((sid: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    setEditingSessionId(sid)
  }, [])

  const handleOpenTerminal = useCallback((sid: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    setTerminalSessionIds((current) => (current.includes(sid) ? current : [...current, sid]))
    setActiveTerminalSessionId(sid)
    setTerminalMinimized(false)
  }, [])

  const handleSelectTerminal = useCallback((sid: string) => {
    setActiveTerminalSessionId(sid)
    setTerminalMinimized(false)
  }, [])

  const handleCloseTerminalTab = useCallback((sid: string) => {
    setTerminalSessionIds((current) => {
      const next = current.filter((item) => item !== sid)
      if (next.length === 0) {
        setActiveTerminalSessionId(null)
        setTerminalMinimized(false)
        return next
      }
      setActiveTerminalSessionId((active) => {
        if (active && active !== sid) return active
        const sidIndex = current.indexOf(sid)
        const fallbackIndex = Math.max(0, Math.min(sidIndex, next.length - 1))
        return next[fallbackIndex] || next[next.length - 1]
      })
      return next
    })
  }, [])

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

  const handleRenameGroup = (group: string, nextNameInput: string) => {
    const currentName = normalizeSessionGroupName(group)
    const nextName = normalizeSessionGroupName(nextNameInput)
    if (currentName === DEFAULT_SESSION_GROUP) {
      addToast('默认组不能重命名', 'error')
      return false
    }
    if (!nextName) {
      addToast('请输入新的会话组名称', 'error')
      return false
    }
    if (nextName === currentName) {
      addToast('组名称没有变化', 'info')
      return true
    }
    if (groupNames.includes(nextName) && nextName !== currentName) {
      addToast('目标会话组已存在', 'error')
      return false
    }
    const affected = (grouped[currentName] || []).slice()
    renameSessionGroup(currentName, nextName)
    if (selectedGroup === currentName) setSelectedGroup(nextName)
    void syncSessionsGroupToBackend(affected, nextName, addToast)
    addToast(`已重命名为：${nextName}`, 'success')
    return true
  }

  const handleDeleteGroup = (group: string) => {
    const currentName = normalizeSessionGroupName(group)
    if (currentName === DEFAULT_SESSION_GROUP) {
      addToast('默认组不能删除', 'error')
      return
    }
    const affected = (grouped[currentName] || []).slice()
    deleteSessionGroup(currentName, DEFAULT_SESSION_GROUP)
    if (selectedGroup === currentName) setSelectedGroup(DEFAULT_SESSION_GROUP)
    void syncSessionsGroupToBackend(affected, DEFAULT_SESSION_GROUP, addToast)
    addToast(`已删除会话组：${currentName}`, 'success')
  }

  const handleSetGroupPermission = useCallback((group: string, allowModifications: boolean) => {
    const currentName = normalizeSessionGroupName(group)
    const affected = (grouped[currentName] || []).slice()
    if (affected.length === 0) {
      addToast('该会话组暂无会话', 'info')
      return
    }
    void syncSessionsPermissionToBackend(affected, allowModifications, updateSession, addToast, 'group', currentName)
  }, [addToast, grouped, updateSession])

  const handleSetAllSessionsPermission = useCallback((allowModifications: boolean) => {
    if (sessionList.length === 0) {
      addToast('暂无活跃会话', 'info')
      return
    }
    void syncSessionsPermissionToBackend(sessionList, allowModifications, updateSession, addToast, 'global')
  }, [addToast, sessionList, updateSession])

  const handleToggleMultiAgentTarget = useCallback((sid: string) => {
    setMultiAgentTargetIds((current) => {
      const next = new Set(current)
      if (next.has(sid)) next.delete(sid)
      else next.add(sid)
      return next
    })
  }, [])

  const handleSelectGroupTargets = useCallback((group: string) => {
    const currentName = normalizeSessionGroupName(group)
    const ids = (grouped[currentName] || []).map((session) => session.id)
    setMultiAgentTargetIds(new Set(ids))
    setSelectedGroup(currentName)
    addToast(ids.length > 0 ? `已选择 ${ids.length} 个协同目标` : '该会话组暂无会话', ids.length > 0 ? 'success' : 'info')
  }, [addToast, grouped])

  const handleClearMultiAgentTargets = useCallback(() => {
    setMultiAgentTargetIds(new Set())
  }, [])

  const handleComposeMultiAgentDraft = useCallback(() => {
    if (multiAgentTargets.length === 0) {
      addToast('请先选择协同目标', 'info')
      return
    }
    const activeSessionId = currentSessionId || multiAgentTargets[0]?.id
    if (!activeSessionId) return
    if (!currentSessionId) setCurrentSession(activeSessionId)
    setView('chat')
    const scope = multiAgentDraftScope
    const groupName = scope === 'group' ? multiAgentTargetGroups[0] : ''
    const targetLines = multiAgentTargets.map((session) => (
      `- ${session.id} | ${session.remark || session.host} | ${session.user}@${session.host} | ${session.asset_type}/${session.protocol}`
    ))
    const message = [
      '请按以下目标执行多 Agent 协同任务，先确认任务内容后再调用 dispatch_sub_agents。',
      `dispatch_scope: ${scope}`,
      groupName ? `group_name: ${groupName}` : 'group_name: ',
      'targets:',
      ...targetLines,
      '',
      '任务内容：',
      '<在这里填写要让每个目标执行的排查或操作任务>',
      '',
      '执行要求：',
      '- 对每个目标生成一条 tasks 记录，target_session_id 必须使用上面列出的 ID。',
      '- task_description 使用“任务内容”并结合目标资产信息。',
      '- group 模式必须带 group_name；global 模式不要扩大到未列出的目标。',
    ].join('\n')
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('opscore:chat-draft', {
        detail: { sessionId: activeSessionId, message },
      }))
    }, 0)
    addToast(`已生成 ${multiAgentTargets.length} 个目标的协同指令草稿`, 'success')
  }, [
    addToast,
    currentSessionId,
    multiAgentDraftScope,
    multiAgentTargetGroups,
    multiAgentTargets,
    setCurrentSession,
    setView,
  ])

  const handleSelectSession = useCallback((sessionId: string, group: string) => {
    setCurrentSession(sessionId)
    setView('chat')
    setSelectedGroup(group)
  }, [setCurrentSession, setView])

  const handleSaveSessionEdit = async (values: SessionEditValues) => {
    if (!editingSessionId) return
    const editingSession = sessionsById[editingSessionId]
    if (!editingSession) return
    const groupName = normalizeSessionGroupName(values.groupName)
    if (!groupName) {
      addToast('会话组不能为空', 'error')
      return
    }
    setEditingBusy(true)
    const currentGroup = sessionPrimaryGroup(editingSession)
    const currentRemark = String(editingSession.remark || '').trim()
    const currentTags = (editingSession.tags || [])
      .map((tag) => normalizeSessionGroupName(tag))
      .filter((tag, index) => tag && (index > 0 || tag !== currentGroup))
    const remarkChanged = values.remark !== currentRemark
    const secondaryTagsChanged = !sameStringList(values.tags, currentTags)
    const groupChanged = groupName !== currentGroup
    const saved = !remarkChanged && !secondaryTagsChanged && groupChanged
      ? await saveSessionGroupToBackend({
        addToast,
        groupName,
        sessionId: editingSessionId,
        updateSession,
      })
      : await saveSessionMetadataToBackend({
        addToast,
        groupName,
        remark: values.remark,
        sessionId: editingSessionId,
        tags: values.tags,
        updateSession,
      })
    setEditingBusy(false)
    if (saved) {
      if (!groupNames.includes(saved.group_name)) createSessionGroup(saved.group_name)
      setSelectedGroup(saved.group_name)
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
    handleOpenTerminal,
    handleSelectTerminal,
    handleCloseTerminalTab,
    handleRenameGroup,
    handleSaveSessionEdit,
    handleSelectSession,
    handleSetAllSessionsPermission,
    handleSetGroupPermission,
    handleClearMultiAgentTargets,
    handleComposeMultiAgentDraft,
    handleSelectGroupTargets,
    handleToggleMultiAgentTarget,
    closeSessionEdit: () => setEditingSessionId(null),
    closeTerminal: () => {
      if (!activeTerminalSessionId) return
      handleCloseTerminalTab(activeTerminalSessionId)
    },
    minimizeTerminal: () => setTerminalMinimized(true),
    restoreTerminal: () => setTerminalMinimized(false),
    openConnectModal: () => openModal('connect'),
    allGroupNames: groupNames,
    pendingApprovalCount: sessionMetrics.pendingApproval,
    pendingInputCount: sessionMetrics.pendingInput,
    readonlyCount: sessionMetrics.readonly,
    readwriteCount: sessionMetrics.readwrite,
    runningCount: sessionMetrics.running,
    multiAgentDraftScope,
    multiAgentTargetCount: multiAgentTargets.length,
    multiAgentTargetIds,
    multiAgentTargetGroups,
    selectedGroup,
    sessionList: visibleSessions.sessionList,
    sessionSearch,
    setGroupDraft,
    setSessionSearch,
    setSelectedGroup,
    sidebarOpen,
    activeTerminalSessionId,
    terminalMinimized,
    terminalSessions,
    terminalSession,
    totalSessionCount: sessionList.length,
    toggleGroup,
  }
}

function useStableSidebarSessionList(sessions: Record<string, Session>) {
  const cacheRef = useRef<{ signature: string; list: Session[] } | null>(null)
  return useMemo(() => {
    const list = Object.values(sessions)
    const signature = list.map(sidebarSessionSignature).join('\u001e')
    if (cacheRef.current?.signature === signature) return cacheRef.current.list
    cacheRef.current = { signature, list }
    return list
  }, [sessions])
}

function sidebarSessionSignature(session: Session): string {
  return [
    session.id,
    session.host,
    session.remark,
    session.isReadWriteMode ? 'rw' : 'ro',
    session.user,
    session.asset_type,
    session.protocol,
    session.agentProfile,
    session.heartbeatEnabled ? 'hb1' : 'hb0',
    session.target_scope || '',
    session.scope_value || '',
    session.backendStreaming ? 'bs1' : 'bs0',
    session.isStreaming ? 's1' : 's0',
    session.historyLoaded ? 'h1' : 'h0',
    stableStringList(session.tags),
    stableStringList(session.skills),
  ].join('\u001f')
}

function stableStringList(items: string[] | undefined): string {
  return (items || []).join('\u001d')
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

function sameStringList(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false
  return left.every((item, index) => item === right[index])
}
