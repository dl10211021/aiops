import { useRef, useEffect, useState } from 'react'
import { useStore } from '@/store'
import { streamChat, stopChat, approveToolCall } from '@/api/client'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChatMessage, ExecTraceItem, ToolApproval } from '@/types'

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
  const [modelName, setModelName] = useState(() =>
    localStorage.getItem('ops_model') || 'gemini-2.5-flash-preview-05-20'
  )
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const session = currentSessionId ? sessions[currentSessionId] : null
  const messages = session?.messages || []
  const isStreaming = session?.isStreaming || false

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load available models once
  useEffect(() => {
    import('@/api/client').then(({ getAvailableModels }) =>
      getAvailableModels().then((r) => {
        if (r.data.models) setAvailableModels(r.data.models)
      }).catch(() => {})
    )
  }, [])

  // Save model to localStorage
  useEffect(() => {
    localStorage.setItem('ops_model', modelName)
  }, [modelName])

  const sendMessage = async () => {
    if (!input.trim() || !currentSessionId || isStreaming) return

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    }
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
      const response = await streamChat(currentSessionId, userMsg.content, modelName, controller.signal)
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
                  } as ExecTraceItem],
                }))
                break

              case 'tool_end':
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  execTrace: [...(m.execTrace || []), {
                    type: 'tool_end',
                    tool: data.tool || 'unknown',
                    result: data.result || '',
                  } as ExecTraceItem],
                }))
                break

              case 'tool_ask_approval': {
                const approval: ToolApproval = {
                  toolCallId: data.tool_call_id,
                  toolName: data.tool_name || 'unknown',
                  args: typeof data.args === 'string' ? data.args : JSON.stringify(data.args || {}),
                  uniqueId: `approval-${Date.now()}`,
                  resolved: false,
                }
                updateLastAssistantMessage(sid, (m) => ({
                  ...m,
                  toolApproval: approval,
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
      }
    } finally {
      updateSession(currentSessionId, { isStreaming: false })
      setChatController(null)
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
    try {
      await approveToolCall(currentSessionId, toolCallId, approved, autoAll)
      updateLastAssistantMessage(currentSessionId, (m) => ({
        ...m, toolApproval: m.toolApproval ? { ...m.toolApproval, resolved: true } : undefined,
      }))
    } catch {
      addToast('审批提交失败', 'error')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
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
    <div className="flex-1 flex flex-col min-w-0">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onApproval={handleApproval}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-ops-surface0 bg-ops-panel p-3">
        <div className="flex items-end gap-2">
          {/* Model selector */}
          <select
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            className="bg-ops-surface0 text-ops-text text-xs rounded px-2 py-1.5 border border-ops-surface1 outline-none self-end"
          >
            {availableModels.length > 0 ? (
              availableModels.map((m) => <option key={m} value={m}>{m}</option>)
            ) : (
              <option value={modelName}>{modelName}</option>
            )}
          </select>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            rows={1}
            className="flex-1 bg-ops-dark text-ops-text rounded-lg px-3 py-2 text-sm resize-none outline-none border border-ops-surface1 focus:border-ops-accent transition-colors max-h-32 overflow-y-auto"
            style={{ minHeight: '38px' }}
          />

          {isStreaming ? (
            <button
              onClick={handleStop}
              className="bg-ops-alert text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-ops-alert/80 transition-colors shrink-0"
            >
              ⏹ 停止
            </button>
          ) : (
            <button
              onClick={sendMessage}
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

// --- Message Bubble Sub-component ---

function MessageBubble({ message, onApproval }: {
  message: ChatMessage
  onApproval: (toolCallId: string, approved: boolean, autoAll?: boolean) => void
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

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
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
              <div className="mt-1 bg-ops-dark rounded-lg p-2 space-y-1 border border-ops-surface0">
                {message.execTrace!.map((t, i) => (
                  <div key={i} className="flex items-start gap-1">
                    <span className={t.type === 'tool_start' ? 'text-ops-accent' : 'text-ops-success'}>
                      {t.type === 'tool_start' ? '▶' : '✓'}
                    </span>
                    <div className="min-w-0">
                      <span className="font-mono">{t.tool}</span>
                      {t.args && (
                        <pre className="text-ops-overlay mt-0.5 whitespace-pre-wrap break-all">{t.args.substring(0, 300)}</pre>
                      )}
                      {t.result && (
                        <pre className="text-ops-subtext mt-0.5 whitespace-pre-wrap break-all max-h-40 overflow-y-auto">{t.result.substring(0, 500)}</pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tool approval request */}
        {approval && !approval.resolved && (
          <div className="bg-yellow-900/30 border border-yellow-600/40 rounded-lg p-3 space-y-2">
            <div className="text-sm font-medium text-yellow-400">⚠️ AI 请求执行敏感操作</div>
            <div className="text-xs text-ops-subtext">
              <span className="font-mono text-ops-text">{approval.toolName}</span>
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

        {/* Message content */}
        {message.content ? (
          <div
            className="markdown-body bg-ops-panel rounded-2xl rounded-bl-md px-4 py-2.5 text-sm"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
          />
        ) : (
          <div className="bg-ops-panel rounded-2xl rounded-bl-md px-4 py-2.5 text-sm">
            <span className="inline-flex gap-1">
              <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-ops-accent rounded-full" />
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
