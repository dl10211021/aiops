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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/55 p-4" onClick={onClose}>
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-ops-surface1 bg-ops-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-ops-text">{form.id ? '编辑巡检计划' : '新建巡检计划'}</h2>
          <button onClick={onClose} className="text-sm text-ops-overlay hover:text-ops-text">关闭</button>
        </div>
        <div className="grid gap-4">
          <div>
            <label className="text-xs text-ops-subtext">绑定资产</label>
            <select
              value={form.asset_id}
              onChange={(e) => onSelectAsset(e.target.value)}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
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
            <div className="mt-2 flex max-h-28 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-ops-surface1 bg-ops-dark p-2">
              {skills.length > 0 ? (
                skills.map((skill) => {
                  const selected = form.active_skills.includes(skill.id)
                  return (
                    <button
                      key={skill.id}
                      type="button"
                      onClick={() => onToggleSkill(skill.id)}
                      className={`rounded px-2 py-1 text-[11px] transition ${selected ? 'bg-ops-accent text-ops-dark' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}
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
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-sm text-ops-text outline-none focus:border-ops-accent"
            />
            <div className="mt-1.5 flex flex-wrap gap-1">
              {cronPresets.map((preset) => (
                <button
                  key={preset.expr}
                  onClick={() => onFormChange({ ...form, cron_expr: preset.expr })}
                  className="rounded bg-ops-surface0 px-2 py-0.5 text-[10px] text-ops-subtext hover:text-ops-text"
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
              className="mt-1 w-full resize-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
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
                className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
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
                className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
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
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={onSave} className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark hover:bg-ops-accent/80">
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
