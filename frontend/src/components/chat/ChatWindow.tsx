import { useRef, useEffect, useState } from 'react'
import { useStore } from '@/store'
import { streamChat, stopChat, approveToolCall, respondUserInteraction, getSafetyPolicy, getAvailableModels, getSessionTools, getSessionCommands } from '@/api/client'
import type { ModelGroup } from '@/api/client'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChatMessage, ExecTraceItem, Session, SessionToolCatalog, ToolApproval, ToolsetInfo, UserInteractionRequest } from '@/types'

// Configure marked for async
marked.setOptions({ breaks: true, gfm: true })

function renderMarkdown(md: string): string {
  const raw = marked.parse(md)
  // marked.parse may return string | Promise<string>, handle both
  if (typeof raw === 'string') return DOMPurify.sanitize(raw)
  return ''
}

export default function ChatWindow() {
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)
  const appendMessage = useStore((s) => s.appendMessage)
  const updateLastAssistantMessage = useStore((s) => s.updateLastAssistantMessage)
  const updateSession = useStore((s) => s.updateSession)
  const chatController = useStore((s) => s.chatController)
  const setChatController = useStore((s) => s.setChatController)
  const addToast = useStore((s) => s.addToast)

  const [input, setInput] = useState('')
  const [modelName, setModelName] = useState(() => {
    const stored = localStorage.getItem('ops_model');
    if (stored) {
      if (!stored.includes('|') && stored.includes('gemini')) return `google|${stored}`;
      if (!stored.includes('|') && stored.includes('claude')) return `anthropic|${stored}`;
      if (!stored.includes('|') && stored.includes('deepseek')) return `deepseek|${stored}`;
      return stored;
    }
    return '';
  })
  const [thinkingMode, setThinkingMode] = useState(() =>
    localStorage.getItem('ops_thinking') || 'off'
  )
  const [availableModels, setAvailableModels] = useState<ModelGroup[]>([])
  const [readWriteWarningEnabled, setReadWriteWarningEnabled] = useState(true)
  const [readWriteConfirm, setReadWriteConfirm] = useState<{ message: string; remember: boolean } | null>(null)
  const [toolCatalog, setToolCatalog] = useState<SessionToolCatalog | null>(null)
  const [backendCommands, setBackendCommands] = useState<Array<{ id: string; label: string; description: string; prompt: string }>>([])
  const [inputHistory, setInputHistory] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('ops_chat_input_history')
      const parsed = stored ? JSON.parse(stored) : []
      return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
    } catch {
      return []
    }
  })
  const [historyIndex, setHistoryIndex] = useState<number | null>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const session = currentSessionId ? sessions[currentSessionId] : null
  const messages = session?.messages || []
  const isStreaming = session?.isStreaming || false
  const slashCommands = backendCommands.length > 0 ? backendCommands : (session ? buildSlashCommands(session, toolCatalog) : [])
  const slashQuery = input.startsWith('/') ? input.slice(1).toLowerCase() : ''
  const visibleSlashCommands = input.startsWith('/')
    ? slashCommands.filter((cmd) => cmd.id.includes(slashQuery) || cmd.label.toLowerCase().includes(slashQuery)).slice(0, 6)
    : []

  // Scroll to bottom on new messages
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }, [messages])

  // Load available models once
  useEffect(() => {
    getAvailableModels().then((r) => {
      const groups = r.data.models || []
      setAvailableModels(groups)
      const validIds = groups.flatMap((g) => g.models.map((m) => m.id))
      const firstValid = validIds.find((id) => !id.endsWith('|none')) || validIds[0] || ''
      setModelName((current) => {
        if (current && validIds.includes(current)) return current
        return firstValid || current
      })
    }).catch(() => {})
    getSafetyPolicy()
      .then((r) => setReadWriteWarningEnabled(r.data.policy.readwrite_chat_warning_enabled))
      .catch(() => {})
  }, [])

  // Save model to localStorage
  useEffect(() => {
    if (modelName) localStorage.setItem('ops_model', modelName)
  }, [modelName])

  useEffect(() => {
    localStorage.setItem('ops_thinking', thinkingMode)
  }, [thinkingMode])

  useEffect(() => {
    localStorage.setItem('ops_chat_input_history', JSON.stringify(inputHistory.slice(0, 20)))
  }, [inputHistory])

  useEffect(() => {
    if (!currentSessionId) {
      setToolCatalog(null)
      return
    }
    let cancelled = false
    getSessionTools(currentSessionId)
      .then((r) => {
        if (!cancelled) setToolCatalog(r.data)
      })
      .catch(() => {
        if (!cancelled) setToolCatalog(null)
      })
    getSessionCommands(currentSessionId)
      .then((r) => {
        if (!cancelled) setBackendCommands(r.data.commands || [])
      })
      .catch(() => {
        if (!cancelled) setBackendCommands([])
      })
    return () => {
      cancelled = true
    }
  }, [currentSessionId, session?.asset_type, session?.protocol])

  const sendMessage = async (forcedMessage?: string) => {
    const text = (forcedMessage ?? input).trim()
    if (!text || !currentSessionId || isStreaming) return

    if (!forcedMessage && session?.isReadWriteMode && readWriteWarningEnabled) {
      const ackKey = `opscore_rw_confirmed_${currentSessionId}`
      if (sessionStorage.getItem(ackKey) !== '1') {
        setReadWriteConfirm({ message: text, remember: false })
        return
      }
    }

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    setInputHistory((prev) => [text, ...prev.filter((item) => item !== text)].slice(0, 20))
    setHistoryIndex(null)
    appendMessage(currentSessionId, userMsg)
    setInput('')

    // Create assistant skeleton
    const assistantMsg: ChatMessage = {
      id: `a-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      execTrace: [],
    }
    appendMessage(currentSessionId, assistantMsg)
    updateSession(currentSessionId, { isStreaming: true })

    const controller = new AbortController()
    setChatController(controller)

    let accumulatedMd = ''

    try {
      const response = await streamChat(currentSessionId, userMsg.content, modelName, thinkingMode, controller.signal)
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP Error ${response.status}: ${response.statusText}`);
      }
      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const data = JSON.parse(jsonStr)
            const sid = currentSessionId // capture

            switch (data.type) {
              case 'status':
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  execTrace: [...(m.execTrace || []), {
                    type: 'tool_start', tool: '🔄 ' + data.content, args: '',
                  } as ExecTraceItem],
                }))
                break

              case 'tool_start':
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  execTrace: [...(m.execTrace || []), {
                    type: 'tool_start',
                    tool: data.tool || 'unknown',
                    args: typeof data.args === 'string' ? data.args : JSON.stringify(data.args || {}),
                    status: 'running',
                    startedAt: Date.now(),
                  } as ExecTraceItem],
                }))
                break

              case 'tool_end':
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  execTrace: completeLastTrace(m.execTrace || [], data),
                }))
                break

              case 'tool_ask_approval': {
                const approval: ToolApproval = {
                  toolCallId: data.tool_call_id,
                  toolName: data.tool_name || 'unknown',
                  args: typeof data.args === 'string' ? data.args : JSON.stringify(data.args || {}),
                  reason: data.reason || '',
                  uniqueId: `approval-${Date.now()}`,
                  resolved: false,
                }
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  toolApproval: approval,
                }))
                break
              }

              case 'user_interaction_request': {
                const options = Array.isArray(data.options)
                  ? data.options
                    .filter((item: unknown) => item && typeof item === 'object')
                    .map((item: Record<string, unknown>) => ({
                      label: String(item.label || item.value || '选项'),
                      value: String(item.value || item.label || ''),
                      description: item.description ? String(item.description) : undefined,
                    }))
                  : []
                const interaction: UserInteractionRequest = {
                  requestId: String(data.request_id || ''),
                  prompt: String(data.prompt || '请补充信息'),
                  inputType: String(data.input_type || 'text'),
                  options,
                  placeholder: String(data.placeholder || ''),
                  required: data.required !== false,
                  timeoutSeconds: Number(data.timeout_seconds || 300),
                  resolved: false,
                }
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  userInteraction: interaction,
                }))
                break
              }

              case 'chunk':
                accumulatedMd += data.content || ''
                updateLastAssistantMessage(sid, (m) => ({
                  ...m, content: accumulatedMd,
                }))
                break

              case 'error':
                updateLastAssistantMessage(sid, (m) => ({
                  ...m, content: m.content + '\n\n❌ ' + (data.content || 'Unknown error'),
                }))
                break

              case 'done':
                break
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        updateLastAssistantMessage(currentSessionId, (m) => ({
          ...m, content: m.content + '\n\n⏹️ 已中止',
        }))
      } else {
        const errMsg = err instanceof Error ? err.message : 'Network error'
        addToast(errMsg, 'error')
        updateLastAssistantMessage(currentSessionId, (m) => ({
          ...m, content: m.content || `\n\n❌ 消息发送失败: ${errMsg}`,
        }))
      }
    } finally {
      updateSession(currentSessionId, { isStreaming: false })
      setChatController(null)
    }
  }

  const handleUserInteraction = async (requestId: string, value: string, label = '') => {
    if (!currentSessionId) return
    try {
      await respondUserInteraction(currentSessionId, requestId, value, label)
      updateLastAssistantMessage(currentSessionId, (m) => {
        const interaction = m.userInteraction
        const displayValue = interaction?.inputType === 'password' && value ? '******' : value
        return {
          ...m,
          userInteraction: interaction
            ? { ...interaction, resolved: true, value: displayValue, label }
            : undefined,
        }
      })
    } catch {
      addToast('交互输入提交失败，可能已超时', 'error')
    }
  }

  const handleStop = async () => {
    chatController?.abort()
    if (currentSessionId) {
      try { await stopChat(currentSessionId) } catch { /* ignore */ }
      updateSession(currentSessionId, { isStreaming: false })
    }
    setChatController(null)
  }

  const handleApproval = async (toolCallId: string, approved: boolean, autoAll = false) => {
    if (!currentSessionId) return
    const action = approved ? '批准' : '拒绝'
    if (autoAll) {
      const confirmation = window.prompt('高风险操作：请输入“全部批准”以确认本会话后续高危工具自动放行。', '')
      if (confirmation !== '全部批准') {
        addToast('已取消全部批准', 'error')
        return
      }
    } else if (!window.confirm(`确认${action}本次敏感工具调用？`)) {
      return
    }
    const operator = window.prompt('请输入操作人', localStorage.getItem('OPSCORE_OPERATOR') || 'user') || ''
    if (!operator.trim()) {
      addToast('操作人不能为空', 'error')
      return
    }
    localStorage.setItem('OPSCORE_OPERATOR', operator.trim())
    const note = window.prompt(`请输入${action}原因`, autoAll ? '本会话后续同类工具调用由人工确认全部放行' : '') || ''
    if (approved && !note.trim()) {
      addToast('批准敏感操作必须填写原因', 'error')
      return
    }
    try {
      await approveToolCall(currentSessionId, toolCallId, approved, autoAll, operator.trim(), note.trim())
      updateLastAssistantMessage(currentSessionId, (m) => ({
        ...m, toolApproval: m.toolApproval ? { ...m.toolApproval, resolved: true } : undefined,
      }))
    } catch {
      addToast('审批提交失败', 'error')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'ArrowUp' && inputHistory.length > 0 && !e.shiftKey) {
      const atStart = e.currentTarget.selectionStart === 0
      if (!input.trim() || atStart) {
        e.preventDefault()
        const nextIndex = historyIndex === null ? 0 : Math.min(historyIndex + 1, inputHistory.length - 1)
        setHistoryIndex(nextIndex)
        setInput(inputHistory[nextIndex])
        requestAnimationFrame(() => {
          const el = textareaRef.current
          if (el) el.selectionStart = el.selectionEnd = el.value.length
        })
        return
      }
    }

    if (e.key === 'ArrowDown' && inputHistory.length > 0 && !e.shiftKey) {
      const atEnd = e.currentTarget.selectionStart === input.length
      if (historyIndex !== null && atEnd) {
        e.preventDefault()
        const nextIndex = historyIndex - 1
        if (nextIndex < 0) {
          setHistoryIndex(null)
          setInput('')
          return
        }
        setHistoryIndex(nextIndex)
        setInput(inputHistory[nextIndex])
        requestAnimationFrame(() => {
          const el = textareaRef.current
          if (el) el.selectionStart = el.selectionEnd = el.value.length
        })
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const confirmReadWriteSend = () => {
    if (!readWriteConfirm || !currentSessionId) return
    if (readWriteConfirm.remember) {
      sessionStorage.setItem(`opscore_rw_confirmed_${currentSessionId}`, '1')
    }
    const message = readWriteConfirm.message
    setReadWriteConfirm(null)
    void sendMessage(message)
  }

  const applySlashCommand = (prompt: string) => {
    setInput(prompt)
    setHistoryIndex(null)
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  const pickHistory = (direction: 'prev' | 'next') => {
    if (inputHistory.length === 0) return
    if (direction === 'prev') {
      const nextIndex = historyIndex === null ? 0 : Math.min(historyIndex + 1, inputHistory.length - 1)
      setHistoryIndex(nextIndex)
      setInput(inputHistory[nextIndex])
    } else {
      if (historyIndex === null) return
      const nextIndex = historyIndex - 1
      if (nextIndex < 0) {
        setHistoryIndex(null)
        setInput('')
      } else {
        setHistoryIndex(nextIndex)
        setInput(inputHistory[nextIndex])
      }
    }
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  if (!session) {
    return (
      <div className="flex-1 flex items-center justify-center text-ops-subtext">
        <div className="text-center">
          <div className="text-5xl mb-4">⚡</div>
          <h2 className="text-xl font-semibold text-ops-text mb-2">SkillOps AIOps Platform</h2>
          <p className="text-sm">选择一个已有会话或新建连接开始工作</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0">
      {readWriteConfirm && (
        <div className="fixed inset-0 bg-black/50 z-30 flex items-center justify-center">
          <div className="bg-ops-panel border border-ops-alert/40 rounded-xl p-5 w-[460px] shadow-2xl">
            <h3 className="text-base font-semibold text-ops-alert">读写模式确认</h3>
            <p className="text-sm text-ops-subtext mt-2 leading-relaxed">
              当前会话已开启读写权限。AI 可能调用会改变目标系统状态的工具；高危工具仍会走后端审批。
            </p>
            <pre className="mt-3 max-h-32 overflow-y-auto whitespace-pre-wrap break-all bg-ops-dark border border-ops-surface0 rounded-lg p-2 text-xs text-ops-text">
              {readWriteConfirm.message}
            </pre>
            <label className="mt-3 flex items-center gap-2 text-sm text-ops-text">
              <input
                type="checkbox"
                checked={readWriteConfirm.remember}
                onChange={(e) => setReadWriteConfirm({ ...readWriteConfirm, remember: e.target.checked })}
                className="accent-ops-accent"
              />
              本会话不再提示
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setReadWriteConfirm(null)}
                className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text"
              >
                取消
              </button>
              <button
                onClick={confirmReadWriteSend}
                className="px-4 py-2 text-sm bg-ops-alert text-white rounded-lg font-medium hover:bg-ops-alert/80 transition-colors"
              >
                确认发送
              </button>
            </div>
          </div>
        </div>
      )}
      <ToolsetBar
        catalog={toolCatalog}
        session={session}
        availableModels={availableModels}
        modelName={modelName}
        thinkingMode={thinkingMode}
        onModelChange={setModelName}
        onThinkingModeChange={setThinkingMode}
      />
      {/* Messages area */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {messages.map((msg, index) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isPending={isStreaming && index === messages.length - 1 && msg.role === 'assistant'}
            onApproval={handleApproval}
            onInteraction={handleUserInteraction}
          />
        ))}
      </div>

      {/* Input area */}
      <div className="border-t border-ops-surface0 bg-ops-panel p-3">
        {slashCommands.length > 0 && (
          <QuickCommandDock
            commands={slashCommands.slice(0, 5)}
            onSelect={applySlashCommand}
          />
        )}
        {visibleSlashCommands.length > 0 && (
          <SlashCommandMenu
            commands={visibleSlashCommands}
            onSelect={applySlashCommand}
          />
        )}
        <div className="flex items-end gap-2">
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              setHistoryIndex(null)
            }}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行，上/下方向键选择历史输入)"
            rows={1}
            className="flex-1 bg-ops-dark text-ops-text rounded-lg px-3 py-2 text-sm resize-none outline-none border border-ops-surface1 focus:border-ops-accent transition-colors max-h-32 overflow-y-auto"
            style={{ minHeight: '38px' }}
          />

          <div className="flex shrink-0 flex-col gap-1 self-end">
            <button
              type="button"
              onClick={() => pickHistory('prev')}
              disabled={inputHistory.length === 0}
              className="h-[18px] w-8 rounded border border-ops-surface1 bg-ops-surface0 text-[10px] text-ops-subtext hover:text-ops-text disabled:opacity-35"
              title="上一条历史输入"
            >
              ↑
            </button>
            <button
              type="button"
              onClick={() => pickHistory('next')}
              disabled={inputHistory.length === 0 || historyIndex === null}
              className="h-[18px] w-8 rounded border border-ops-surface1 bg-ops-surface0 text-[10px] text-ops-subtext hover:text-ops-text disabled:opacity-35"
              title="下一条历史输入"
            >
              ↓
            </button>
          </div>

          {isStreaming ? (
            <button
              onClick={handleStop}
              className="bg-ops-alert text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-ops-alert/80 transition-colors shrink-0"
            >
              ⏹ 停止
            </button>
          ) : (
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim()}
              className="bg-ops-accent text-ops-dark px-4 py-2 rounded-lg text-sm font-medium hover:bg-ops-accent/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              发送 ↵
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function buildSlashCommands(session: Session, catalog: SessionToolCatalog | null) {
  const activeTools = catalog?.active_tools || []
  const toolList = activeTools.length > 0 ? activeTools.join(', ') : '当前会话原生协议工具'
  const target = `${session.asset_type}/${session.protocol} ${session.host}`
  return [
    {
      id: 'inspect',
      label: '/inspect 只读巡检',
      description: '按当前协议执行系统、数据库或网络设备巡检',
      prompt: `请对当前资产 ${target} 执行一次完整只读巡检。必须使用当前会话的原生协议工具，不要使用本地脚本。输出包括：关键健康状态、异常项、风险等级、建议下一步。`,
    },
    {
      id: 'config',
      label: '/config 当前配置',
      description: '查看系统或实例关键配置',
      prompt: `请查看当前资产 ${target} 的关键配置信息。必须使用当前会话的原生协议工具，不要重新登录或要求我提供账号密码。请按“基础信息、资源/版本、网络/监听、关键配置、异常项”输出。`,
    },
    {
      id: 'status',
      label: '/status 当前状态',
      description: '快速确认在线状态和核心指标',
      prompt: `请快速检查当前资产 ${target} 的运行状态。优先返回在线性、核心服务/实例状态、资源使用率、近期错误或告警线索。`,
    },
    {
      id: 'tools',
      label: '/tools 可用工具',
      description: '解释当前会话会用哪些协议工具',
      prompt: `请说明当前资产 ${target} 已启用的工具和正确使用边界。当前工具包括：${toolList}。请特别说明哪些操作只读可执行，哪些需要审批或会被硬拦截。`,
    },
    {
      id: 'risk',
      label: '/risk 风险排查',
      description: '只读模式下做安全和稳定性风险扫描',
      prompt: `请在只读模式下对当前资产 ${target} 做风险排查。禁止修改配置、重启服务、删除文件或写入数据。请输出高风险、中风险、低风险和需要人工确认的事项。`,
    },
  ]
}

function QuickCommandDock({
  commands,
  onSelect,
}: {
  commands: Array<{ id: string; label: string; description: string; prompt: string }>
  onSelect: (prompt: string) => void
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <span className="text-[10px] uppercase tracking-[0.18em] text-ops-overlay">当前资产快捷命令</span>
      {commands.map((cmd) => (
        <button
          key={cmd.id}
          type="button"
          onClick={() => onSelect(cmd.prompt)}
          className="rounded-full border border-ops-surface1 bg-ops-dark/70 px-3 py-1 text-[11px] text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text"
          title={cmd.description}
        >
          {cmd.label}
        </button>
      ))}
    </div>
  )
}

function SlashCommandMenu({
  commands,
  onSelect,
}: {
  commands: Array<{ id: string; label: string; description: string; prompt: string }>
  onSelect: (prompt: string) => void
}) {
  return (
    <div className="mb-3 max-w-3xl overflow-hidden rounded-xl border border-ops-surface1 bg-ops-dark/95 shadow-2xl">
      <div className="border-b border-ops-surface0 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-ops-overlay">
        斜杠菜单
      </div>
      <div className="grid gap-1 p-2 sm:grid-cols-2">
        {commands.map((cmd) => (
          <button
            key={cmd.id}
            type="button"
            onClick={() => onSelect(cmd.prompt)}
            className="rounded-lg px-3 py-2 text-left transition-colors hover:bg-ops-surface0 focus:outline-none focus:ring-1 focus:ring-ops-accent"
          >
            <div className="font-mono text-xs text-ops-accent">{cmd.label}</div>
            <div className="mt-1 text-[11px] text-ops-subtext">{cmd.description}</div>
          </button>
        ))}
      </div>
    </div>
  )
}

function ToolsetBar({
  catalog,
  session,
  availableModels,
  modelName,
  thinkingMode,
  onModelChange,
  onThinkingModeChange,
}: {
  catalog: SessionToolCatalog | null
  session: Session
  availableModels: ModelGroup[]
  modelName: string
  thinkingMode: string
  onModelChange: (value: string) => void
  onThinkingModeChange: (value: string) => void
}) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const enabledToolsets = (catalog?.toolsets || []).filter((t) => t.enabled)
  const activeTools = catalog?.active_tools || enabledToolsets.flatMap((t) => t.tools.filter((tool) => tool.enabled).map((tool) => tool.name))
  const primaryToolsets = enabledToolsets.slice(0, 3)
  const scope = session.target_scope || catalog?.context?.target_scope || 'asset'
  const scopeValue = session.scope_value || catalog?.context?.host || session.host
  const targetLabel = session.remark || session.host || '-'
  const toolsetSummary = primaryToolsets.length > 0
    ? primaryToolsets.map((toolset) => `${toolset.id} ${toolset.tools.filter((tool) => tool.enabled).length}`).join(' / ')
    : '读取工具集...'

  return (
    <div className="border-b border-ops-surface0 bg-ops-panel/80 px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span className="shrink-0 rounded-full border border-ops-accent/30 bg-ops-accent/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ops-accent">
            {session.asset_type}/{session.protocol}
          </span>
          <span className="truncate text-sm font-semibold text-ops-text">{targetLabel}</span>
          <span className="hidden min-w-0 truncate font-mono text-[11px] text-ops-overlay md:inline">
            {session.user}@{session.host}
          </span>
          <span className="hidden min-w-0 truncate rounded-full border border-ops-surface1/70 bg-ops-dark/45 px-2 py-1 font-mono text-[11px] text-ops-subtext xl:inline">
            {toolsetSummary}
          </span>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-ops-surface1 bg-ops-dark/60 px-2 py-1.5">
            <span className="text-[10px] text-ops-overlay">模型</span>
            <select
              value={modelName}
              onChange={(e) => onModelChange(e.target.value)}
              className="w-40 bg-transparent text-xs text-ops-text outline-none lg:w-48"
              title="模型"
            >
              {availableModels.length > 0 ? (
                availableModels.map((group) => (
                  <optgroup key={group.provider_id} label={group.provider_name}>
                    {group.models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                  </optgroup>
                ))
              ) : (
                <option value={modelName}>{modelName || '使用后端默认模型'}</option>
              )}
            </select>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-ops-surface1 bg-ops-dark/60 px-2 py-1.5">
            <span className="text-[10px] text-ops-overlay">思考</span>
            <select
              value={thinkingMode}
              onChange={(e) => onThinkingModeChange(e.target.value)}
              className="w-24 bg-transparent text-xs text-ops-text outline-none"
              title="思考模式"
            >
              <option value="off">关闭</option>
              <option value="enabled">开启</option>
              <option value="low">低度</option>
              <option value="medium">中度</option>
              <option value="high">高度</option>
            </select>
          </div>

          <span className="hidden rounded-lg border border-ops-surface1 bg-ops-dark/45 px-2 py-1.5 text-right text-[11px] text-ops-subtext sm:inline-flex">
            工具 <span className="ml-1 font-mono text-ops-text">{activeTools.length}</span>
            <span className="mx-1 text-ops-overlay">/</span>
            技能 <span className="ml-1 font-mono text-ops-text">{session.skills.length}</span>
          </span>

          <button
            type="button"
            onClick={() => setDetailsOpen((open) => !open)}
            className="rounded-lg border border-ops-surface1 bg-ops-dark/45 px-2.5 py-1.5 text-xs text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text"
            aria-expanded={detailsOpen}
          >
            {detailsOpen ? '收起' : '详情'}
          </button>
        </div>
      </div>

      {detailsOpen && (
        <div className="mt-2 grid gap-2 border-t border-ops-surface0 pt-2 lg:grid-cols-[1fr_360px]">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              {primaryToolsets.length > 0 ? primaryToolsets.map((toolset) => (
                <ToolsetPill key={toolset.id} toolset={toolset} />
              )) : (
                <span className="text-xs text-ops-overlay">正在读取当前会话工具集...</span>
              )}
              {enabledToolsets.length > primaryToolsets.length && (
                <span className="rounded-full border border-ops-surface1 bg-ops-dark/50 px-2 py-1 text-xs text-ops-overlay">
                  +{enabledToolsets.length - primaryToolsets.length} 类
                </span>
              )}
            </div>
            <div className="grid gap-2 text-[11px] text-ops-subtext md:grid-cols-2 xl:grid-cols-4">
              <ContextCell label="目标" value={targetLabel} />
              <ContextCell label="账号" value={session.user || '-'} />
              <ContextCell label="范围" value={`${scope}${scopeValue ? ` / ${scopeValue}` : ''}`} />
              <ContextCell label="标签" value={(session.tags || []).slice(0, 3).join(', ') || '-'} />
            </div>
          </div>
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 px-3 py-2 text-xs leading-relaxed text-ops-subtext">
            <div className="font-semibold text-ops-text">安全边界</div>
            <div className="mt-1">
              凭据由资产中心托管注入；高危工具进入审批队列，硬拦截规则会直接拒绝。
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ContextCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-ops-surface0 bg-ops-dark/35 px-2.5 py-2">
      <div className="text-[10px] uppercase tracking-[0.16em] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate font-mono text-ops-text">{value}</div>
    </div>
  )
}

function ToolsetPill({ toolset }: { toolset: ToolsetInfo }) {
  const enabledTools = toolset.tools.filter((tool) => tool.enabled)
  return (
    <details className="group">
      <summary className="cursor-pointer list-none rounded-full border border-ops-surface1 bg-ops-dark/70 px-3 py-1.5 text-xs text-ops-text hover:border-ops-accent/50">
        <span className="font-mono text-ops-accent">{toolset.id}</span>
        <span className="ml-2 text-ops-overlay">{enabledTools.length}</span>
      </summary>
      <div className="absolute z-20 mt-2 w-80 rounded-xl border border-ops-surface1 bg-ops-panel p-3 shadow-2xl">
        <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-ops-overlay">enabled tools</div>
        <div className="space-y-2">
          {enabledTools.map((tool) => (
            <div key={tool.name} className="rounded-lg bg-ops-dark/70 p-2">
              <div className="font-mono text-xs text-ops-text">{tool.name}</div>
              <div className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-ops-subtext">{tool.description}</div>
            </div>
          ))}
        </div>
      </div>
    </details>
  )
}

// --- Message Bubble Sub-component ---

function MessageBubble({ message, isPending = false, onApproval, onInteraction }: {
  message: ChatMessage
  isPending?: boolean
  onApproval: (toolCallId: string, approved: boolean, autoAll?: boolean) => void
  onInteraction: (requestId: string, value: string, label?: string) => void
}) {
  const [traceOpen, setTraceOpen] = useState(false)

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-ops-accent/15 text-ops-text rounded-2xl rounded-br-md px-4 py-2.5 text-sm whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    )
  }

  if (message.role === 'system') {
    return (
      <div className="flex justify-center">
        <div className="text-xs text-ops-subtext bg-ops-surface0 rounded-full px-3 py-1">
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant message
  const hasTrace = message.execTrace && message.execTrace.length > 0
  const approval = message.toolApproval
  const interaction = message.userInteraction
  const hasContent = message.content.trim().length > 0
  const shouldShowEmptyBubble = isPending && !hasContent && !approval && !interaction
  if (!hasContent && !hasTrace && !approval && !interaction && !isPending) {
    return null
  }
  const assistantTime = new Date(message.timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="flex w-full justify-start">
      <div className="w-full space-y-2">
        {/* Execution trace */}
        {hasTrace && (
          <div className="text-xs">
            <button
              onClick={() => setTraceOpen(!traceOpen)}
              className="text-ops-overlay hover:text-ops-subtext flex items-center gap-1"
            >
              <span>{traceOpen ? '▼' : '▶'}</span>
              <span>执行轨迹 ({message.execTrace!.length})</span>
            </button>
            {traceOpen && (
              <ToolTraceList items={message.execTrace!} />
            )}
          </div>
        )}

        {/* Tool approval request */}
        {approval && !approval.resolved && (
          <div className="bg-yellow-900/30 border border-yellow-600/40 rounded-lg p-3 space-y-2">
            <div className="text-sm font-medium text-yellow-400">⚠️ AI 请求执行敏感操作</div>
            <div className="text-xs text-ops-subtext">
              <span className="font-mono text-ops-text">{approval.toolName}</span>
              {approval.reason && <div className="mt-1 text-yellow-300">{approval.reason}</div>}
              <pre className="mt-1 whitespace-pre-wrap break-all">{approval.args.substring(0, 300)}</pre>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => onApproval(approval.toolCallId, true)}
                className="bg-ops-success/80 text-ops-dark text-xs px-3 py-1 rounded font-medium hover:bg-ops-success transition-colors"
              >
                ✅ 批准
              </button>
              <button
                onClick={() => onApproval(approval.toolCallId, false)}
                className="bg-ops-alert/80 text-white text-xs px-3 py-1 rounded font-medium hover:bg-ops-alert transition-colors"
              >
                ❌ 拒绝
              </button>
              <button
                onClick={() => onApproval(approval.toolCallId, true, true)}
                className="bg-ops-surface1 text-ops-subtext text-xs px-3 py-1 rounded hover:text-ops-text transition-colors"
              >
                全部批准
              </button>
            </div>
          </div>
        )}

        {interaction && (
          <UserInteractionCard interaction={interaction} onSubmit={onInteraction} />
        )}

        {/* Message content */}
        {hasContent ? (
          <article className="w-full overflow-hidden rounded-xl border border-ops-surface1/55 bg-ops-panel/85 shadow-[0_12px_40px_rgba(0,0,0,0.18)]">
            <div className="flex items-center justify-between gap-3 border-b border-ops-surface0/80 bg-ops-surface0/35 px-4 py-2">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-ops-success shadow-[0_0_14px_rgba(79,209,177,0.55)]" />
                <span className="text-xs font-semibold text-ops-text">AI 输出报告</span>
              </div>
              <span className="font-mono text-[11px] text-ops-overlay">{assistantTime}</span>
            </div>
            <div
              className="markdown-body ai-report-body w-full px-5 py-4"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          </article>
        ) : shouldShowEmptyBubble ? (
          <div className="w-full rounded-xl border border-ops-surface1/55 bg-ops-panel/85 px-5 py-4 text-[15px]">
            <span className="inline-flex gap-1">
              <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
            </span>
          </div>
        ) : null}
      </div>
    </div>
  )
}

function UserInteractionCard({
  interaction,
  onSubmit,
}: {
  interaction: UserInteractionRequest
  onSubmit: (requestId: string, value: string, label?: string) => void
}) {
  const [value, setValue] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isPassword = interaction.inputType === 'password'
  const isChoice = interaction.inputType === 'choice'
  const options = interaction.options || []

  const submitValue = async (nextValue: string, label = '') => {
    if (interaction.resolved || submitting) return
    if (interaction.required !== false && !nextValue.trim()) return
    setSubmitting(true)
    try {
      await Promise.resolve(onSubmit(interaction.requestId, nextValue, label))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-ops-accent/35 bg-ops-accent/5">
      <div className="border-b border-ops-accent/20 px-4 py-3">
        <div className="text-xs font-semibold text-ops-accent">需要你补充信息</div>
        <div className="mt-1 text-[15px] leading-relaxed text-ops-text">{interaction.prompt}</div>
      </div>

      {interaction.resolved ? (
        <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
          <span className="text-ops-success">已提交，AI 将继续处理。</span>
          {(interaction.label || interaction.value) && (
            <span className="max-w-[55%] truncate rounded-full border border-ops-surface1 bg-ops-panel px-3 py-1 text-xs text-ops-subtext">
              {interaction.label || interaction.value}
            </span>
          )}
        </div>
      ) : isChoice ? (
        <div className="grid gap-2 p-3 md:grid-cols-2">
          {options.map((option, index) => (
            <button
              key={`${option.value}-${index}`}
              type="button"
              disabled={submitting}
              onClick={() => submitValue(option.value, option.label)}
              className="rounded-lg border border-ops-surface1 bg-ops-panel/80 px-3 py-2 text-left transition-colors hover:border-ops-accent/70 hover:bg-ops-surface0 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <div className="text-sm font-medium text-ops-text">{option.label}</div>
              {option.description && (
                <div className="mt-1 text-xs leading-relaxed text-ops-subtext">{option.description}</div>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2 p-3 sm:flex-row">
          <input
            value={value}
            type={isPassword ? 'password' : 'text'}
            autoComplete={isPassword ? 'new-password' : 'off'}
            placeholder={interaction.placeholder || (isPassword ? '输入后仅用于本次会话' : '请输入补充信息')}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                submitValue(value)
              }
            }}
            className="min-w-0 flex-1 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
          />
          <button
            type="button"
            disabled={submitting || (interaction.required !== false && !value.trim())}
            onClick={() => submitValue(value)}
            className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            提交
          </button>
        </div>
      )}
    </section>
  )
}

function ToolTraceList({ items }: { items: ExecTraceItem[] }) {
  return (
    <div className="mt-2 space-y-2">
      {items.map((t, i) => (
        <ToolTraceCard key={i} item={t} />
      ))}
    </div>
  )
}

function ToolTraceCard({ item }: { item: ExecTraceItem }) {
  const status = item.status || (item.type === 'tool_start' ? 'running' : 'done')
  const elapsed = item.startedAt && item.completedAt
    ? `${Math.max(0, ((item.completedAt - item.startedAt) / 1000)).toFixed(1)}s`
    : item.startedAt
      ? 'running'
      : ''
  const tone = status === 'error'
    ? 'border-ops-alert/45 bg-ops-alert/5 text-ops-alert'
    : status === 'running'
      ? 'border-ops-accent/45 bg-ops-accent/5 text-ops-accent'
      : 'border-ops-success/30 bg-ops-success/5 text-ops-success'

  return (
    <div className={`overflow-hidden rounded-xl border ${tone}`}>
      <div className="flex items-center gap-2 px-3 py-2 text-xs">
        <span className={`h-2 w-2 rounded-full ${status === 'running' ? 'bg-ops-accent animate-pulse' : status === 'error' ? 'bg-ops-alert' : 'bg-ops-success'}`} />
        <span className="font-mono font-semibold text-ops-text">{item.tool}</span>
        {elapsed && <span className="ml-auto font-mono text-[10px] text-ops-overlay">{elapsed}</span>}
      </div>
      {item.args && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[10px] uppercase tracking-[0.18em] text-ops-overlay">args</div>
          <pre className="max-h-24 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
            {item.args.substring(0, 600)}
          </pre>
        </div>
      )}
      {item.result && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[10px] uppercase tracking-[0.18em] text-ops-overlay">result</div>
          <pre className="max-h-44 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
            {item.result.substring(0, 1200)}
          </pre>
        </div>
      )}
    </div>
  )
}

function completeLastTrace(items: ExecTraceItem[], data: Record<string, unknown>): ExecTraceItem[] {
  const result = String(data.result || '')
  const status = result.includes('"BLOCKED"') || result.includes('"ERROR"') || result.includes('❌') ? 'error' : 'done'
  const next = [...items]
  for (let i = next.length - 1; i >= 0; i--) {
    if (next[i].type === 'tool_start' && next[i].status === 'running') {
      next[i] = {
        ...next[i],
        type: 'tool_end',
        result,
        status,
        completedAt: Date.now(),
      }
      return next
    }
  }
  next.push({
    type: 'tool_end',
    tool: String(data.tool || 'unknown'),
    result,
    status,
    completedAt: Date.now(),
  })
  return next
}
