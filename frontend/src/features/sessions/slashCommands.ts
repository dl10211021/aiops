import type { Session, SessionToolCatalog, SlashCommand } from '@/types'
import { toolLabel } from '@/utils/assetDisplay'

const DATABASE_ASSET_TYPES = new Set([
  'oracle',
  'mysql',
  'mariadb',
  'tidb',
  'oceanbase',
  'postgresql',
  'postgres',
  'opengauss',
  'kingbase',
  'vastbase',
  'mssql',
  'sqlserver',
  'dameng',
  'dm',
])

const DATABASE_PROTOCOLS = new Set(['oracle', 'mysql', 'postgresql', 'mssql', 'dameng', 'sql', 'jdbc'])

function databaseShortcutCommands(session: Session, activeTools: string[], target: string): SlashCommand[] {
  const isDatabaseSession = activeTools.includes('db_execute_query')
    || DATABASE_ASSET_TYPES.has(String(session.asset_type || '').toLowerCase())
    || DATABASE_PROTOCOLS.has(String(session.protocol || '').toLowerCase())
  if (!isDatabaseSession) return []
  return [
    {
      id: 'database-inspect',
      label: '数据库巡检',
      description: '按当前数据库类型执行完整只读巡检',
      category: '数据库巡检',
      prompt: `请对当前数据库 ${target} 做一次完整只读巡检。使用当前会话数据库工具，不要本地脚本，不要写入。先识别数据库类型和版本，再按该类型选择只读 SQL：连接/会话、容量、锁等待、慢 SQL/高耗 SQL、错误/告警、复制/集群、关键配置。输出：健康结论、证据 SQL 摘要、风险等级、P0/P1/P2 建议。`,
    },
    {
      id: 'database-slow-sql',
      label: '慢SQL分析',
      description: '按数据库类型查找慢 SQL、高耗 SQL、等待和锁线索',
      category: '数据库巡检',
      prompt: `请对当前数据库 ${target} 做只读慢 SQL 和高耗 SQL 分析。先判断数据库类型，再使用对应系统视图或性能视图查询。不要执行写入、kill、flush 或参数变更。输出：Top SQL、耗时/等待/锁、影响范围、证据 SQL 摘要、优化建议。`,
    },
    {
      id: 'database-baseline',
      label: '配置基线',
      description: '检查数据库关键参数、账号、安全和高风险配置',
      category: '数据库巡检',
      prompt: `请对当前数据库 ${target} 做只读配置基线检查。先识别数据库类型，再检查版本、关键参数、账号状态、权限风险、审计/日志、备份线索和高危默认配置。不要修改任何参数或账号。输出：异常项、风险等级、证据 SQL 摘要和整改建议。`,
    },
    {
      id: 'database-index',
      label: '索引健康',
      description: '分析索引、表空间/膨胀、热点对象和容量风险',
      category: '数据库巡检',
      prompt: `请对当前数据库 ${target} 做只读索引和对象健康分析。先识别数据库类型，再检查大表、索引失效/未使用、表空间或数据文件水位、膨胀/碎片、热点对象和容量风险。不要 rebuild、analyze、vacuum 或执行任何写入。输出：对象清单、风险等级、证据 SQL 摘要和建议动作。`,
    },
  ]
}

export function buildSlashCommands(session: Session, catalog: SessionToolCatalog | null): SlashCommand[] {
  const activeTools = catalog?.active_tools || []
  const activeToolDetails = catalog?.active_tool_details || []
  const toolList = activeToolDetails.length > 0
    ? activeToolDetails.map((tool) => tool.label || toolLabel(tool.name)).join('、')
    : activeTools.length > 0
      ? activeTools.map(toolLabel).join('、')
      : '当前会话原生协议工具'
  const target = `${session.asset_type}/${session.protocol} ${session.host}`
  return [
    ...databaseShortcutCommands(session, activeTools, target),
    {
      id: 'inspect',
      label: '只读巡检',
      description: '按当前协议执行系统、数据库或网络设备巡检',
      category: '通用',
      prompt: `请对当前资产 ${target} 执行一次完整只读巡检。必须使用当前会话的原生协议工具，不要使用本地脚本。输出包括：关键健康状态、异常项、风险等级、建议下一步。`,
    },
    {
      id: 'config',
      label: '当前配置',
      description: '查看系统或实例关键配置',
      category: '通用',
      prompt: `请查看当前资产 ${target} 的关键配置信息。必须使用当前会话的原生协议工具，不要重新登录或要求我提供账号密码。请按“基础信息、资源/版本、网络/监听、关键配置、异常项”输出。`,
    },
    {
      id: 'status',
      label: '当前状态',
      description: '快速确认在线状态和核心指标',
      category: '通用',
      prompt: `请快速检查当前资产 ${target} 的运行状态。优先返回在线性、核心服务/实例状态、资源使用率、近期错误或告警线索。`,
    },
    {
      id: 'tools',
      label: '可用工具',
      description: '解释当前会话会用哪些协议工具',
      category: '通用',
      prompt: `请说明当前资产 ${target} 已启用的工具和正确使用边界。当前工具包括：${toolList}。请特别说明哪些操作只读可执行，哪些需要审批或会被硬拦截。`,
    },
    {
      id: 'risk',
      label: '风险排查',
      description: '只读模式下做安全和稳定性风险扫描',
      category: '通用',
      prompt: `请在只读模式下对当前资产 ${target} 做风险排查。禁止修改配置、重启服务、删除文件或写入数据。请输出高风险、中风险、低风险和需要人工确认的事项。`,
    },
  ]
}

export function commandDraftForSession(session: Session | null): Partial<SlashCommand> {
  return {
    label: '自定义命令',
    description: '',
    prompt_template: session
      ? `请针对当前资产 {target} 执行自定义只读检查，并按“发现、影响、建议”输出。`
      : '请执行自定义检查，并按“发现、影响、建议”输出。',
    category: '自定义',
    scope_type: session ? 'asset_type' : 'global',
    asset_type: session?.asset_type || '',
    protocol: session?.protocol || '',
    host: '',
    readonly: true,
    pinned: true,
    enabled: true,
    sort_order: 1,
  }
}

export function commandDraftFromCommand(command: SlashCommand, session: Session | null): Partial<SlashCommand> {
  return {
    label: displayCommandLabel(command.label),
    description: command.description || '',
    prompt_template: command.prompt_template || command.prompt || '',
    category: command.category || '自定义',
    scope_type: command.scope_type === 'global' ? 'global' : 'asset_type',
    asset_type: command.asset_type || session?.asset_type || '',
    protocol: command.protocol || session?.protocol || '',
    host: '',
    readonly: command.readonly !== false,
    pinned: true,
    enabled: true,
    sort_order: 1,
  }
}

export function commandDraftForBuiltin(command: SlashCommand): Partial<SlashCommand> {
  return {
    id: command.builtin_id || command.id,
    label: displayCommandLabel(command.label),
    description: command.description || '',
    prompt_template: command.prompt_template || command.prompt || '',
    category: command.category || '通用',
    scope_type: command.scope_type || 'global',
    asset_type: command.asset_type || command.asset_types?.[0] || '',
    protocol: command.protocol || command.protocols?.[0] || '',
    host: command.host || '',
    readonly: command.readonly !== false,
    pinned: Boolean(command.pinned),
    enabled: command.enabled !== false,
    sort_order: Number(command.sort_order || 1),
    source: command.source || 'builtin',
    is_override: Boolean(command.is_override),
    builtin_id: command.builtin_id || command.id,
  }
}

export function scopeLabel(command: SlashCommand | Partial<SlashCommand>) {
  if (command.scope_type === 'asset') return `单资产 ${command.host || '-'}`
  if (command.scope_type === 'asset_type') return `系统 ${command.asset_type || '-'}`
  if (command.scope_type === 'protocol') return `协议 ${command.protocol || '-'}`
  return '全局'
}

function commandSortKey(command: SlashCommand) {
  const order = Number(command.sort_order || 100)
  return Number.isFinite(order) ? order : 100
}

export function commandStableId(command: SlashCommand) {
  return command.builtin_id || command.id
}

export function displayCommandLabel(label: string | undefined) {
  const raw = String(label || '').trim()
  if (!raw) return '快捷命令'
  return raw.replace(/^\/[A-Za-z0-9_-]+\s*/, '').trim() || raw.replace(/^\//, '')
}

export function sortCommandList(commands: SlashCommand[]) {
  return [...commands].sort((left, right) => {
    const orderDiff = commandSortKey(left) - commandSortKey(right)
    if (orderDiff !== 0) return orderDiff
    return left.label.localeCompare(right.label, 'zh-CN')
  })
}

export function commandOrderPreview(commands: SlashCommand[], pickedIds: string[]) {
  if (pickedIds.length === 0) return commands
  const byId = new Map(commands.map((command) => [commandStableId(command), command]))
  const picked = pickedIds.map((id) => byId.get(id)).filter(Boolean) as SlashCommand[]
  const pickedSet = new Set(pickedIds)
  return [...picked, ...commands.filter((command) => !pickedSet.has(commandStableId(command)))]
}

export function commandOrderSavePayload(commands: SlashCommand[], pickedIds: string[]) {
  return commandOrderPreview(commands, pickedIds).slice(0, 100).map((command, index) => {
    const base = command.source === 'custom' ? { ...command } : commandDraftForBuiltin(command)
    return {
      ...base,
      id: commandStableId(command),
      sort_order: index + 1,
      prompt_template: base.prompt_template || command.prompt_template || command.prompt || '',
      label: base.label || command.label,
      description: base.description ?? command.description ?? '',
      category: base.category || command.category || '通用',
      readonly: base.readonly !== false,
      pinned: Boolean(base.pinned),
      enabled: base.enabled !== false,
    }
  })
}
