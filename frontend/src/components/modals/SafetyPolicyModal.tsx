import { useEffect, useState } from 'react'
import { useStore } from '@/store'
import { getSafetyPolicy, updateSafetyPolicy } from '@/api/client'
import type { SafetyPolicy, SafetyPolicyCategory } from '@/types'

type CategoryKey = 'linux' | 'windows' | 'sql' | 'redis' | 'http' | 'network' | 'local'
type ListField =
  | 'approval_patterns'
  | 'readonly_block_patterns'
  | 'readonly_safe_roots'
  | 'approval_commands'
  | 'readonly_block_commands'
  | 'approval_methods'
  | 'readonly_block_methods'
  | 'hard_block_substrings'

const CATEGORY_LABELS: Record<CategoryKey, string> = {
  linux: 'Linux / KVM',
  windows: 'Windows WinRM',
  sql: '数据库 SQL',
  redis: 'Redis',
  http: 'HTTP / API',
  network: '交换机 / 网络设备',
  local: '本地 Skill 脚本',
}

const CATEGORY_HINTS: Record<CategoryKey, string> = {
  linux: '只读默认放行巡检命令；直接拦截只用于明确写入/变更动作。',
  windows: '正则按 PowerShell/CMD 命令文本匹配。',
  sql: '正则按 SQL 文本匹配；只读模式会直接拦截写入类语句。',
  redis: '按 Redis 命令首词匹配，不区分大小写。',
  http: '按 HTTP 方法匹配；默认 POST 只审批不拦截，PUT/PATCH/DELETE 在只读模式拦截。',
  network: '按交换机 CLI 文本匹配；display/show/ping 等巡检命令默认放行。',
  local: '宿主机本地脚本风险最高，建议始终保留人工审批。',
}

function lines(value?: string[]) {
  return (value || []).join('\n')
}

function splitLines(value: string) {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
}

export default function SafetyPolicyModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)
  const [policy, setPolicy] = useState<SafetyPolicy | null>(null)
  const [active, setActive] = useState<CategoryKey>('linux')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getSafetyPolicy()
      .then((res) => setPolicy(res.data.policy))
      .catch(() => addToast('加载安全策略失败', 'error'))
  }, [addToast])

  const category = policy?.categories?.[active] || {}

  const updatePolicy = (patch: Partial<SafetyPolicy>) => {
    if (!policy) return
    setPolicy({ ...policy, ...patch })
  }

  const updateCategory = (patch: Partial<SafetyPolicyCategory>) => {
    if (!policy) return
    setPolicy({
      ...policy,
      categories: {
        ...policy.categories,
        [active]: { ...(policy.categories[active] || {}), ...patch },
      },
    })
  }

  const updateList = (field: ListField, value: string) => {
    updateCategory({ [field]: splitLines(value) })
  }

  const save = async () => {
    if (!policy) return
    setSaving(true)
    try {
      const res = await updateSafetyPolicy(policy)
      setPolicy(res.data.policy)
      addToast('安全策略已保存', 'success')
      closeModal()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存安全策略失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  const textArea = (label: string, field: ListField, rows = 6) => (
    <label className="block">
      <span className="text-xs text-ops-subtext">{label}</span>
      <textarea
        value={lines(category[field] as string[] | undefined)}
        onChange={(e) => updateList(field, e.target.value)}
        rows={rows}
        className="mt-1 w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-xs font-mono text-ops-text outline-none focus:border-ops-accent resize-y"
        spellCheck={false}
      />
    </label>
  )

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl w-[920px] h-[680px] flex overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="w-56 bg-ops-dark border-r border-ops-surface0 flex flex-col">
          <div className="p-4 border-b border-ops-surface0">
            <h2 className="text-ops-text font-bold">安全策略</h2>
            <p className="text-[11px] text-ops-subtext mt-1">审批、只读拦截、硬拦截规则</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {(Object.keys(CATEGORY_LABELS) as CategoryKey[]).map((key) => (
              <button
                key={key}
                onClick={() => setActive(key)}
                className={`w-full text-left px-3 py-2 text-sm rounded transition-colors ${
                  active === key ? 'bg-ops-surface1 text-ops-text font-medium' : 'text-ops-subtext hover:bg-ops-surface0'
                }`}
              >
                {CATEGORY_LABELS[key]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col">
          <div className="h-14 border-b border-ops-surface0 px-5 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-ops-text">{CATEGORY_LABELS[active]}</h3>
              <p className="text-[11px] text-ops-subtext">{CATEGORY_HINTS[active]}</p>
            </div>
            <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-xl">&times;</button>
          </div>

          {!policy ? (
            <div className="flex-1 flex items-center justify-center text-ops-subtext">加载中...</div>
          ) : (
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              <section className="grid grid-cols-2 gap-4 bg-ops-dark/50 border border-ops-surface0 rounded-lg p-4">
                <label>
                  <span className="text-xs text-ops-subtext">审批等待超时（秒）</span>
                  <input
                    type="number"
                    min={30}
                    max={1800}
                    value={policy.approval_timeout_seconds}
                    onChange={(e) => updatePolicy({ approval_timeout_seconds: Number(e.target.value) || 300 })}
                    className="mt-1 w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                  />
                </label>
                <label className="flex items-center gap-2 pt-6 text-sm text-ops-text">
                  <input
                    type="checkbox"
                    checked={policy.readwrite_chat_warning_enabled}
                    onChange={(e) => updatePolicy({ readwrite_chat_warning_enabled: e.target.checked })}
                    className="accent-ops-accent"
                  />
                  读写会话聊天前弹窗提醒
                </label>
              </section>

              <section className="bg-ops-surface0/40 border border-red-500/20 rounded-lg p-4 space-y-2">
                <div>
                  <h4 className="text-xs font-semibold text-red-300">硬拦截片段</h4>
                  <p className="text-[11px] text-ops-subtext mt-1">
                    命中后无论只读或读写模式都会直接拒绝，不进入审批。这里只放删库、格式化、清空配置等极端破坏动作。
                  </p>
                </div>
                {textArea('无论读写都强制拒绝的危险片段（每行一个，按包含匹配）', 'hard_block_substrings', 5)}
              </section>

              {active === 'linux' && (
                <>
                  {textArea('需要后端审批的命令正则', 'approval_patterns', 8)}
                  {textArea('只读模式直接拦截的命令正则', 'readonly_block_patterns', 8)}
                  <details className="bg-ops-dark/40 border border-ops-surface0 rounded-lg p-3">
                    <summary className="cursor-pointer text-xs text-ops-subtext">高级：只读未知命令审批白名单（默认关闭）</summary>
                    <div className="mt-3 space-y-3">
                      {textArea('只读模式安全根命令（每行一个）', 'readonly_safe_roots', 5)}
                    </div>
                  </details>
                  <label className="flex items-center gap-2 text-sm text-ops-text">
                    <input
                      type="checkbox"
                      checked={Boolean(category.readonly_unknown_requires_approval)}
                      onChange={(e) => updateCategory({ readonly_unknown_requires_approval: e.target.checked })}
                      className="accent-ops-accent"
                    />
                    只读模式下未知根命令需要人工审批
                  </label>
                </>
              )}

              {(active === 'windows' || active === 'sql') && (
                <>
                  {textArea('需要后端审批的正则', 'approval_patterns', 10)}
                  {textArea('只读模式直接拦截的正则', 'readonly_block_patterns', 10)}
                </>
              )}

              {active === 'network' && (
                <>
                  {textArea('需要后端审批的网络设备命令正则', 'approval_patterns', 10)}
                  {textArea('只读模式直接拦截的网络设备命令正则', 'readonly_block_patterns', 10)}
                </>
              )}

              {active === 'redis' && (
                <>
                  {textArea('需要后端审批的 Redis 命令', 'approval_commands', 10)}
                  {textArea('只读模式直接拦截的 Redis 命令', 'readonly_block_commands', 10)}
                </>
              )}

              {active === 'http' && (
                <>
                  {textArea('需要后端审批的 HTTP 方法', 'approval_methods', 5)}
                  {textArea('只读模式直接拦截的 HTTP 方法', 'readonly_block_methods', 5)}
                </>
              )}

              {active === 'local' && (
                <>
                  <label className="flex items-center gap-2 text-sm text-ops-text">
                    <input
                      type="checkbox"
                      checked={Boolean(category.always_approval)}
                      onChange={(e) => updateCategory({ always_approval: e.target.checked })}
                      className="accent-ops-accent"
                    />
                    本地 Skill 脚本始终需要人工审批
                  </label>
                  <label className="block">
                    <span className="text-xs text-ops-subtext">审批提示文案</span>
                    <input
                      value={category.approval_reason || ''}
                      onChange={(e) => updateCategory({ approval_reason: e.target.value })}
                      className="mt-1 w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  {textArea('只读模式直接拦截的本地命令正则', 'readonly_block_patterns', 8)}
                </>
              )}
            </div>
          )}

          <div className="border-t border-ops-surface0 px-5 py-3 flex justify-end gap-2">
            <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
            <button
              onClick={save}
              disabled={!policy || saving}
              className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors"
            >
              {saving ? '保存中...' : '保存策略'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
