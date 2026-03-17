// Types for the OpsCore AIOps platform

export interface Session {
  id: string
  host: string
  remark: string
  isReadWriteMode: boolean
  skills: string[]
  agentProfile: string
  user: string
  asset_type: string
  extra_args: Record<string, unknown>
  heartbeatEnabled: boolean
  tags: string[]
  // Frontend-only state
  messages: ChatMessage[]
  isStreaming: boolean
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  // For tool execution traces
  execTrace?: ExecTraceItem[]
  // For tool approval requests
  toolApproval?: ToolApproval
}

export interface ExecTraceItem {
  type: 'tool_start' | 'tool_end'
  tool: string
  args?: string
  result?: string
}

export interface ToolApproval {
  toolCallId: string
  toolName: string
  args: string
  uniqueId: string
  resolved: boolean
}

export interface SkillInfo {
  id: string
  name: string
  description: string
  category: string
  is_market?: boolean
  source_path?: string
}

export interface Asset {
  id: number
  remark: string
  host: string
  port: number
  username: string
  password?: string
  asset_type: string
  agent_profile: string
  extra_args: Record<string, unknown>
  skills: string[]
  tags: string[]
}

export interface CronJob {
  id: string
  cron_expr: string
  message: string
  host: string
  username: string
  agent_profile: string
  next_run?: string
}

export interface KnowledgeFile {
  filename: string
  size?: number
  chunks?: number
}

export interface ApiResponse<T = Record<string, unknown>> {
  status: 'success' | 'error'
  data: T
  message: string
}

export type ViewId = 'chat' | 'assets' | 'cron' | 'skills' | 'knowledge'

export interface LLMPreset {
  name: string
  base_url: string
  api_key_placeholder: string
}
