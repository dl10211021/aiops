import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import type { ExecTraceItem, Session } from '@/types'
import { protocolLabel } from '@/utils/assetDisplay'
import { useStore } from '@/store'
import '@xterm/xterm/css/xterm.css'

interface SessionTerminalModalProps {
  sessions: Session[]
  activeSessionId: string
  onSelectSession: (sessionId: string) => void
  onCloseSession: (sessionId: string) => void
  onClose: () => void
  onMinimize: () => void
}

type TerminalState = 'connecting' | 'connected' | 'disconnected' | 'error'
type TerminalFloatRect = { left: number; top: number; width: number; height: number }
type SendTranscriptToChatFn = () => void

const AI_MIRROR_TOOL_NAMES = new Set([
  'linux_execute_command',
  'network_cli_execute_command',
  'winrm_execute_command',
  'container_execute_command',
  'middleware_execute_command',
  'storage_execute_command',
  'db_execute_query',
  'redis_execute_command',
  'memcached_execute_command',
  'mongodb_find',
])

export default function SessionTerminalModal({
  sessions,
  activeSessionId,
  onSelectSession,
  onCloseSession,
  onClose,
  onMinimize,
}: SessionTerminalModalProps) {
  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeSessionId) || sessions[0] || null,
    [activeSessionId, sessions],
  )
  const activeSessionRuntimeId = activeSession?.id || ''
  const activeSessionMessages = useStore((state) => (
    activeSessionRuntimeId ? state.sessions[activeSessionRuntimeId]?.messages || [] : []
  ))
  const hostRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const processedTraceKeysRef = useRef<Record<string, Set<string>>>({})
  const traceMirrorOpenedAtRef = useRef<Record<string, number>>({})
  const chatLinkEnabledRef = useRef(false)
  const draggingRef = useRef<{ pointerOffsetX: number; pointerOffsetY: number } | null>(null)
  const terminalInputDraftRef = useRef('')
  const terminalTranscriptRef = useRef('')
  const lastMirroredMessageRef = useRef('')
  const sendTranscriptToChatRef = useRef<SendTranscriptToChatFn | null>(null)
  const [connectVersion, setConnectVersion] = useState(0)
  const [state, setState] = useState<TerminalState>('connecting')
  const [errorText, setErrorText] = useState('')
  const [floatRect, setFloatRect] = useState<TerminalFloatRect | null>(null)
  const [chatLinkEnabled, setChatLinkEnabled] = useState(false)
  const terminalTitle = useMemo(
    () => {
      if (!activeSession) return '-'
      return `${activeSession.user}@${activeSession.host} (${protocolLabel(activeSession.protocol || activeSession.asset_type)})`
    },
    [activeSession],
  )

  useEffect(() => {
    if (!activeSessionRuntimeId) return
    const container = hostRef.current
    if (!container) return

    setState('connecting')
    setErrorText('')
    container.innerHTML = ''
    traceMirrorOpenedAtRef.current[activeSessionRuntimeId] = Date.now()

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: 'Cascadia Mono, Consolas, Menlo, monospace',
      fontSize: 13,
      scrollback: 20000,
      allowProposedApi: false,
      theme: {
        background: '#060a11',
        foreground: '#d5deea',
        cursor: '#5fe1b0',
        selectionBackground: 'rgba(95,225,176,0.24)',
      },
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(container)
    fitAddon.fit()
    term.focus()

    terminalRef.current = term
    fitAddonRef.current = fitAddon

    let disposed = false
    terminalInputDraftRef.current = ''
    terminalTranscriptRef.current = ''
    lastMirroredMessageRef.current = ''

    const sendResize = () => {
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return
      socketRef.current.send(JSON.stringify({
        type: 'resize',
        cols: term.cols,
        rows: term.rows,
      }))
    }
    const fitAndResize = () => {
      try {
        fitAddon.fit()
        sendResize()
      } catch {
        // The terminal can be disposed while a deferred resize is still queued.
      }
    }

    const connect = () => {
      const ws = new WebSocket(buildTerminalWebSocketUrl(activeSessionRuntimeId))
      socketRef.current = ws
      setState('connecting')

      ws.onopen = () => {
        if (disposed) return
        setState('connected')
        setErrorText('')
        sendResize()
        term.focus()
      }

      ws.onmessage = (event) => {
        if (disposed) return
        const content = typeof event.data === 'string' ? event.data : String(event.data || '')
        if (content) term.write(content)
        if (!chatLinkEnabledRef.current) return
        const normalized = normalizeTerminalChunk(content)
        if (!normalized) return
        terminalTranscriptRef.current = appendTerminalTranscript(terminalTranscriptRef.current, normalized)
      }

      ws.onerror = () => {
        if (disposed) return
        setState('error')
        setErrorText('终端连接异常')
      }

      ws.onclose = () => {
        if (disposed) return
        setState('disconnected')
      }
    }

    sendTranscriptToChatRef.current = () => {
      if (!chatLinkEnabledRef.current) return
      const transcript = truncateTerminalTranscript(terminalTranscriptRef.current.trim())
      if (!transcript) return
      const payload = [
        `【SSH终端记录】${terminalTitle}`,
        '以下是我在 SSH 终端里连续操作的一段记录：',
        '```text',
        transcript,
        '```',
        '请结合这段终端记录分析当前状态、异常点和下一步建议。',
      ].join('\n')
      if (payload === lastMirroredMessageRef.current) return
      lastMirroredMessageRef.current = payload
      emitTerminalLinkedChatMessage(activeSessionRuntimeId, payload)
      terminalTranscriptRef.current = ''
    }

    const inputDisposable = term.onData((data) => {
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return
      socketRef.current.send(JSON.stringify({ type: 'input', data }))
      if (!chatLinkEnabledRef.current) return
      const { draft, submittedCommands } = appendTerminalCommandBuffer(terminalInputDraftRef.current, data)
      terminalInputDraftRef.current = draft
      for (const command of submittedCommands) {
        terminalTranscriptRef.current = appendTerminalTranscript(
          terminalTranscriptRef.current,
          `\n$ ${command}\n`,
        )
      }
    })
    const resizeDisposable = term.onResize((size) => {
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return
      socketRef.current.send(JSON.stringify({
        type: 'resize',
        cols: size.cols,
        rows: size.rows,
      }))
    })

    const onWindowResize = fitAndResize
    window.addEventListener('resize', onWindowResize)
    const resizeObserver = new ResizeObserver(() => fitAndResize())
    resizeObserver.observe(container)
    window.requestAnimationFrame(() => {
      fitAndResize()
      window.requestAnimationFrame(fitAndResize)
    })

    connect()

    return () => {
      disposed = true
      window.removeEventListener('resize', onWindowResize)
      resizeObserver.disconnect()
      inputDisposable.dispose()
      resizeDisposable.dispose()
      if (socketRef.current) {
        try {
          socketRef.current.close()
        } catch {
          // no-op
        }
        socketRef.current = null
      }
      sendTranscriptToChatRef.current = null
      term.dispose()
      terminalRef.current = null
      fitAddonRef.current = null
    }
  }, [activeSessionRuntimeId, connectVersion, terminalTitle])

  useEffect(() => {
    if (!activeSessionRuntimeId) return
    if (chatLinkEnabled) return
    const term = terminalRef.current
    if (!term) return
    const openedAt = traceMirrorOpenedAtRef.current[activeSessionRuntimeId] || 0
    const seenMap = processedTraceKeysRef.current
    const seen = seenMap[activeSessionRuntimeId] || new Set<string>()
    seenMap[activeSessionRuntimeId] = seen
    for (const message of activeSessionMessages) {
      const traces = message.execTrace || []
      for (const trace of traces) {
        if (!AI_MIRROR_TOOL_NAMES.has(String(trace.tool || ''))) continue
        const key = traceMirrorKey(trace)
        if (seen.has(key)) continue
        seen.add(key)
        if (!isTraceAfterTerminalOpen(trace, openedAt)) continue
        if (trace.type === 'tool_start') {
          const cmd = extractTraceCommand(trace.args || '')
          if (cmd) term.writeln(`\r\n[AI CMD] ${cmd}`)
          continue
        }
        if (trace.type === 'tool_end') {
          const status = String(trace.status || 'done').toUpperCase()
          const output = extractTraceOutput(trace.result || '')
          term.writeln(`\r\n[AI RESULT ${status}] ${trace.tool}`)
          if (output) {
            for (const line of output.split('\n')) {
              term.writeln(line)
            }
          }
        }
      }
    }
  }, [activeSessionMessages, activeSessionRuntimeId, chatLinkEnabled])

  useEffect(() => {
    if (floatRect) return
    const width = Math.min(1040, Math.max(780, window.innerWidth - 24))
    const height = Math.min(Math.floor(window.innerHeight * 0.76), window.innerHeight - 24)
    setFloatRect({
      left: Math.max(12, window.innerWidth - width - 12),
      top: Math.max(12, window.innerHeight - height - 12),
      width,
      height,
    })
  }, [floatRect])

  useEffect(() => {
    const onWindowResize = () => {
      setFloatRect((current) => {
        if (!current) return current
        const width = Math.min(current.width, Math.max(520, window.innerWidth - 24))
        const height = Math.min(current.height, Math.max(360, window.innerHeight - 24))
        return {
          width,
          height,
          left: clamp(current.left, 8, Math.max(8, window.innerWidth - width - 8)),
          top: clamp(current.top, 8, Math.max(8, window.innerHeight - height - 8)),
        }
      })
    }
    window.addEventListener('resize', onWindowResize)
    return () => window.removeEventListener('resize', onWindowResize)
  }, [])

  useEffect(() => {
    const onPointerMove = (event: MouseEvent) => {
      if (!draggingRef.current) return
      const { pointerOffsetX, pointerOffsetY } = draggingRef.current
      setFloatRect((current) => {
        if (!current) return current
        const nextLeft = clamp(
          event.clientX - pointerOffsetX,
          8,
          Math.max(8, window.innerWidth - current.width - 8),
        )
        const nextTop = clamp(
          event.clientY - pointerOffsetY,
          8,
          Math.max(8, window.innerHeight - current.height - 8),
        )
        return { ...current, left: nextLeft, top: nextTop }
      })
    }
    const onPointerUp = () => {
      draggingRef.current = null
      document.body.style.userSelect = ''
    }
    window.addEventListener('mousemove', onPointerMove)
    window.addEventListener('mouseup', onPointerUp)
    return () => {
      window.removeEventListener('mousemove', onPointerMove)
      window.removeEventListener('mouseup', onPointerUp)
    }
  }, [])

  useEffect(() => {
    chatLinkEnabledRef.current = chatLinkEnabled
    if (!chatLinkEnabled) {
      terminalInputDraftRef.current = ''
      terminalTranscriptRef.current = ''
    }
  }, [chatLinkEnabled])

  if (!activeSession) return null

  const modal = (
    <div className="pointer-events-none fixed inset-0 z-[92]">
      <div
        className="pointer-events-auto absolute bottom-4 right-4 flex h-[min(76vh,calc(100vh-1.5rem))] w-[min(1040px,calc(100vw-1.5rem))] min-w-[780px] flex-col overflow-hidden rounded-2xl border border-ops-surface1/80 bg-ops-panel shadow-[0_28px_90px_rgba(0,0,0,0.55)]"
        style={floatRect ? {
          left: `${floatRect.left}px`,
          top: `${floatRect.top}px`,
          width: `${floatRect.width}px`,
          height: `${floatRect.height}px`,
          right: 'auto',
          bottom: 'auto',
        } : undefined}
      >
        <div
          className="flex cursor-move items-start justify-between gap-3 border-b border-ops-surface0 bg-[linear-gradient(135deg,rgba(40,208,168,0.14),rgba(14,28,46,0.9))] px-5 py-4"
          onMouseDown={(event) => {
            if (event.button !== 0) return
            if ((event.target as HTMLElement).closest('button')) return
            const panelRect = event.currentTarget.parentElement?.getBoundingClientRect()
            if (!panelRect) return
            draggingRef.current = {
              pointerOffsetX: event.clientX - panelRect.left,
              pointerOffsetY: event.clientY - panelRect.top,
            }
            document.body.style.userSelect = 'none'
          }}
        >
          <div className="min-w-0">
            <h2 className="truncate text-sm font-bold text-ops-text">SSH Terminal</h2>
            <div className="mt-1 truncate text-[11px] text-ops-overlay">{terminalTitle}</div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => terminalRef.current?.clear()}
              className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-2.5 py-1 text-xs text-ops-subtext transition-colors hover:text-ops-text"
            >
              清屏
            </button>
            <button
              type="button"
              onClick={() => setConnectVersion((value) => value + 1)}
              className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-2.5 py-1 text-xs text-ops-subtext transition-colors hover:text-ops-text"
            >
              重连
            </button>
            <button
              type="button"
              onClick={onMinimize}
              className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-2.5 py-1 text-xs text-ops-subtext transition-colors hover:text-ops-text"
              title="最小化"
            >
              最小化
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-2 py-1 text-xs text-ops-overlay transition-colors hover:bg-ops-surface0 hover:text-ops-text"
              title="关闭当前"
            >
              关闭当前
            </button>
          </div>
        </div>

        <div className="border-b border-ops-surface0/80 bg-ops-dark/35 px-4 py-2">
          <div className="flex gap-2 overflow-x-auto pb-0.5">
            {sessions.map((item) => {
              const active = item.id === activeSession.id
              return (
                <div
                  key={item.id}
                  className={`inline-flex min-w-0 shrink-0 items-center gap-1.5 rounded-lg border px-2 py-1 text-[11px] ${
                    active
                      ? 'border-ops-accent/55 bg-ops-accent/15 text-ops-accent'
                      : 'border-ops-surface1/70 bg-ops-panel/50 text-ops-subtext'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelectSession(item.id)}
                    className="max-w-[180px] truncate text-left"
                    title={`${item.user}@${item.host}`}
                  >
                    {item.remark || item.host}
                  </button>
                  <button
                    type="button"
                    onClick={() => onCloseSession(item.id)}
                    className="rounded px-1 text-ops-overlay transition-colors hover:bg-ops-surface0 hover:text-ops-text"
                    title="关闭标签"
                    aria-label="关闭标签"
                  >
                    ×
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        <div className="border-b border-ops-surface0/80 px-4 py-1.5 text-[11px] text-ops-overlay">
          <span className="mr-2">状态：</span>
          <span className={statusClassName(state)}>{statusText(state)}</span>
          {errorText && <span className="ml-3 text-red-300">{errorText}</span>}
          <span className="ml-4 inline-flex items-center gap-1.5">
            <label className="inline-flex cursor-pointer items-center gap-1.5 select-none text-ops-subtext">
              <input
                type="checkbox"
                checked={chatLinkEnabled}
                onChange={(event) => {
                  const enabled = event.currentTarget.checked
                  terminalInputDraftRef.current = ''
                  terminalTranscriptRef.current = ''
                  setChatLinkEnabled(enabled)
                }}
              />
              记录终端
            </label>
            <button
              type="button"
              onClick={() => sendTranscriptToChatRef.current?.()}
              disabled={!chatLinkEnabled}
              className="rounded border border-ops-surface1/80 bg-ops-dark/35 px-2 py-0.5 text-[10px] text-ops-subtext transition-colors enabled:hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-45"
            >
              分析记录
            </button>
            <button
              type="button"
              onClick={() => {
                terminalInputDraftRef.current = ''
                terminalTranscriptRef.current = ''
              }}
              disabled={!chatLinkEnabled}
              className="rounded border border-ops-surface1/80 bg-ops-dark/35 px-2 py-0.5 text-[10px] text-ops-subtext transition-colors enabled:hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-45"
            >
              清空记录
            </button>
          </span>
        </div>

        <div className="min-h-0 flex-1 px-4 py-3">
          <div className="h-full min-h-0 overflow-hidden rounded-xl border border-ops-surface1/65 bg-[#060a11] p-2">
            <div
              ref={hostRef}
              className="h-full min-h-0 overflow-hidden"
              aria-label="SSH terminal"
              role="region"
            />
          </div>
        </div>

        <div className="border-t border-ops-surface0 px-4 py-2 text-[11px] text-ops-overlay">
          已启用持续会话模式；终端记录只在点击分析时进入当前 AI 会话，本轮不执行工具。
        </div>
      </div>
    </div>
  )
  return createPortal(modal, document.body)
}

function buildTerminalWebSocketUrl(sessionId: string): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const params = new URLSearchParams()
  const token = localStorage.getItem('OPSCORE_API_TOKEN')
  if (token) params.set('token', token)
  return `${scheme}://${window.location.host}/api/v1/session/${encodeURIComponent(sessionId)}/terminal/ws?${params.toString()}`
}

function statusText(state: TerminalState): string {
  if (state === 'connected') return '已连接'
  if (state === 'connecting') return '连接中'
  if (state === 'error') return '异常'
  return '已断开'
}

function statusClassName(state: TerminalState): string {
  if (state === 'connected') return 'text-ops-success'
  if (state === 'connecting') return 'text-ops-accent'
  if (state === 'error') return 'text-red-300'
  return 'text-yellow-200'
}

function traceMirrorKey(trace: ExecTraceItem): string {
  return [
    trace.type,
    trace.tool || '',
    trace.startedAt || '',
    trace.completedAt || '',
    trace.status || '',
    trace.args || '',
  ].join('|')
}

function isTraceAfterTerminalOpen(trace: ExecTraceItem, openedAt: number): boolean {
  const timestamp = normalizeTraceTimestamp(trace.startedAt ?? trace.completedAt)
  if (!timestamp) return false
  return timestamp >= openedAt
}

function normalizeTraceTimestamp(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return value < 10_000_000_000 ? value * 1000 : value
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function extractTraceCommand(rawArgs: string): string {
  const parsed = parseJsonRecord(rawArgs)
  if (parsed) {
    if (typeof parsed.command === 'string' && parsed.command.trim()) return parsed.command.trim()
    if (typeof parsed.sql === 'string' && parsed.sql.trim()) return parsed.sql.trim()
  }
  return rawArgs.trim()
}

function extractTraceOutput(rawResult: string): string {
  const parsed = parseJsonRecord(rawResult)
  if (parsed) {
    const candidates = [parsed.output, parsed.error, parsed.result, parsed.message]
    for (const value of candidates) {
      if (typeof value === 'string' && value.trim()) return truncateMirrorText(value.trim())
    }
  }
  if (rawResult.trim()) return truncateMirrorText(rawResult.trim())
  return ''
}

function truncateMirrorText(text: string): string {
  const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const lines = normalized.split('\n')
  const clipped = lines.slice(0, 40).join('\n')
  return clipped.length > 2000 ? `${clipped.slice(0, 2000)}\n...[truncated]` : clipped
}

function parseJsonRecord(value: string): Record<string, unknown> | null {
  if (!value) return null
  try {
    const parsed = JSON.parse(value)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
  } catch {
    return null
  }
  return null
}

function emitTerminalLinkedChatMessage(sessionId: string, message: string): void {
  const content = message.trim()
  if (!sessionId || !content) return
  window.dispatchEvent(new CustomEvent('opscore:chat-send', {
    detail: {
      sessionId,
      message: content,
      source: 'terminal',
      analysisOnly: true,
    },
  }))
}

function appendTerminalTranscript(current: string, nextChunk: string): string {
  const merged = `${current}${nextChunk}`
  if (merged.length <= 30000) return merged
  return merged.slice(merged.length - 30000)
}

function truncateTerminalTranscript(text: string): string {
  const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (normalized.length <= 8000) return normalized
  return `...[terminal transcript truncated]\n${normalized.slice(normalized.length - 8000)}`
}

function appendTerminalCommandBuffer(
  currentDraft: string,
  inputData: string,
): { draft: string; submittedCommands: string[] } {
  let draft = currentDraft
  const submittedCommands: string[] = []
  for (const char of inputData) {
    if (char === '\r' || char === '\n') {
      const normalized = draft.trim()
      if (normalized) submittedCommands.push(normalized)
      draft = ''
      continue
    }
    if (char === '\u007f' || char === '\b') {
      draft = draft.slice(0, -1)
      continue
    }
    if (char === '\u0015' || char === '\u0003') {
      draft = ''
      continue
    }
    if (char === '\t') {
      draft += ' '
      continue
    }
    if (char.charCodeAt(0) < 32 || char === '\u001b') continue
    draft += char
  }
  if (draft.length > 4096) {
    draft = draft.slice(draft.length - 4096)
  }
  return { draft, submittedCommands }
}

function normalizeTerminalChunk(value: string): string {
  if (!value) return ''
  return value
    .replace(/\u001b\[[0-9;?]*[ -/]*[@-~]/g, '')
    .replace(/\u001b][^\u0007]*(?:\u0007|\u001b\\)/g, '')
    .replace(/[^\x09\x0A\x0D\x20-\x7E]/g, '')
}
