import type { Asset, InspectionTemplate, SkillInfo } from '@/types'
import { CronField } from './CronManagerParts'
import { cronPresets, type CronForm } from './cronTypes'

interface CronJobEditorModalProps {
  assets: Asset[]
  form: CronForm
  skills: SkillInfo[]
  templates: InspectionTemplate[]
  onClose: () => void
  onFormChange: (form: CronForm) => void
  onSave: () => void
  onSelectAsset: (assetId: string) => void
  onToggleSkill: (skillId: string) => void
}

export default function CronJobEditorModal({
  assets,
  form,
  skills,
  templates,
  onClose,
  onFormChange,
  onSave,
  onSelectAsset,
  onToggleSkill,
}: CronJobEditorModalProps) {
  return (
    <div className="ops-modal-backdrop" onClick={onClose}>
      <div className="ops-modal-surface flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="ops-modal-header">
          <h2 className="text-lg font-bold text-ops-text">{form.id ? '编辑巡检计划' : '新建巡检计划'}</h2>
          <button onClick={onClose} className="ops-icon-button h-9 w-9">x</button>
        </div>
        <div className="ops-modal-body grid gap-4 p-6">
          <div>
            <label className="text-xs text-ops-subtext">绑定资产</label>
            <select
              value={form.asset_id}
              onChange={(e) => onSelectAsset(e.target.value)}
              className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="">不绑定，手动填写目标</option>
              {assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  #{asset.id} {asset.remark || asset.host} - {asset.username}@{asset.host}:{asset.port} ({asset.asset_type}/{asset.protocol || asset.asset_type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="flex items-center justify-between gap-2">
              <label className="text-xs text-ops-subtext">任务技能</label>
              {form.active_skills.length > 0 && (
                <button
                  onClick={() => onFormChange({ ...form, active_skills: [] })}
                  className="text-[11px] text-ops-overlay hover:text-ops-text"
                >
                  清空
                </button>
              )}
            </div>
            <div className="ops-data-panel mt-2 flex max-h-28 flex-wrap gap-1.5 overflow-y-auto p-2">
              {skills.length > 0 ? (
                skills.map((skill) => {
                  const selected = form.active_skills.includes(skill.id)
                  return (
                    <button
                      key={skill.id}
                      type="button"
                      onClick={() => onToggleSkill(skill.id)}
                      className={`rounded px-2 py-1 text-[11px] transition ${selected ? 'bg-ops-accent text-ops-dark' : 'ops-control text-ops-subtext hover:text-ops-text'}`}
                      title={skill.description || skill.name || skill.id}
                    >
                      {skill.name || skill.id}
                    </button>
                  )
                })
              ) : (
                <span className="px-1 py-0.5 text-xs text-ops-overlay">无可用技能</span>
              )}
            </div>
          </div>

          <div>
            <label className="text-xs text-ops-subtext">Cron 表达式</label>
            <input
              value={form.cron_expr}
              onChange={(e) => onFormChange({ ...form, cron_expr: e.target.value })}
              className="ops-control mt-1 w-full px-3 py-2 font-mono text-sm text-ops-text outline-none focus:border-ops-accent"
            />
            <div className="mt-1.5 flex flex-wrap gap-1">
              {cronPresets.map((preset) => (
                <button
                  key={preset.expr}
                  onClick={() => onFormChange({ ...form, cron_expr: preset.expr })}
                  className="ops-control px-2 py-0.5 text-[10px] text-ops-subtext hover:text-ops-text"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-ops-subtext">巡检指令</label>
            <textarea
              value={form.message}
              onChange={(e) => onFormChange({ ...form, message: e.target.value })}
              rows={4}
              className="ops-control mt-1 w-full resize-none px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              placeholder="例如：执行一次 Linux/K8s/MySQL 标准只读巡检..."
            />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <CronField label="目标主机" value={form.host} onChange={(host) => onFormChange({ ...form, host })} placeholder="192.168.1.1" />
            <CronField label="用户名" value={form.username} onChange={(username) => onFormChange({ ...form, username })} />
            <CronField label="Agent 角色" value={form.agent_profile} onChange={(agent_profile) => onFormChange({ ...form, agent_profile })} />
            <CronField label="密码/凭据覆盖" type="password" value={form.password} onChange={(password) => onFormChange({ ...form, password })} placeholder="留空则使用后端任务保存凭据" />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-xs text-ops-subtext">目标范围</label>
              <select
                value={form.target_scope}
                onChange={(e) => onFormChange({ ...form, target_scope: e.target.value })}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              >
                <option value="asset">单资产</option>
                <option value="tag">资产标签</option>
                <option value="category">资产分类</option>
                <option value="protocol">登录协议</option>
                <option value="asset_type">资产类型</option>
                <option value="all">全部资产</option>
              </select>
            </div>
            <CronField label="范围值" value={form.scope_value} onChange={(scope_value) => onFormChange({ ...form, scope_value })} placeholder="资产ID、标签、分类或协议" />
            <div>
              <label className="text-xs text-ops-subtext">巡检模板</label>
              <select
                value={form.template_id}
                onChange={(e) => onFormChange({ ...form, template_id: e.target.value })}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              >
                <option value="">默认内置巡检</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>{template.name || template.id}</option>
                ))}
              </select>
            </div>
            <CronField label="通知渠道" value={form.notification_channel} onChange={(notification_channel) => onFormChange({ ...form, notification_channel })} placeholder="auto / webhook / email" />
            <CronField label="失败重试次数" value={form.retry_count} onChange={(retry_count) => onFormChange({ ...form, retry_count })} placeholder="0" type="number" />
          </div>
        </div>
        <div className="ops-modal-footer">
          <button onClick={onClose} className="ops-muted-action px-4 py-2 text-sm">取消</button>
          <button onClick={onSave} className="ops-primary-action px-4 py-2 text-sm">
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
