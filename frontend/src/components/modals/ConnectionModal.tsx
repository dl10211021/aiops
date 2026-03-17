import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { connectSession, testConnection, getSkillRegistry } from '@/api/client'
import type { SkillInfo } from '@/types'

const PROTOCOL_OPTIONS = [
  { value: 'ssh', label: 'SSH (Linux/Unix)' },
  { value: 'winrm', label: 'WinRM (Windows)' },
  { value: 'database', label: '数据库' },
  { value: 'api', label: 'API / 虚拟' },
]

const DB_TYPES = ['mysql', 'oracle', 'postgresql', 'mssql']

export default function ConnectionModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addSession = useStore((s) => s.addSession)
  const addToast = useStore((s) => s.addToast)
  const setView = useStore((s) => s.setView)

  const [form, setForm] = useState({
    host: '', port: 22, username: 'root', password: '',
    remark: '', protocol: 'ssh', agent_profile: 'default',
    group_name: '未分组', allow_modifications: false,
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
          agent_profile: a.agent_profile || 'default', group_name: a.group_name || '未分组',
          allow_modifications: false, extra_args: a.extra_args || {},
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
      const res = await testConnection({
        host: form.host, port: form.port, username: form.username,
        password: form.password, protocol: form.protocol,
        extra_args: form.extra_args, active_skills: [],
      })
      setTestResult({ ok: res.status === 'success', msg: res.message })
    } catch (e: unknown) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : 'Test failed' })
    }
    setTesting(false)
  }

  const handleConnect = async () => {
    if (!form.host) { addToast('请输入主机地址', 'error'); return }
    setConnecting(true)
    try {
      const res = await connectSession({
        ...form,
        active_skills: Array.from(selectedSkills),
      })
      const sid = res.data.session_id
      addSession({
        id: sid, host: form.host, remark: form.remark,
        isReadWriteMode: form.allow_modifications,
        skills: Array.from(selectedSkills), agentProfile: form.agent_profile,
        user: form.username, protocol: form.protocol,
        extra_args: form.extra_args, heartbeatEnabled: false,
        group_name: form.group_name, messages: [], isStreaming: false,
      })
      addToast(`已连接到 ${form.remark || form.host}`, 'success')
      closeModal()
      setView('chat')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '连接失败', 'error')
    }
    setConnecting(false)
  }

  const toggleSkill = (id: string) => {
    const next = new Set(selectedSkills)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelectedSkills(next)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[560px] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">⚡ 新建连接</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>

        <div className="space-y-3">
          {/* Protocol selector */}
          <div className="flex gap-2">
            {PROTOCOL_OPTIONS.map((p) => (
              <button key={p.value} onClick={() => setForm({ ...form, protocol: p.value, port: p.value === 'database' ? 3306 : p.value === 'winrm' ? 5985 : 22 })}
                className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${form.protocol === p.value ? 'bg-ops-accent/20 text-ops-accent' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}>
                {p.label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-ops-subtext">主机地址</label>
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
          {form.protocol === 'database' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-ops-subtext">数据库类型</label>
                <select value={(form.extra_args.db_type as string) || 'mysql'}
                  onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, db_type: e.target.value } })}
                  className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent">
                  {DB_TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                </select>
              </div>
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
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={handleTest} disabled={testing || !form.host}
            className="px-4 py-2 text-sm bg-ops-surface0 text-ops-subtext rounded-lg hover:text-ops-text disabled:opacity-40 transition-colors">
            {testing ? '测试中...' : '🔌 测试'}
          </button>
          <button onClick={handleConnect} disabled={connecting || !form.host}
            className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors">
            {connecting ? '连接中...' : '⚡ 连接'}
          </button>
        </div>
      </div>
    </div>
  )
}
