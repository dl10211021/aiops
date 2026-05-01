import type { SafetyPolicyDecision } from '@/types'

export type CategoryKey = 'linux' | 'windows' | 'sql' | 'redis' | 'memcached' | 'mongodb' | 'http' | 'network' | 'local' | 'skill_change'
export type Decision = 'approval' | 'deny'
export type MatcherType = 'contains' | 'prefix' | 'equals' | 'regex' | 'http_method' | 'platform_action' | 'sql_action' | 'linux_action' | 'windows_action' | 'redis_action' | 'memcached_action' | 'mongodb_action' | 'network_action'
export type PolicyPanel = 'actions' | 'network-boundary' | 'test' | 'advanced'

export type DomainDefinition = {
  id: string
  label: string
  icon: string
  category: CategoryKey
  platforms: string[]
  objects: string
  hint: string
  examples: Array<{ action: string; decision: 'allow' | 'approval' | 'deny'; example: string }>
}

export type OperationPreset = {
  name: string
  platform: string
  resource: string
  action: string
  decision: Decision
  matcherType: MatcherType
  matcherValue: string
  reason: string
}

export type ActionRuleOption = {
  id: string
  label: string
  description: string
  example: string
  defaultDecision: SafetyPolicyDecision
}

export const CATEGORY_LABELS: Record<CategoryKey, string> = {
  linux: 'Linux / KVM',
  windows: 'Windows WinRM',
  sql: '数据库 SQL',
  redis: 'Redis',
  memcached: 'Memcached',
  mongodb: 'MongoDB',
  http: 'HTTP / API 平台',
  network: '交换机 / 网络设备',
  local: '本地 Skill 脚本',
  skill_change: '技能变更',
}

export const DECISION_LABELS = {
  allow: { label: '允许执行', className: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' },
  approval: { label: '需要审批', className: 'border-yellow-300/30 bg-yellow-300/10 text-yellow-200' },
  deny: { label: '禁止执行', className: 'border-red-400/30 bg-red-400/10 text-red-200' },
}

export const ACTION_RULE_DOMAIN_OPTIONS = [
  { value: 'linux', label: 'Linux / SSH 命令', placeholder: 'linux.read.logs' },
  { value: 'windows', label: 'Windows / WinRM 命令', placeholder: 'windows.read.eventlog' },
  { value: 'sql', label: '数据库 SQL', placeholder: 'sql.instance_admin' },
  { value: 'http', label: '平台 / API 动作', placeholder: 's3.download_object' },
  { value: 'network', label: '网络设备命令', placeholder: 'network.interface.change' },
  { value: 'redis', label: 'Redis 命令', placeholder: 'redis.flush' },
  { value: 'memcached', label: 'Memcached 命令', placeholder: 'memcached.flush' },
  { value: 'mongodb', label: 'MongoDB 操作', placeholder: 'mongodb.find' },
  { value: 'local', label: '平台本地能力', placeholder: 'platform.evolve_skill' },
]

export const POLICY_PANELS: Array<{ id: PolicyPanel; label: string; hint: string }> = [
  { id: 'actions', label: '动作权限', hint: '统一配置读写权限' },
  { id: 'network-boundary', label: '网络边界', hint: '限制 AI 活动范围' },
  { id: 'test', label: '模拟测试', hint: '保存前先预演' },
  { id: 'advanced', label: '高级设置', hint: '底层兜底字段' },
]

export const LINUX_ACTION_OPTIONS: ActionRuleOption[] = [
  { id: 'linux.read.resource', label: '读取资源状态', description: 'CPU、内存、磁盘、负载、系统版本等基础巡检。', example: 'free -m / df -hT / lscpu', defaultDecision: 'allow' },
  { id: 'linux.read.logs', label: '读取系统日志', description: '查看 journalctl、dmesg 或 /var/log 下的日志。', example: 'journalctl -p err -n 100', defaultDecision: 'allow' },
  { id: 'linux.read.service', label: '查看服务状态', description: '查看服务状态、失败服务、服务单元文件。', example: 'systemctl status sshd', defaultDecision: 'allow' },
  { id: 'linux.read.cron', label: '查看计划任务', description: '读取 crontab 和计划任务配置。', example: 'crontab -l', defaultDecision: 'allow' },
  { id: 'linux.read.history', label: '查看历史记录', description: '查看登录历史、重启历史。', example: 'last reboot', defaultDecision: 'allow' },
  { id: 'linux.read.network', label: '查看网络状态', description: '查看端口、路由、网卡和连接状态。', example: 'ss -tulpn / ip addr', defaultDecision: 'allow' },
  { id: 'linux.read.file', label: '读取普通文件', description: '读取普通配置或文本文件。', example: 'cat /etc/os-release', defaultDecision: 'allow' },
  { id: 'linux.read.filesystem', label: '读取文件系统/挂载状态', description: '查看 fstab、当前挂载表、块设备、IO 调度器等只读状态。', example: 'mount / findmnt / cat /etc/fstab', defaultDecision: 'allow' },
  { id: 'linux.sensitive.read', label: '读取敏感文件', description: '读取账号、私钥、影子口令等敏感内容。', example: 'cat /etc/shadow', defaultDecision: 'approval' },
  { id: 'linux.network.probe', label: '主动网络访问', description: '对目标发起 ping、curl、nc、nmap、ssh 等连接或探测。', example: 'curl http://10.0.0.1:9100/metrics', defaultDecision: 'approval' },
  { id: 'linux.service.change', label: '变更服务状态', description: '启动、停止、重启、重载、启用或禁用服务。', example: 'systemctl restart nginx', defaultDecision: 'approval' },
  { id: 'linux.file.write', label: '写入文件', description: '创建、覆盖、追加、移动或复制文件。', example: 'echo ok > /tmp/a.txt', defaultDecision: 'approval' },
  { id: 'linux.file.delete', label: '删除文件', description: '删除文件或目录。', example: 'rm /tmp/a.txt', defaultDecision: 'approval' },
  { id: 'linux.permission.change', label: '修改权限', description: '修改文件属主、权限或 ACL。', example: 'chmod 600 app.conf', defaultDecision: 'approval' },
  { id: 'linux.package.change', label: '软件包变更', description: '安装、删除或升级系统软件包。', example: 'yum install nginx', defaultDecision: 'approval' },
  { id: 'linux.user.change', label: '账号变更', description: '新增、删除或修改系统用户和用户组。', example: 'useradd ops', defaultDecision: 'approval' },
  { id: 'linux.disk.change', label: '磁盘/挂载变更', description: '格式化、分区、挂载、卸载、启停 swap。', example: 'mkfs.ext4 /dev/sdb', defaultDecision: 'approval' },
  { id: 'linux.network.change', label: '网络配置变更', description: '修改防火墙、路由、网卡或网络规则。', example: 'firewall-cmd --add-port=80/tcp', defaultDecision: 'approval' },
  { id: 'linux.system.power', label: '系统电源操作', description: '重启、关机、断电或切换运行级别。', example: 'sudo reboot', defaultDecision: 'approval' },
]

export const WINDOWS_ACTION_OPTIONS: ActionRuleOption[] = [
  { id: 'windows.read.info', label: '读取系统信息', description: '系统版本、补丁、硬件、CIM/WMI 等基础状态。', example: 'Get-CimInstance Win32_OperatingSystem', defaultDecision: 'allow' },
  { id: 'windows.read.service', label: '查看服务状态', description: '读取服务列表、状态或配置，不改变服务运行状态。', example: 'Get-Service | Where-Object {$_.Status -ne "Running"}', defaultDecision: 'allow' },
  { id: 'windows.read.eventlog', label: '读取事件日志', description: '查看 Windows 事件日志或系统错误。', example: 'Get-WinEvent -FilterHashtable @{LogName="System"; Level=1,2}', defaultDecision: 'allow' },
  { id: 'windows.read.process', label: '查看进程', description: '查看进程、任务或资源占用情况。', example: 'Get-Process | Sort-Object CPU -Descending', defaultDecision: 'allow' },
  { id: 'windows.read.network', label: '查看网络状态', description: '查看网卡、连接、路由、防火墙规则等本机网络状态。', example: 'Get-NetTCPConnection / ipconfig / netstat', defaultDecision: 'allow' },
  { id: 'windows.read.file', label: '读取普通文件', description: '读取普通配置或文本文件。', example: 'Get-Content C:\\Windows\\System32\\drivers\\etc\\hosts', defaultDecision: 'allow' },
  { id: 'windows.read.virtualization', label: '读取 Hyper-V 状态', description: '查看虚拟机、虚拟交换机、磁盘或复制状态。', example: 'Get-VM / Get-VMSwitch', defaultDecision: 'allow' },
  { id: 'windows.sensitive.read', label: '读取敏感数据', description: '读取 SAM、SYSTEM、SECURITY、NTDS 或私钥等敏感内容。', example: 'Get-Content C:\\Windows\\System32\\config\\SAM', defaultDecision: 'approval' },
  { id: 'windows.network.probe', label: '主动网络访问', description: '通过 ping、Test-NetConnection、Invoke-WebRequest 等主动连接或探测其他地址。', example: 'Test-NetConnection 10.0.0.1 -Port 443', defaultDecision: 'approval' },
  { id: 'windows.service.change', label: '变更服务状态', description: '启动、停止、重启、创建、删除或修改服务配置。', example: 'Restart-Service Spooler', defaultDecision: 'approval' },
  { id: 'windows.process.stop', label: '终止进程', description: '停止 Windows 进程或任务。', example: 'Stop-Process -Name app', defaultDecision: 'approval' },
  { id: 'windows.file.write', label: '写入文件', description: '创建、覆盖、追加、复制、移动或重命名文件。', example: 'Set-Content C:\\temp\\app.conf', defaultDecision: 'approval' },
  { id: 'windows.file.delete', label: '删除文件', description: '删除文件或目录。', example: 'Remove-Item C:\\temp\\old.log', defaultDecision: 'approval' },
  { id: 'windows.permission.change', label: '修改权限', description: '修改 ACL、文件权限或访问控制。', example: 'icacls C:\\app /grant ops:F', defaultDecision: 'approval' },
  { id: 'windows.user.change', label: '账号/组变更', description: '新增、删除或修改本地用户、本地组或组成员。', example: 'New-LocalUser ops', defaultDecision: 'approval' },
  { id: 'windows.registry.change', label: '注册表变更', description: '新增、删除或修改注册表键值。', example: 'Set-ItemProperty HKLM:\\Software\\App', defaultDecision: 'approval' },
  { id: 'windows.firewall.change', label: '防火墙变更', description: '新增、删除或修改 Windows 防火墙规则。', example: 'New-NetFirewallRule -DisplayName App', defaultDecision: 'approval' },
  { id: 'windows.package.change', label: '软件/角色变更', description: '安装、卸载或修改 Windows 功能、模块或软件包。', example: 'Install-WindowsFeature Web-Server', defaultDecision: 'approval' },
  { id: 'windows.system.power', label: '系统电源操作', description: '重启、关机或关闭计算机。', example: 'Restart-Computer -Force', defaultDecision: 'approval' },
  { id: 'hyperv.vm.power', label: 'Hyper-V 虚拟机电源操作', description: '启动、停止、重启、挂起或保存虚拟机。', example: 'Restart-VM -Name prod-01', defaultDecision: 'approval' },
  { id: 'hyperv.vm.change', label: 'Hyper-V 虚拟机变更', description: '创建、修改、检查点、恢复或迁移虚拟机资源。', example: 'Checkpoint-VM -Name prod-01', defaultDecision: 'approval' },
  { id: 'hyperv.vm.delete', label: '删除 Hyper-V 虚拟机', description: '删除虚拟机资源，通常不可逆。', example: 'Remove-VM -Name old-vm -Force', defaultDecision: 'deny' },
]

export const DEFAULT_NETWORK_BOUNDARY = {
  enabled: false,
  active_cidrs: [],
  readonly_cidrs: [],
  blocked_cidrs: [],
  allowed_hosts: [],
  blocked_hosts: [],
  block_unknown_targets: false,
}

export const DEFAULT_FORM = {
  name: '',
  platform: '',
  resource: '',
  action: '',
  matcherType: 'contains' as MatcherType,
  matcherValue: '',
  decision: 'approval' as Decision,
  reason: '',
  scopeType: 'all',
  scopeValue: '',
  sources: ['chat', 'cron', 'alert'],
}

export const DEFAULT_TEST_FORM = {
  input: '',
  method: 'GET',
  mode: 'readonly' as 'readonly' | 'readwrite',
}

export const DEFAULT_CUSTOM_ACTION_RULE = {
  domain: '',
  actionId: '',
  decision: 'approval' as SafetyPolicyDecision,
}

export const SCOPE_OPTIONS = [
  { value: 'all', label: '全部资产', placeholder: '全部资产无需填写' },
  { value: 'tag', label: '资产标签', placeholder: '例如：生产、核心、涉密' },
  { value: 'environment', label: '环境', placeholder: '例如：prod、uat、dev' },
  { value: 'asset_group', label: '资产组', placeholder: '例如：核心数据库组' },
  { value: 'asset_type', label: '资产类型', placeholder: '例如：oracle、vmware、s3' },
  { value: 'protocol', label: '接入协议', placeholder: '例如：ssh、oracle、s3、winrm' },
  { value: 'platform', label: '平台名称', placeholder: '例如：VMware、OpenStack、MinIO' },
  { value: 'data_center', label: '数据中心/机房', placeholder: '例如：上海-AZ1' },
  { value: 'tenant', label: '租户/业务线', placeholder: '例如：支付、风控、ERP' },
  { value: 'asset', label: '单资产', placeholder: '例如：172.17.10.2 或资产 ID' },
]

export const SOURCE_OPTIONS = [
  { value: 'chat', label: 'AI 会话' },
  { value: 'cron', label: '自动巡检' },
  { value: 'alert', label: '告警联动' },
  { value: 'api', label: '外部 API' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'heartbeat', label: '心跳任务' },
  { value: 'sub_agent', label: '子 Agent' },
]

export const MATCHER_LABELS: Record<string, string> = {
  contains: '包含关键词',
  command_prefix: '命令开头',
  prefix: '命令开头',
  equals: '完全等于',
  regex: '正则匹配',
  http_method: 'HTTP 方法',
  platform_action: '平台动作',
  sql_action: 'SQL 动作',
  linux_action: 'Linux 动作',
  windows_action: 'Windows 动作',
  redis_action: 'Redis 动作',
  memcached_action: 'Memcached 动作',
  mongodb_action: 'MongoDB 动作',
  network_action: '网络设备动作',
  api_path_contains: 'API 路径包含',
}

export const SQL_ACTION_OPTIONS = [
  { value: 'sql.data_write', label: '数据写入', hint: 'INSERT / UPDATE / DELETE / MERGE / REPLACE' },
  { value: 'sql.schema_change', label: '结构变更', hint: 'CREATE / ALTER / DROP / TRUNCATE / RENAME' },
  { value: 'sql.instance_admin', label: '实例管理', hint: 'ALTER SYSTEM / SWITCH LOGFILE / STARTUP / SHUTDOWN' },
  { value: 'sql.privilege_change', label: '账号权限', hint: 'GRANT / REVOKE / CREATE USER / ALTER USER' },
  { value: 'sql.transaction', label: '事务控制', hint: 'COMMIT / ROLLBACK' },
  { value: 'sql.dangerous_drop', label: '高危删除', hint: 'DROP DATABASE / DROP USER / TRUNCATE TABLE' },
]

export const SQL_ACTION_RULE_OPTIONS: ActionRuleOption[] = [
  { id: 'sql.read', label: '数据库读取', description: '查询数据、查看元数据、执行解释计划，不直接改变数据库状态。', example: 'SELECT / SHOW / DESCRIBE / EXPLAIN', defaultDecision: 'allow' },
  { id: 'sql.data_write', label: '数据写入', description: 'INSERT、UPDATE、DELETE、MERGE、REPLACE 或过程调用，会改变业务数据。', example: 'UPDATE orders SET status = 1', defaultDecision: 'approval' },
  { id: 'sql.schema_change', label: '结构变更', description: 'CREATE、ALTER、DROP、TRUNCATE、RENAME 会改变库表对象结构。', example: 'ALTER TABLE orders ADD remark VARCHAR2(200)', defaultDecision: 'approval' },
  { id: 'sql.instance_admin', label: '实例级管理', description: '日志切换、实例启停、检查点等动作会影响数据库运行状态。', example: 'ALTER SYSTEM SWITCH LOGFILE', defaultDecision: 'approval' },
  { id: 'sql.privilege_change', label: '账号权限', description: 'GRANT、REVOKE、用户创建或修改会改变访问边界。', example: 'GRANT SELECT ON app.orders TO readonly_user', defaultDecision: 'approval' },
  { id: 'sql.transaction', label: '事务控制', description: 'COMMIT 或 ROLLBACK 会影响当前事务上下文。', example: 'COMMIT / ROLLBACK', defaultDecision: 'approval' },
  { id: 'sql.dangerous_drop', label: '高危删除', description: '删库、删用户、删表空间或清表属于高危不可逆动作。', example: 'DROP USER old_user CASCADE', defaultDecision: 'deny' },
]

export const REDIS_ACTION_RULE_OPTIONS: ActionRuleOption[] = [
  { id: 'redis.read', label: 'Redis 读取', description: 'GET、MGET、SCAN、INFO、DBSIZE、TTL 等读取或状态查询。', example: 'INFO / GET app:key', defaultDecision: 'allow' },
  { id: 'redis.key_write', label: '写入 Key', description: 'SET、HSET、LPUSH、SADD、ZADD 等会写入或修改数据。', example: 'SET app:key value', defaultDecision: 'approval' },
  { id: 'redis.key_delete', label: '删除 Key', description: 'DEL、UNLINK、RENAME 等会删除或移动数据。', example: 'DEL app:key', defaultDecision: 'approval' },
  { id: 'redis.expire', label: '修改过期时间', description: 'EXPIRE、PERSIST、PEXPIRE 等会改变 Key 生命周期。', example: 'EXPIRE app:key 60', defaultDecision: 'approval' },
  { id: 'redis.counter_change', label: '计数变更', description: 'INCR、DECR 等会修改计数值。', example: 'INCR counter', defaultDecision: 'approval' },
  { id: 'redis.config_change', label: '配置变更', description: 'CONFIG SET、MODULE、SCRIPT FLUSH 等会改变实例配置或执行环境。', example: 'CONFIG SET maxmemory 1gb', defaultDecision: 'approval' },
  { id: 'redis.acl_change', label: 'ACL 变更', description: 'ACL SETUSER、ACL DELUSER 等会改变访问权限。', example: 'ACL SETUSER ops on', defaultDecision: 'approval' },
  { id: 'redis.persistence_change', label: '持久化变更', description: 'SAVE、BGSAVE、BGREWRITEAOF 等会影响持久化和性能。', example: 'BGSAVE', defaultDecision: 'approval' },
  { id: 'redis.replication_change', label: '主从/复制变更', description: 'REPLICAOF、SLAVEOF 等会改变复制拓扑。', example: 'REPLICAOF 10.0.0.2 6379', defaultDecision: 'approval' },
  { id: 'redis.flush', label: '清空数据', description: 'FLUSHALL 或 FLUSHDB 会清空库或实例数据。', example: 'FLUSHALL', defaultDecision: 'deny' },
]

export const MEMCACHED_ACTION_RULE_OPTIONS: ActionRuleOption[] = [
  { id: 'memcached.read', label: 'Memcached 读取', description: 'version、stats、get、gets 等只读命令。', example: 'stats / get app:key', defaultDecision: 'allow' },
  { id: 'memcached.key_write', label: '写入 Key', description: 'set、add、replace、append、prepend、cas 等会写入或修改数据。', example: 'set app:key 0 60 5', defaultDecision: 'approval' },
  { id: 'memcached.key_delete', label: '删除 Key', description: 'delete 会删除缓存数据。', example: 'delete app:key', defaultDecision: 'approval' },
  { id: 'memcached.counter_change', label: '计数/过期变更', description: 'incr、decr、touch、gat、gats 等会改变数据或过期时间。', example: 'incr counter 1', defaultDecision: 'approval' },
  { id: 'memcached.flush', label: '清空缓存', description: 'flush_all 会清空缓存数据。', example: 'flush_all', defaultDecision: 'deny' },
]

export const MONGODB_ACTION_RULE_OPTIONS: ActionRuleOption[] = [
  { id: 'mongodb.find', label: 'MongoDB 读取查询', description: 'find、count、distinct、listCollections、listIndexes、stats 等读取查询。', example: 'db.orders.find({status: "OPEN"}).limit(20)', defaultDecision: 'allow' },
  { id: 'mongodb.aggregate', label: 'MongoDB 聚合查询', description: 'aggregate 聚合可能消耗较多资源，默认需要审批。', example: 'db.orders.aggregate([...])', defaultDecision: 'approval' },
  { id: 'mongodb.write', label: 'MongoDB 数据写入', description: 'insert、update、replace、delete 等会改变集合数据。', example: 'db.orders.updateOne({...}, {$set: {...}})', defaultDecision: 'approval' },
  { id: 'mongodb.index_change', label: 'MongoDB 索引变更', description: 'createIndex、dropIndex 等会改变集合索引并影响性能。', example: 'db.orders.createIndex({createdAt: 1})', defaultDecision: 'approval' },
  { id: 'mongodb.admin', label: 'MongoDB 管理操作', description: '用户、角色、分片、副本集、参数等管理动作会改变实例状态。', example: 'rs.stepDown() / db.createUser(...)', defaultDecision: 'approval' },
  { id: 'mongodb.drop', label: 'MongoDB 高危删除', description: 'dropDatabase、dropCollection 等高危不可逆动作。', example: 'db.dropDatabase()', defaultDecision: 'deny' },
]

export const NETWORK_ACTION_RULE_OPTIONS: ActionRuleOption[] = [
  { id: 'network.read.status', label: '查看设备状态', description: '查看接口、路由、邻居、会话、版本等运行状态，不改变设备配置。', example: 'display interface brief / show ip route', defaultDecision: 'allow' },
  { id: 'network.read.config', label: '读取设备配置', description: '读取 running-config、current-configuration、startup-config 等配置内容，可能包含密钥或口令。', example: 'display current-configuration / show running-config', defaultDecision: 'approval' },
  { id: 'network.diagnostic', label: '网络诊断探测', description: '从网络设备发起 ping、traceroute、telnet 等主动探测或连接。', example: 'ping 10.0.0.1 / traceroute 8.8.8.8', defaultDecision: 'approval' },
  { id: 'network.config.mode', label: '进入配置模式', description: '进入可修改设备配置的模式。', example: 'system-view / configure terminal', defaultDecision: 'approval' },
  { id: 'network.interface.change', label: '接口配置变更', description: '进入接口配置、shutdown/undo shutdown、修改端口/VLAN/描述等。', example: 'interface GigabitEthernet0/0/1 / shutdown', defaultDecision: 'approval' },
  { id: 'network.route.change', label: '路由配置变更', description: '新增、删除或修改静态路由、默认路由或路由策略。', example: 'ip route-static 10.0.0.0 255.255.255.0 172.17.1.1', defaultDecision: 'approval' },
  { id: 'network.acl_nat.change', label: 'ACL/NAT/安全策略变更', description: '修改 ACL、访问控制、防火墙策略、NAT 或安全域规则。', example: 'acl 3000 / access-list 101 permit tcp any any', defaultDecision: 'approval' },
  { id: 'network.save_config', label: '保存设备配置', description: '把当前运行配置固化到启动配置。', example: 'save / write memory / copy running-config startup-config', defaultDecision: 'approval' },
  { id: 'network.file_transfer', label: '设备文件传输', description: '通过 TFTP、FTP、SCP 或 copy 上传下载镜像、配置或文件。', example: 'copy tftp flash / scp config.cfg', defaultDecision: 'approval' },
  { id: 'network.reset', label: '重启或清空配置', description: '重启设备、清空启动配置、格式化 flash 等高危动作。', example: 'reload / reset saved-configuration / erase startup-config', defaultDecision: 'deny' },
]

export const HTTP_ACTION_RULE_OPTIONS: ActionRuleOption[] = [
  { id: 'k8s.delete_namespace', label: '删除 Namespace', description: '批量删除命名空间内资源。', example: 'DELETE /api/v1/namespaces/prod', defaultDecision: 'deny' },
  { id: 'k8s.scale_deployment', label: 'K8s 扩缩容', description: '调整 Deployment 副本数。', example: 'PATCH /apis/apps/v1/deployments/app/scale', defaultDecision: 'approval' },
  { id: 'k8s.delete_pod', label: '删除 Pod', description: '终止正在运行的业务实例。', example: 'DELETE /api/v1/namespaces/default/pods/nginx', defaultDecision: 'approval' },
  { id: 'k8s.delete_secret', label: '删除 Secret', description: '影响认证和访问凭据。', example: 'DELETE /api/v1/namespaces/default/secrets/db', defaultDecision: 'deny' },
  { id: 'virtualization.delete_vm', label: '删除虚拟机', description: '删除虚拟机资源，通常不可逆。', example: 'DELETE /vms/prod-01', defaultDecision: 'deny' },
  { id: 'virtualization.reboot_vm', label: '重启虚拟机', description: '影响虚拟机上层业务可用性。', example: 'POST /vms/prod-01/reboot', defaultDecision: 'approval' },
  { id: 'virtualization.migrate_vm', label: '迁移虚拟机', description: '改变虚拟机运行位置和资源状态。', example: 'POST /vms/prod-01/migrate', defaultDecision: 'approval' },
  { id: 'virtualization.rollback_snapshot', label: '快照回滚', description: '改变系统和数据状态。', example: 'POST /vms/prod-01/snapshots/rollback', defaultDecision: 'approval' },
  { id: 'nacos.publish_config', label: '发布配置', description: '影响依赖该配置的服务。', example: 'POST /nacos/v1/cs/configs', defaultDecision: 'approval' },
  { id: 'kafka.delete_topic', label: '删除 Topic', description: '可能造成消息数据丢失。', example: 'DELETE /topics/payments', defaultDecision: 'deny' },
  { id: 'yarn.kill_application', label: '停止大数据任务', description: '中断数据处理链路。', example: 'PUT /ws/v1/cluster/apps/app_1/state=KILLED', defaultDecision: 'approval' },
  { id: 'bigdata.delete_partition', label: '删除数据分区', description: '删除分区数据，可能不可恢复。', example: 'DELETE /tables/fact/partitions/dt=2026', defaultDecision: 'deny' },
  { id: 'cicd.deploy_prod', label: '生产发布', description: '改变线上版本或生产流量。', example: 'POST /job/prod-deploy/build', defaultDecision: 'approval' },
  { id: 'argocd.rollback', label: '回滚部署', description: '改变线上应用版本。', example: 'POST /applications/app/rollback', defaultDecision: 'approval' },
  { id: 'artifact.delete_release', label: '删除制品', description: '影响回滚和审计追溯。', example: 'DELETE /repository/releases/app.jar', defaultDecision: 'deny' },
  { id: 'ai.stop_training_job', label: '停止训练任务', description: '中断训练或计算过程。', example: 'POST /jobs/123/stop', defaultDecision: 'approval' },
  { id: 'ai.release_gpu', label: '释放 GPU', description: '可能影响运行中的训练或推理任务。', example: 'POST /gpu/allocations/1/release', defaultDecision: 'approval' },
  { id: 'mlflow.delete_model_version', label: '删除模型版本', description: '影响推理服务和模型追溯。', example: 'DELETE /models/prod/versions/12', defaultDecision: 'deny' },
  { id: 's3.download_object', label: '下载对象', description: '对象可能包含敏感数据。', example: 'GET /bucket/object.zip', defaultDecision: 'approval' },
  { id: 's3.change_bucket_policy', label: '修改 Bucket 策略', description: '改变对象存储访问边界。', example: 'PUT /bucket?policy', defaultDecision: 'approval' },
  { id: 's3.public_bucket', label: '公开 Bucket', description: '可能造成数据泄露。', example: 'PUT /bucket?publicAccessBlock', defaultDecision: 'deny' },
  { id: 's3.delete_bucket', label: '删除 Bucket', description: '删除对象存储命名空间。', example: 'DELETE /bucket', defaultDecision: 'deny' },
  { id: 's3.delete_object', label: '删除对象', description: '删除对象数据。', example: 'DELETE /bucket/a.log', defaultDecision: 'approval' },
  { id: 'alertmanager.create_silence', label: '创建告警静默', description: '可能掩盖真实故障。', example: 'POST /api/v2/silences', defaultDecision: 'approval' },
  { id: 'monitoring.update_rule', label: '修改监控规则', description: '影响监控覆盖和告警质量。', example: 'PUT /api/ruler/rules/app', defaultDecision: 'approval' },
  { id: 'monitoring.delete_rule', label: '删除监控规则', description: '造成监控缺口。', example: 'DELETE /api/ruler/rules/app', defaultDecision: 'deny' },
]
