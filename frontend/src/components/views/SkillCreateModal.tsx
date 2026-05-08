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
    <div className="ops-modal-backdrop" onClick={onClose}>
      <div className="ops-modal-surface flex max-h-[86vh] w-full max-w-xl flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="ops-modal-header">
          <h2 className="text-lg font-bold text-ops-text">创建新技能</h2>
          <button onClick={onClose} className="ops-icon-button h-9 w-9">x</button>
        </div>
        <div className="ops-modal-body space-y-3 p-5">
          <div>
            <label className="text-xs text-ops-subtext">技能 ID (英文+横线)</label>
            <input
              value={form.skill_id}
              onChange={(e) => onFormChange({ ...form, skill_id: e.target.value })}
              className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder="my-custom-skill"
            />
          </div>
          <div>
            <label className="text-xs text-ops-subtext">描述</label>
            <input
              value={form.description}
              onChange={(e) => onFormChange({ ...form, description: e.target.value })}
              className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder="这个技能可以..."
            />
          </div>
          <div>
            <label className="text-xs text-ops-subtext">技能指令 (Markdown)</label>
            <textarea
              value={form.instructions}
              onChange={(e) => onFormChange({ ...form, instructions: e.target.value })}
              rows={8}
              className="ops-control mt-1 w-full resize-none px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder="# 技能名称&#10;&#10;## 技能职责&#10;..."
            />
          </div>
        </div>
        <div className="ops-modal-footer">
          <button onClick={onClose} className="ops-muted-action px-4 py-2 text-sm">取消</button>
          <button onClick={onSubmit} className="ops-primary-action px-4 py-2 text-sm">创建</button>
        </div>
      </div>
    </div>
  )
}
