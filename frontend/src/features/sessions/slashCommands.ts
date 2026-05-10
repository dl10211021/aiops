import type { Session, SessionToolCatalog, SlashCommand } from '@/types'
import { toolLabel } from '@/utils/assetDisplay'

const SQL_DATABASE_ASSET_TYPES = new Set([
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
  'db2',
  'clickhouse',
  'hive',
  'iotdb',
  'xugu',
  'starrocks_fe',
  'doris_fe',
])

const DATA_SERVICE_ASSET_TYPES = new Set([
  ...SQL_DATABASE_ASSET_TYPES,
  'redis',
  'redis_cluster',
  'redis_sentinel',
  'valkey',
  'kvrocks',
  'mongodb',
  'mongodb_atlas',
  'elasticsearch',
  'opensearch',
  'memcached',
  'starrocks_be',
  'doris_be',
  'hbase_master',
  'hbase_regionserver',
  'hugegraph',
  'influxdb',
  'nebula_graph',
  'nebula_graph_cluster',
])

const SQL_DATABASE_PROTOCOLS = new Set([
  'oracle',
  'mysql',
  'postgresql',
  'mssql',
  'sqlserver',
  'db2',
  'dameng',
  'hive',
  'iotdb',
  'clickhouse',
  'xugu',
  'sql',
  'jdbc',
])

const DATA_SERVICE_PROTOCOLS = new Set([
  ...SQL_DATABASE_PROTOCOLS,
  'redis',
  'mongodb',
  'elasticsearch',
  'memcached',
  'nebula_graph',
])

const DATABASE_TOOL_NAMES = new Set([
  'db_execute_query',
  'database_api_request',
  'redis_execute_command',
  'memcached_execute_command',
  'mongodb_find',
])

const SQL_DATABASE_TOOLS = new Set(['db_execute_query'])

const DEDICATED_DB_PROTOCOLS: Record<string, string[]> = {
  oracle: ['oracle', 'sql'],
  mysql: ['mysql', 'sql'],
  mariadb: ['mysql', 'sql'],
  tidb: ['mysql', 'sql'],
  oceanbase: ['mysql', 'sql'],
  postgresql: ['postgresql', 'sql'],
  postgres: ['postgresql', 'sql'],
  opengauss: ['postgresql', 'sql'],
  kingbase: ['postgresql', 'sql'],
  vastbase: ['postgresql', 'sql'],
  mssql: ['mssql', 'sql'],
  sqlserver: ['mssql', 'sql'],
  dameng: ['dameng', 'sql'],
  dm: ['dameng', 'sql'],
  db2: ['db2', 'sql'],
  xugu: ['xugu', 'sql'],
}

const TOOL_CATEGORY: Record<string, string> = {
  db_execute_query: 'db',
  database_api_request: 'db',
  redis_execute_command: 'db',
  memcached_execute_command: 'db',
  mongodb_find: 'db',
  container_execute_command: 'container',
  k8s_api_request: 'container',
  middleware_execute_command: 'middleware',
  middleware_api_request: 'middleware',
  storage_execute_command: 'storage',
  storage_api_request: 'storage',
  bigdata_api_request: 'bigdata',
  network_cli_execute_command: 'network',
  snmp_get: 'network',
  monitoring_api_query: 'monitor',
  virtualization_api_request: 'virtualization',
  service_probe_request: 'service',
  discovery_api_request: 'discovery',
  security_api_request: 'security',
  oob_api_request: 'oob',
  ai_platform_api_request: 'ai',
  cicd_api_request: 'cicd',
  winrm_execute_command: 'os',
  linux_execute_command: 'os',
}

function text(value: unknown) {
  return String(value || '').toLowerCase()
}

function sessionCategory(session: Session, activeTools: string[]) {
  const category = text(session.extra_args?.category)
  if (category) return category
  for (const tool of activeTools) {
    const toolCategory = TOOL_CATEGORY[tool]
    if (toolCategory) return toolCategory
  }
  const protocol = text(session.protocol)
  if (DATA_SERVICE_PROTOCOLS.has(protocol)) return 'db'
  return ''
}

function hasAnyTool(activeTools: string[], names: Set<string>) {
  return activeTools.some((tool) => names.has(tool))
}

function hasDedicatedDatabaseProtocolMismatch(assetType: string, protocol: string, activeTools: string[]) {
  const expected = DEDICATED_DB_PROTOCOLS[assetType]
  if (!expected) return false
  if (hasAnyTool(activeTools, DATABASE_TOOL_NAMES)) return false
  return !expected.includes(protocol)
}

function isDataServiceSession(session: Session, activeTools: string[]) {
  const assetType = text(session.asset_type)
  const protocol = text(session.protocol)
  if (hasDedicatedDatabaseProtocolMismatch(assetType, protocol, activeTools)) return false
  return hasAnyTool(activeTools, DATABASE_TOOL_NAMES)
    || sessionCategory(session, activeTools) === 'db'
    || DATA_SERVICE_ASSET_TYPES.has(assetType)
    || DATA_SERVICE_PROTOCOLS.has(protocol)
}

function isSqlDatabaseSession(session: Session, activeTools: string[]) {
  const assetType = text(session.asset_type)
  const protocol = text(session.protocol)
  if (hasDedicatedDatabaseProtocolMismatch(assetType, protocol, activeTools)) return false
  return hasAnyTool(activeTools, SQL_DATABASE_TOOLS)
    || SQL_DATABASE_ASSET_TYPES.has(assetType)
    || SQL_DATABASE_PROTOCOLS.has(protocol)
}

function command(
  id: string,
  label: string,
  description: string,
  category: string,
  prompt: string,
  pinned = true,
): SlashCommand {
  return { id, label, description, category, prompt, pinned }
}

function databaseShortcutCommands(session: Session, activeTools: string[], target: string): SlashCommand[] {
  if (!isDataServiceSession(session, activeTools)) return []
  const assetType = text(session.asset_type)
  const protocol = text(session.protocol)
  const commands = [
    command(
      'database-inspect',
      '/db-inspect 数据库巡检',
      '按当前数据服务类型执行完整只读巡检',
      '数据库巡检',
      `请对当前数据服务 ${target} 做一次完整只读巡检。使用当前会话数据库或数据服务原生工具，不要本地脚本，不要写入。先识别类型和版本，再按该类型选择只读 SQL、命令或 API：连接/会话、容量、锁等待或慢操作、错误/告警、复制/集群、关键配置。输出：健康结论、证据摘要、风险等级、P0/P1/P2 建议。`,
    ),
  ]

  if (assetType === 'oracle' || protocol === 'oracle') {
    commands.push(
      command('oracle-health', '/oracle-health 实例健康', '检查 Oracle 实例、监听、会话和等待事件', '数据库巡检', `请使用当前 Oracle 会话只读检查 ${target}：实例状态、数据库版本、监听/服务名线索、会话数、等待事件、告警日志线索。不要执行 DDL/DML。`),
      command('oracle-tablespace', '/tablespace 表空间', '检查表空间水位、数据文件和自动扩展', '数据库巡检', `请只读检查 ${target} 的表空间使用率、数据文件、自动扩展、临时表空间和即将满的风险，按紧急程度输出。`, false),
      command('oracle-locks', '/locks 锁等待', '检查阻塞、锁等待和长事务', '数据库巡检', `请只读检查 ${target} 的阻塞会话、锁等待、长事务、活跃 SQL 和影响范围。不要 kill session，不要修改系统参数。`, false),
    )
  } else if (['mysql', 'mariadb', 'tidb', 'oceanbase'].includes(assetType) || protocol === 'mysql') {
    commands.push(
      command('mysql-health', '/mysql-health 实例健康', '检查 MySQL/TiDB 版本、连接、慢 SQL 和复制状态', '数据库巡检', `请使用当前 MySQL/TiDB 会话只读检查 ${target}：版本、运行时长、连接数、慢查询、错误计数、复制状态和容量风险。不要执行写入 SQL。`),
      command('mysql-process', '/processlist 会话列表', '查看 MySQL 活跃连接、锁等待和长查询', '数据库巡检', `请只读检查 ${target} 的 processlist、长查询、锁等待和异常来源 IP，输出可能影响业务的 SQL 线索。`, false),
    )
  } else if (['postgresql', 'postgres', 'opengauss', 'kingbase', 'vastbase'].includes(assetType) || protocol === 'postgresql') {
    commands.push(command('postgres-health', '/pg-health 实例健康', '检查 PostgreSQL 连接、复制、锁等待和膨胀风险', '数据库巡检', `请使用当前 PostgreSQL 会话只读检查 ${target}：版本、连接数、复制状态、锁等待、长事务、膨胀风险、慢查询线索和容量风险。不要执行写入 SQL。`))
  } else if (protocol === 'redis' || ['redis', 'redis_cluster', 'redis_sentinel', 'valkey', 'kvrocks'].includes(assetType)) {
    commands.push(command('redis-health', '/redis-health Redis 健康', '检查 Redis 内存、持久化、连接和慢日志', '数据库巡检', `请只读检查 ${target} 的 Redis info、内存水位、客户端连接、持久化状态、复制状态、慢日志摘要和高风险配置。`))
  } else if (protocol === 'mongodb' || ['mongodb', 'mongodb_atlas'].includes(assetType)) {
    commands.push(command('mongodb-health', '/mongo-health 实例健康', '检查 MongoDB 副本集、连接、慢操作和存储水位', '数据库巡检', `请只读检查 ${target} 的 MongoDB 状态：版本、副本集/分片状态、连接数、慢操作、锁/队列、存储空间和高风险配置。`))
  } else if (protocol === 'elasticsearch' || ['elasticsearch', 'opensearch'].includes(assetType)) {
    commands.push(command('elastic-health', '/es-health 集群健康', '检查 Elasticsearch/OpenSearch 集群、索引、分片和磁盘水位', '数据库巡检', `请只读检查 ${target} 的 Elasticsearch/OpenSearch 健康：cluster health、节点状态、索引异常、未分配分片、磁盘水位、慢查询和安全配置风险。`))
  }

  if (isSqlDatabaseSession(session, activeTools)) {
    commands.push(
      command('database-slow-sql', '/db-slow 慢SQL分析', '按数据库类型查找慢 SQL、高耗 SQL、等待和锁线索', '数据库巡检', `请对当前数据库 ${target} 做只读慢 SQL 和高耗 SQL 分析。先判断数据库类型，再使用对应系统视图或性能视图查询。不要执行写入、kill、flush 或参数变更。输出：Top SQL、耗时/等待/锁、影响范围、证据 SQL 摘要、优化建议。`, false),
      command('database-baseline', '/db-baseline 配置基线', '检查数据库关键参数、账号、安全和高风险配置', '数据库巡检', `请对当前数据库 ${target} 做只读配置基线检查。先识别数据库类型，再检查版本、关键参数、账号状态、权限风险、审计/日志、备份线索和高危默认配置。不要修改任何参数或账号。输出：异常项、风险等级、证据 SQL 摘要和整改建议。`, false),
      command('database-index', '/db-index 索引健康', '分析索引、表空间/膨胀、热点对象和容量风险', '数据库巡检', `请对当前数据库 ${target} 做只读索引和对象健康分析。先识别数据库类型，再检查大表、索引失效/未使用、表空间或数据文件水位、膨胀/碎片、热点对象和容量风险。不要 rebuild、analyze、vacuum 或执行任何写入。输出：对象清单、风险等级、证据 SQL 摘要和建议动作。`, false),
    )
  }

  return commands
}

function domainShortcutCommands(session: Session, activeTools: string[], target: string): SlashCommand[] {
  const category = sessionCategory(session, activeTools)
  if (category === 'db') return []
  if (category === 'network') {
    return [command('network-device-health', '/net-health 网络设备健康', '检查网络设备接口、路由、邻居、CPU/内存和告警', '网络', `请只读检查 ${target} 的网络设备健康：设备型号/版本、CPU/内存、接口状态、错误包、路由/邻居摘要、HA 状态和近期告警。不要修改配置。`)]
  }
  if (category === 'storage') {
    return [command('storage-health', '/storage 存储健康', '检查块/文件/分布式存储容量、告警和副本状态', '存储', `请只读检查 ${target} 的存储健康：容量水位、卷/池状态、副本/恢复状态、近期告警、性能瓶颈和数据保护风险。`)]
  }
  if (category === 'middleware') {
    return [command('middleware-health', '/middleware 中间件健康', '检查中间件进程、端口、日志、队列或集群状态', '中间件', `请只读检查 ${target} 的中间件健康状态：进程/服务、监听端口、版本、集群/队列状态、近期错误日志、资源水位和业务影响。`)]
  }
  if (category === 'container') {
    const commands = [command('container-health', '/container 容器平台健康', '检查容器平台、运行时、镜像仓库和节点状态', '容器平台', `请只读检查 ${target} 的容器平台健康：节点/运行时状态、镜像仓库/API 连通、工作负载或容器异常、近期事件、资源水位和安全风险。必须使用当前会话原生工具，不要修改工作负载或镜像。`)]
    if (text(session.protocol) === 'k8s' || ['k8s', 'kubernetes', 'openshift'].includes(text(session.asset_type))) {
      commands.push(command('k8s-workloads', '/workloads 工作负载', '检查 K8s 节点、Pod、事件和异常工作负载', '容器平台', `请只读检查 ${target} 的 Kubernetes 节点、Pod、Deployment/StatefulSet、近期事件、重启次数和 Pending/CrashLoop 风险。`, false))
    }
    return commands
  }
  if (category === 'bigdata') {
    return [command('bigdata-health', '/bigdata 大数据健康', '检查大数据、分析计算、调度和数据平台状态', '大数据', `请只读检查 ${target} 的大数据/分析平台健康：组件状态、作业/任务、队列/集群、存储水位、失败事件、延迟和关键配置。必须使用当前会话原生工具，不要提交、停止或修改任务。`)]
  }
  if (category === 'virtualization') {
    return [command('vmware-health', '/vmware-health 虚拟化健康', '检查虚拟化平台主机、集群、存储和虚机风险', '虚拟化', `请只读检查 ${target} 的虚拟化平台健康：主机状态、集群资源、Datastore 水位、异常虚机、快照风险和告警摘要。`)]
  }
  if (category === 'monitor') {
    return [command('monitoring-alerts', '/alerts 告警摘要', '检查监控平台当前告警、规则和采集目标状态', '监控告警', `请只读检查 ${target} 的监控平台状态：当前告警、采集目标在线性、规则/通知异常、近期错误和需要优先处置的对象。`)]
  }
  if (category === 'service') {
    return [command('service-probe-health', '/service 服务探测', '检查应用、端口、DNS、证书、消息和网络服务可用性', '服务探测', `请只读检查 ${target} 的服务可用性：协议握手、响应时间、证书/解析/端口状态、错误响应、重试和依赖线索。必须使用当前会话的服务探测或协议工具，不要发起大范围扫描。`)]
  }
  if (category === 'discovery') {
    return [command('discovery-health', '/discovery 服务发现', '检查注册中心、服务发现和目标发现状态', '服务发现', `请只读检查 ${target} 的服务发现状态：注册服务清单、健康实例、异常节点、同步延迟、认证/API 错误和依赖线索。必须使用当前协议工具，不要注册、下线或修改服务。`)]
  }
  if (category === 'security') {
    return [command('security-platform-health', '/security 安全平台健康', '检查安全、身份、堡垒机和审计平台状态', '安全身份', `请只读检查 ${target} 的安全/身份平台健康：认证连通、策略/审计事件、账号或目录状态、近期错误、告警和高风险配置。必须使用当前协议工具，不要修改策略或账号。`)]
  }
  if (category === 'oob') {
    return [command('oob-hardware', '/hardware 硬件健康', '检查带外管理、硬件传感器、电源、风扇和磁盘', '带外/硬件', `请只读检查 ${target} 的硬件健康：电源、风扇、温度、磁盘、RAID、日志事件和保修/型号线索，按严重程度输出。`)]
  }
  if (category === 'ai') {
    return [command('ai-platform-health', '/ai AI 平台健康', '检查模型服务、端点、配额、错误和延迟', 'AI 平台', `请只读检查 ${target} 的 AI/模型平台健康：端点连通、模型清单、错误率、延迟、配额、鉴权和外部依赖。不要调用写接口或触发大规模推理。`)]
  }
  if (category === 'cicd') {
    return [command('cicd-health', '/cicd 发布平台健康', '检查任务、队列、执行器、凭据状态和近期失败', 'CI/CD', `请只读检查 ${target} 的 CI/CD 平台健康：任务队列、执行器/Agent、近期失败、凭据或仓库连通、插件和发布风险。不要触发构建或发布。`)]
  }
  if (text(session.protocol) === 'http_api') {
    return [command('api-health', '/api-health API 健康', '检查 HTTP/API 连通、认证、关键端点和错误摘要', '平台/API', `请只读检查 ${target} 的 API 健康状态：认证方式、关键端点连通性、版本信息、错误响应和可观测性线索。不要调用写接口。`, false)]
  }
  return []
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
    ...domainShortcutCommands(session, activeTools, target),
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
