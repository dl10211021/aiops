import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { connectSession, testConnection, getSkillRegistry, batchImportAssets } from '@/api/client'
import type { SkillInfo } from '@/types'

const ASSET_CATEGORIES = [
  { id: 'os', label: '操作系统与主机 (OS & Compute)' },
  { id: 'db', label: '数据库与缓存 (Database & Cache)' },
  { id: 'cloud', label: '虚拟化与云原生 (Virtualization)' },
  { id: 'network', label: '网络与安全 (Network & Security)' },
  { id: 'monitor', label: '监控与告警 (Monitoring & APM)' },
  { id: 'oob', label: '硬件动环 (Hardware & OOB)' },
]

const ASSET_SUB_TYPES: Record<string, { id: string, label: string, protocol: string, defaultPort: number }[]> = {
  os: [
    { id: 'linux', label: 'Linux / Unix (SSH)', protocol: 'ssh', defaultPort: 22 },
    { id: 'winrm', label: 'Windows Server (WinRM)', protocol: 'winrm', defaultPort: 5985 },
  ],
  db: [
    { id: 'mysql', label: 'MySQL', protocol: 'database', defaultPort: 3306 },
    { id: 'oracle', label: 'Oracle', protocol: 'database', defaultPort: 1521 },
    { id: 'postgresql', label: 'PostgreSQL', protocol: 'database', defaultPort: 5432 },
    { id: 'mssql', label: 'SQL Server', protocol: 'database', defaultPort: 1433 },
    { id: 'redis', label: 'Redis', protocol: 'database', defaultPort: 6379 },
    { id: 'mongodb', label: 'MongoDB', protocol: 'database', defaultPort: 27017 },
    { id: 'elasticsearch', label: 'ElasticSearch', protocol: 'database', defaultPort: 9200 },
  ],
  cloud: [
    { id: 'vmware', label: 'VMware vCenter/ESXi', protocol: 'api', defaultPort: 443 },
    { id: 'k8s', label: 'Kubernetes (K8s)', protocol: 'api', defaultPort: 6443 },
    { id: 'zstack', label: 'ZStack', protocol: 'api', defaultPort: 5000 },
  ],
  network: [
    { id: 'f5', label: 'F5 BIG-IP', protocol: 'api', defaultPort: 443 },
    { id: 'switch', label: 'Switch / Router', protocol: 'ssh', defaultPort: 22 },
  ],
  monitor: [
    { id: 'zabbix', label: 'Zabbix', protocol: 'api', defaultPort: 80 },
    { id: 'prometheus', label: 'Prometheus', protocol: 'api', defaultPort: 9090 },
  ],
  oob: [
    { id: 'snmp', label: 'SNMP', protocol: 'api', defaultPort: 161 },
    { id: 'redfish', label: 'Redfish/iLO/iDRAC', protocol: 'api', defaultPort: 443 },
  ]
}

export default function ConnectionModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addSession = useStore((s) => s.addSession)
  const addToast = useStore((s) => s.addToast)
  const setView = useStore((s) => s.setView)

  const [form, setForm] = useState({
    host: '', port: 22, username: 'root', password: '',
    remark: '', protocol: 'ssh', agent_profile: 'default',
    group_name: '未分组', allow_modifications: false,
    target_scope: 'asset', category: 'os', sub_type: 'linux',
    extra_args: {} as Record<string, unknown>,
  })
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set())
  const [testing, setTesting] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)

  // Load skills and check for prefill
  useEffect(() => {
    getSkillRegistry().then((r) => setSkills(r.data.registry?.filter((s) => !s.is_market) || [])).catch(() => {})

    const prefill = sessionStorage.getItem('prefill_asset')
    if (prefill) {
      try {
        const a = JSON.parse(prefill)
          setForm({
            host: a.host || '', port: a.port || 22, username: a.username || 'root',
            password: a.password || '', remark: a.remark || '', protocol: a.protocol || 'ssh',
            agent_profile: a.agent_profile || 'default', group_name: (a.tags && a.tags[0]) || '未分组',
            allow_modifications: false, target_scope: 'asset', extra_args: a.extra_args || {},
            category: a.category || 'os', sub_type: a.sub_type || 'linux',
          })
        if (a.skills) setSelectedSkills(new Set(a.skills))
      } catch { /* ignore */ }
      sessionStorage.removeItem('prefill_asset')
    }
  }, [])

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const isGlobal = form.target_scope === 'global'
      const host = isGlobal ? 'global' : form.host
      const username = isGlobal ? 'admin' : form.username
      
      const res = await testConnection({
        host, port: form.port, username,
        password: form.password, protocol: isGlobal ? 'api' : form.protocol,
        extra_args: form.extra_args, active_skills: [],
        target_scope: form.target_scope,
        scope_value: form.target_scope === 'group' ? form.group_name : host,
      })
      setTestResult({ ok: res.status === 'success', msg: res.message })
    } catch (e: unknown) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : 'Test failed' })
    }
    setTesting(false)
  }

  const handleConnect = async () => {
    const isGlobal = form.target_scope === 'global'
    const host = isGlobal ? 'global' : form.host
    const username = isGlobal ? 'admin' : form.username

    if (!isGlobal && !form.host) { addToast('请输入主机地址', 'error'); return }
    setConnecting(true)
    try {
      const res = await connectSession({
        ...form,
        host, username, protocol: isGlobal ? 'api' : form.protocol,
        active_skills: Array.from(selectedSkills),
        tags: [form.group_name],
        target_scope: form.target_scope,
        scope_value: form.target_scope === 'group' ? form.group_name : host,
      })
      const sid = res.data.session_id
      addSession({
        id: sid, host, remark: form.remark,
        isReadWriteMode: form.allow_modifications,
        skills: Array.from(selectedSkills), agentProfile: form.agent_profile,
        user: username, protocol: isGlobal ? 'api' : form.protocol,
        extra_args: form.extra_args, heartbeatEnabled: false,
        tags: [form.group_name], messages: [], isStreaming: false,
      })
      addToast(`已连接到 ${form.remark || host}`, 'success')
      closeModal()
      setView('chat')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '连接失败', 'error')
    }
    setConnecting(false)
  }

  const handleSaveOnly = async () => {
    const isGlobal = form.target_scope === 'global'
    const host = isGlobal ? 'global' : form.host
    const username = isGlobal ? 'admin' : form.username

    if (!isGlobal && !form.host) { addToast('请输入主机地址', 'error'); return }
    setConnecting(true)
    try {
      await batchImportAssets([{
        host, username, password: form.password, port: form.port,
        protocol: isGlobal ? 'api' : form.protocol,
        remark: form.remark, agent_profile: form.agent_profile,
        extra_args: form.extra_args, skills: Array.from(selectedSkills),
        tags: [form.group_name]
      }])
      addToast(`已保存资产 ${form.remark || host}`, 'success')
      closeModal()
      if (useStore.getState().currentView !== 'assets') {
        setView('assets')
      }
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存失败', 'error')
    }
    setConnecting(false)
  }

  const toggleSkill = (id: string) => {
    const next = new Set(selectedSkills)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelectedSkills(next)
  }

  const isGlobal = form.target_scope === 'global'

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[560px] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">⚡ 新建连接</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>

        <div className="space-y-3">
          {/* Target Scope selector */}
          <div className="flex gap-4 mb-2 pb-2 border-b border-ops-surface0">
            {[
              { value: 'asset', label: '单台资产' },
              { value: 'group', label: '资产组别' },
              { value: 'global', label: '全局会话' },
            ].map((p) => (
              <label key={p.value} className="flex items-center gap-1.5 text-sm font-medium text-ops-subtext cursor-pointer hover:text-ops-text">
                <input type="radio" name="target_scope" value={p.value} checked={form.target_scope === p.value}
                  onChange={(e) => setForm({ ...form, target_scope: e.target.value })}
                  className="accent-ops-accent" />
                {p.label}
              </label>
            ))}
          </div>

          {/* Asset Taxonomy selector */}
          {form.target_scope !== 'global' && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {ASSET_CATEGORIES.map((c) => (
                  <button key={c.id} 
                    onClick={() => {
                      const firstSub = ASSET_SUB_TYPES[c.id][0]
                      setForm({ ...form, category: c.id, sub_type: firstSub.id, protocol: firstSub.protocol, port: firstSub.defaultPort })
                    }}
                    className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${form.category === c.id ? 'bg-ops-accent/20 text-ops-accent' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}>
                    {c.label}
                  </button>
                ))}
              </div>
              
              {ASSET_SUB_TYPES[form.category] && (
                <div className="flex flex-wrap gap-2">
                  {ASSET_SUB_TYPES[form.category].map((s) => (
                    <button key={s.id} 
                      onClick={() => setForm({ 
                        ...form, 
                        sub_type: s.id, 
                        protocol: s.protocol, 
                        port: s.defaultPort,
                        extra_args: form.category === 'db' ? { ...form.extra_args, db_type: s.id } : form.extra_args
                      })}
                      className={`text-xs px-3 py-1.5 rounded-lg transition-colors border ${form.sub_type === s.id ? 'bg-ops-accent/10 border-ops-accent text-ops-accent' : 'border-ops-surface1 bg-transparent text-ops-subtext hover:text-ops-text hover:border-ops-surface2'}`}>
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {form.target_scope !== 'global' && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-ops-subtext">主机地址 {form.target_scope === 'group' && '(代表主机)'}</label>
                  <input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    placeholder="192.168.1.100" />
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">端口</label>
                  <input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 22 })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-ops-subtext">用户名</label>
                  <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">密码</label>
                  <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                </div>
              </div>
            </>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-ops-subtext">备注/别名</label>
              <input value={form.remark} onChange={(e) => setForm({ ...form, remark: e.target.value })}
                className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                placeholder="生产-WebServer-01" />
            </div>
            <div>
              <label className="text-xs text-ops-subtext">分组</label>
              <input value={form.group_name} onChange={(e) => setForm({ ...form, group_name: e.target.value })}
                className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                placeholder="未分组" />
            </div>
          </div>

          {/* Database extra fields */}
          {form.target_scope !== 'global' && form.category === 'db' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-ops-subtext">数据库/SID</label>
                <input value={(form.extra_args.database as string) || ''}
                  onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, database: e.target.value } })}
                  className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
              </div>
            </div>
          )}

          {/* Skills */}
          {skills.length > 0 && (
            <div>
              <label className="text-xs text-ops-subtext mb-1.5 block">挂载技能</label>
              <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
                {skills.map((sk) => (
                  <button key={sk.id} onClick={() => toggleSkill(sk.id)}
                    className={`text-[11px] px-2 py-1 rounded transition-colors ${selectedSkills.has(sk.id) ? 'bg-ops-accent/20 text-ops-accent' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}>
                    {sk.name || sk.id}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Permission toggle */}
          <label className="flex items-center gap-2 text-sm text-ops-subtext cursor-pointer">
            <input type="checkbox" checked={form.allow_modifications}
              onChange={(e) => setForm({ ...form, allow_modifications: e.target.checked })}
              className="accent-ops-accent" />
            允许 AI 执行修改操作（读写模式）
          </label>

          {/* Test result */}
          {testResult && (
            <div className={`text-xs p-2 rounded-lg ${testResult.ok ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
              {testResult.msg}
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex justify-between mt-5">
          <button onClick={handleSaveOnly} disabled={connecting || (!isGlobal && !form.host)}
            className="px-4 py-2 text-sm bg-ops-surface0 text-ops-subtext rounded-lg hover:text-ops-text disabled:opacity-40 transition-colors">
            💾 仅保存资产
          </button>
          <div className="flex gap-2">
            <button onClick={handleTest} disabled={testing || (!isGlobal && !form.host)}
              className="px-4 py-2 text-sm bg-ops-surface0 text-ops-subtext rounded-lg hover:text-ops-text disabled:opacity-40 transition-colors">
              {testing ? '测试中...' : '🔌 测试'}
            </button>
            <button onClick={handleConnect} disabled={connecting || (!isGlobal && !form.host)}
              className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors">
              {connecting ? '连接中...' : '⚡ 连接'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
