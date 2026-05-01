import type { SkillInfo } from '@/types'
import { skillCategoryLabel } from './skillMarketModel'

export function SkillCard({
  skill,
  onInstall,
  onView,
}: {
  skill: SkillInfo
  onView: (skill: SkillInfo) => void
  onInstall?: (skill: SkillInfo) => void
}) {
  const category = skillCategoryLabel(skill.category)
  return (
    <div className="bg-ops-panel border border-ops-surface0 rounded-lg p-4 hover:border-ops-accent/40 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0">
          <div className="font-medium text-ops-text text-sm truncate">{skill.name || skill.id}</div>
          <div className="text-xs text-ops-overlay mt-0.5">{category}</div>
        </div>
        {skill.is_market && (
          <span className="text-[10px] bg-ops-accent/15 text-ops-accent px-1.5 py-0.5 rounded">可安装</span>
        )}
      </div>
      <p className="text-xs text-ops-subtext line-clamp-2 mb-3">{skill.description || '暂无描述'}</p>
      <div className="flex gap-2">
        <button
          onClick={() => onView(skill)}
          className="flex-1 bg-ops-surface0 text-ops-subtext text-xs py-1.5 rounded-lg hover:text-ops-text transition-colors"
        >
          详情
        </button>
        {onInstall && (
          <button
            onClick={() => onInstall(skill)}
            className="flex-1 bg-ops-accent/15 text-ops-accent text-xs py-1.5 rounded-lg hover:bg-ops-accent/25 transition-colors"
          >
            安装
          </button>
        )}
      </div>
    </div>
  )
}
