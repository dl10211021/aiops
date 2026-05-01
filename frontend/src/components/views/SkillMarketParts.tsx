import type { SkillInfo } from '@/types'
import { SkillCard } from './SkillCard'

export function SkillMarketHeaderActions({
  search,
  onCreate,
  onScan,
  onSearchChange,
}: {
  search: string
  onCreate: () => void
  onScan: () => void
  onSearchChange: (value: string) => void
}) {
  return (
    <>
    <input
      type="text"
      placeholder="搜索技能..."
      value={search}
      onChange={(e) => onSearchChange(e.target.value)}
      className="min-w-72 flex-1 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-1.5 text-sm text-ops-text outline-none focus:border-ops-accent xl:w-80 xl:flex-none"
    />
    <button onClick={onScan} className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors">
      扫描
    </button>
    <button onClick={onCreate} className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors">
      + 创建技能
    </button>
    </>
  )
}

export function SkillSection({
  skills,
  title,
  onInstall,
  onView,
}: {
  skills: SkillInfo[]
  title: string
  onInstall?: (skill: SkillInfo) => void
  onView: (skill: SkillInfo) => void
}) {
  if (skills.length === 0) return null
  return (
    <div className="mb-8">
      <h2 className="text-sm font-semibold text-ops-subtext mb-3">{title}</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-5">
        {skills.map((skill) => (
          <SkillCard key={skill.id} skill={skill} onView={onView} onInstall={onInstall} />
        ))}
      </div>
    </div>
  )
}

export function SkillEmptyState({
  search,
  onClearSearch,
  onCreate,
  onScan,
}: {
  search: string
  onClearSearch: () => void
  onCreate: () => void
  onScan: () => void
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-6">
        <div className="text-sm font-semibold text-ops-text">{search ? '没有匹配的技能' : '暂无技能包'}</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-subtext">
          {search
            ? '可以换一个关键词，或清空搜索后查看全部已安装技能和可安装技能。'
            : '技能用于沉淀资产类型的操作流程、巡检标准和故障处理步骤。可以先扫描本地技能目录，或创建一个面向当前业务的运维技能。'}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          {search && (
            <button onClick={onClearSearch} className="rounded-lg bg-ops-surface0 px-4 py-2 text-sm text-ops-subtext transition-colors hover:text-ops-text">清空搜索</button>
          )}
          <button onClick={onScan} className="rounded-lg bg-ops-surface0 px-4 py-2 text-sm text-ops-subtext transition-colors hover:text-ops-text">扫描技能目录</button>
          <button onClick={onCreate} className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/85">创建技能</button>
        </div>
      </section>
      <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
        {[
          ['资产技能', 'Linux、Oracle、MySQL、Kubernetes、S3 等专项操作流程'],
          ['巡检技能', '标准化巡检项、风险判断、报告输出格式'],
          ['处置技能', '告警研判、回滚步骤、变更审批建议'],
        ].map(([title, desc]) => (
          <div key={title} className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-4">
            <div className="text-sm font-semibold text-ops-text">{title}</div>
            <p className="mt-2 text-xs leading-5 text-ops-subtext">{desc}</p>
          </div>
        ))}
      </section>
    </div>
  )
}
