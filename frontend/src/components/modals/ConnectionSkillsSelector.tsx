import type { SkillInfo } from '@/types'

interface ConnectionSkillsSelectorProps {
  search: string
  selectedSkills: Set<string>
  skills: SkillInfo[]
  onSearchChange: (value: string) => void
  onToggleSkill: (id: string) => void
}

export default function ConnectionSkillsSelector({
  search,
  selectedSkills,
  skills,
  onSearchChange,
  onToggleSkill,
}: ConnectionSkillsSelectorProps) {
  if (skills.length === 0) return null

  const normalizedSearch = search.trim().toLowerCase()
  const filteredSkills = skills.filter((skill) =>
    !normalizedSearch ||
    skill.name?.toLowerCase().includes(normalizedSearch) ||
    skill.id.toLowerCase().includes(normalizedSearch) ||
    skill.description?.toLowerCase().includes(normalizedSearch)
  )
  const orderedFilteredSkills = [...filteredSkills].sort((a, b) => {
    const selectedDelta = Number(selectedSkills.has(b.id)) - Number(selectedSkills.has(a.id))
    if (selectedDelta !== 0) return selectedDelta
    return (a.name || a.id).localeCompare(b.name || b.id)
  })

  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-ops-text">会话技能</div>
          <div className="mt-0.5 text-[11px] text-ops-overlay">已选择 {selectedSkills.size} 个，常用技能会自动排在前面。</div>
        </div>
        <input
          type="text"
          placeholder="搜索技能..."
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          className="w-48 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
      <div className="grid max-h-32 gap-1.5 overflow-y-auto pr-1 sm:grid-cols-2 lg:grid-cols-3">
        {orderedFilteredSkills.map((skill) => (
          <button
            key={skill.id}
            onClick={() => onToggleSkill(skill.id)}
            className={`min-w-0 rounded-lg border px-2.5 py-1.5 text-left text-[11px] transition-colors ${
              selectedSkills.has(skill.id)
                ? 'border-ops-accent/45 bg-ops-accent/15 text-ops-accent'
                : 'border-transparent bg-ops-surface0 text-ops-subtext hover:text-ops-text'
            }`}
            title={skill.description || skill.name || skill.id}
          >
            <span className="block truncate">{skill.name || skill.id}</span>
          </button>
        ))}
        {orderedFilteredSkills.length === 0 && (
          <div className="col-span-full rounded-lg border border-ops-surface0 bg-ops-panel/40 px-3 py-3 text-center text-xs text-ops-overlay">
            没有匹配的技能
          </div>
        )}
      </div>
    </section>
  )
}
