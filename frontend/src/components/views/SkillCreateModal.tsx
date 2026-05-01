import type { SkillCreateForm } from './skillMarketModel'

export function SkillCreateModal({
  form,
  onClose,
  onFormChange,
  onSubmit,
}: {
  form: SkillCreateForm
  onClose: () => void
  onFormChange: (form: SkillCreateForm) => void
  onSubmit: () => void
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="max-h-[86vh] w-full max-w-xl overflow-y-auto rounded-lg border border-ops-surface1 bg-ops-panel p-5" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-ops-text mb-4">创建新技能</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-ops-subtext">技能 ID (英文+横线)</label>
            <input
              value={form.skill_id}
              onChange={(e) => onFormChange({ ...form, skill_id: e.target.value })}
              className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
              placeholder="my-custom-skill"
            />
          </div>
          <div>
            <label className="text-xs text-ops-subtext">描述</label>
            <input
              value={form.description}
              onChange={(e) => onFormChange({ ...form, description: e.target.value })}
              className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
              placeholder="这个技能可以..."
            />
          </div>
          <div>
            <label className="text-xs text-ops-subtext">技能指令 (Markdown)</label>
            <textarea
              value={form.instructions}
              onChange={(e) => onFormChange({ ...form, instructions: e.target.value })}
              rows={8}
              className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent resize-none"
              placeholder="# 技能名称&#10;&#10;## 技能职责&#10;..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={onSubmit} className="bg-ops-accent text-ops-dark px-4 py-2 rounded-lg text-sm font-medium hover:bg-ops-accent/80">创建</button>
        </div>
      </div>
    </div>
  )
}
