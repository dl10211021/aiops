import type { SafetyPolicyCategory } from '@/types'
import type { CategoryKey } from './safetyPolicyShared'

type ListField =
  | 'approval_patterns'
  | 'readonly_block_patterns'
  | 'readonly_safe_roots'
  | 'approval_commands'
  | 'readonly_block_commands'
  | 'approval_methods'
  | 'readonly_block_methods'
  | 'hard_block_substrings'

interface AdvancedPolicyFieldsProps {
  activeCategory: CategoryKey
  category: SafetyPolicyCategory
  updateCategory: (category: CategoryKey, patch: Partial<SafetyPolicyCategory>) => void
}

function lines(value?: string[]) {
  return (value || []).join('\n')
}

function splitLines(value: string) {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
}

export function AdvancedPolicyFields({ activeCategory, category, updateCategory }: AdvancedPolicyFieldsProps) {
  const updateList = (field: ListField, value: string) => {
    updateCategory(activeCategory, { [field]: splitLines(value) })
  }

  const textArea = (label: string, field: ListField, rows = 5) => (
    <label className="block">
      <span className="text-xs text-ops-subtext">{label}</span>
      <textarea
        value={lines(category[field] as string[] | undefined)}
        onChange={(e) => updateList(field, e.target.value)}
        rows={rows}
        className="ops-control mt-1 w-full resize-y px-3 py-2 font-mono text-xs"
        spellCheck={false}
      />
    </label>
  )

  return (
    <section className="ops-data-panel space-y-4 p-4">
      <div>
        <h4 className="text-sm font-semibold text-ops-text">高级规则</h4>
        <p className="mt-1 text-xs text-ops-subtext">
          这里保留底层字段，给懂正则或需要精确兜底的管理员使用。日常配置优先在“动作权限”里完成。
        </p>
      </div>

      {textArea('禁止执行片段（无论只读或读写都拒绝，每行一个）', 'hard_block_substrings', 5)}

      {(activeCategory === 'linux' || activeCategory === 'windows' || activeCategory === 'sql' || activeCategory === 'network' || activeCategory === 'local') && (
        <>
          {textArea('需要审批的命令 / SQL 正则', 'approval_patterns', 7)}
          {textArea('只读模式兜底阻止的命令 / SQL 正则', 'readonly_block_patterns', 7)}
        </>
      )}

      {activeCategory === 'linux' && (
        <details className="ops-data-panel p-3">
          <summary className="cursor-pointer text-xs text-ops-subtext">只读未知命令策略</summary>
          <div className="mt-3 space-y-3">
            {textArea('只读安全根命令（每行一个）', 'readonly_safe_roots', 5)}
            <label className="flex items-center gap-2 text-sm text-ops-text">
              <input
                type="checkbox"
                checked={Boolean(category.readonly_unknown_requires_approval)}
                onChange={(e) => updateCategory(activeCategory, { readonly_unknown_requires_approval: e.target.checked })}
                className="accent-ops-accent"
              />
              只读模式下未知根命令需要人工审批
            </label>
          </div>
        </details>
      )}

      {activeCategory === 'redis' && (
        <>
          {textArea('需要审批的 Redis 命令', 'approval_commands', 7)}
          {textArea('只读模式兜底阻止的 Redis 命令', 'readonly_block_commands', 7)}
        </>
      )}

      {activeCategory === 'http' && (
        <>
          {textArea('需要审批的 HTTP 方法', 'approval_methods', 4)}
          {textArea('只读模式兜底阻止的 HTTP 方法', 'readonly_block_methods', 4)}
        </>
      )}

      {activeCategory === 'local' && (
        <>
          <label className="flex items-center gap-2 text-sm text-ops-text">
            <input
              type="checkbox"
              checked={Boolean(category.always_approval)}
              onChange={(e) => updateCategory(activeCategory, { always_approval: e.target.checked })}
              className="accent-ops-accent"
            />
            本地 Skill 脚本始终需要人工审批
          </label>
          <label className="block">
            <span className="text-xs text-ops-subtext">审批提示文案</span>
            <input
              value={category.approval_reason || ''}
              onChange={(e) => updateCategory(activeCategory, { approval_reason: e.target.value })}
              className="ops-control mt-1 w-full px-3 py-2 text-sm"
            />
          </label>
        </>
      )}
    </section>
  )
}
