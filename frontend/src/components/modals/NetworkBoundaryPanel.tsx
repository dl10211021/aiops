import type { SafetyPolicyNetworkBoundary } from '@/types'

type BoundaryListField = 'active_cidrs' | 'readonly_cidrs' | 'blocked_cidrs' | 'allowed_hosts' | 'blocked_hosts'

interface NetworkBoundaryPanelProps {
  boundary: SafetyPolicyNetworkBoundary
  updateNetworkBoundary: (patch: Partial<SafetyPolicyNetworkBoundary>) => void
}

function lines(value?: string[]) {
  return (value || []).join('\n')
}

function splitLines(value: string) {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
}

export function NetworkBoundaryPanel({ boundary, updateNetworkBoundary }: NetworkBoundaryPanelProps) {
  const updateBoundaryList = (field: BoundaryListField, value: string) => {
    updateNetworkBoundary({ [field]: splitLines(value) })
  }

  const boundaryTextArea = (label: string, field: BoundaryListField, rows = 4, hint?: string) => (
    <label className="block">
      <span className="text-xs text-ops-subtext">{label}</span>
      {hint && <span className="ml-2 text-[10px] text-ops-overlay">{hint}</span>}
      <textarea
        value={lines(boundary[field])}
        onChange={(e) => updateBoundaryList(field, e.target.value)}
        rows={rows}
        className="mt-1 w-full resize-y rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-xs text-ops-text outline-none focus:border-ops-accent"
        spellCheck={false}
      />
    </label>
  )

  return (
    <section className="mb-4 space-y-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h4 className="text-sm font-semibold text-ops-text">网络活动边界</h4>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            限制 AI 主动连接、探测或变更的地址范围。不在活动范围内的地址可以保留为只读资料来源，但不会被 AI 主动访问。
          </p>
        </div>
        <label className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-ops-surface1 bg-ops-panel/50 px-3 py-2 text-sm text-ops-text">
          <input
            type="checkbox"
            checked={boundary.enabled}
            onChange={(e) => updateNetworkBoundary({ enabled: e.target.checked })}
            className="accent-ops-accent"
          />
          启用边界
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3">
          <div className="text-sm font-semibold text-emerald-200">可活动范围</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">允许 AI 主动连接、探测、登录或执行读写操作的网段。</p>
        </div>
        <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 p-3">
          <div className="text-sm font-semibold text-yellow-200">只读资料范围</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">只能读取平台已有资产、告警、监控、知识库数据，不主动访问目标。</p>
        </div>
        <div className="rounded-lg border border-red-400/20 bg-red-400/10 p-3">
          <div className="text-sm font-semibold text-red-200">禁止范围</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">无论会话模式如何，命中后直接拒绝访问。</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {boundaryTextArea('可活动网段', 'active_cidrs', 5, '例如 172.17.0.0/16')}
        {boundaryTextArea('只读资料网段', 'readonly_cidrs', 5, '例如 10.0.0.0/8')}
        {boundaryTextArea('禁止访问网段', 'blocked_cidrs', 4, '例如 0.0.0.0/0')}
        {boundaryTextArea('允许主机名 / IP', 'allowed_hosts', 4, '每行一个')}
        {boundaryTextArea('禁止主机名 / IP', 'blocked_hosts', 4, '每行一个')}
        <div className="rounded-lg border border-ops-surface0 bg-ops-panel/45 p-3">
          <label className="flex items-start gap-2 text-sm text-ops-text">
            <input
              type="checkbox"
              checked={boundary.block_unknown_targets}
              onChange={(e) => updateNetworkBoundary({ block_unknown_targets: e.target.checked })}
              className="mt-1 accent-ops-accent"
            />
            <span>
              <span className="block font-medium">未知目标默认拒绝主动访问</span>
              <span className="mt-1 block text-xs leading-5 text-ops-subtext">
                打开后，AI 只能主动访问“可活动网段/允许主机名”内的目标。适合生产环境。
              </span>
            </span>
          </label>
        </div>
      </div>
    </section>
  )
}
