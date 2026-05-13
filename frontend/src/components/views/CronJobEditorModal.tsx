import type { Asset, InspectionTemplate, SkillInfo } from '@/types'
import { CronField } from './CronManagerParts'
import {
  cronPresets,
  inspectionCycleOptions,
  inspectionDepthOptions,
  type CronForm,
} from './cronTypes'

interface CronJobEditorModalProps {
  assets: Asset[]
  form: CronForm
  notificationConfig: Record<string, unknown>
  skills: SkillInfo[]
  templates: InspectionTemplate[]
  onClose: () => void
  onFormChange: (form: CronForm) => void
  onSave: () => void
  onSelectAsset: (assetId: string) => void
  onToggleSkill: (skillId: string) => void
}

type SelectOption = {
  label: string
  value: string
  disabled?: boolean
}

const notificationLabels: Record<string, string> = {
  auto: '自动选择',
  wechat: '企业微信',
  dingtalk: '钉钉',
  email: '邮件',
}

function hasConfiguredValue(value: unknown) {
  return typeof value === 'string' && value.trim().length > 0
}

function buildNotificationOptions(config: Record<string, unknown>, current: string): SelectOption[] {
  const options: SelectOption[] = [{ value: 'auto', label: '自动选择已配置渠道' }]
  if (config.wechat_enabled !== false && hasConfiguredValue(config.wechat_webhook)) {
    options.push({ value: 'wechat', label: '企业微信' })
  }
  if (config.dingtalk_enabled !== false && hasConfiguredValue(config.dingtalk_webhook)) {
    options.push({ value: 'dingtalk', label: '钉钉' })
  }
  if (config.email_enabled !== false && hasConfiguredValue(config.email_address)) {
    options.push({ value: 'email', label: '邮件' })
  }
  if (current && !options.some((option) => option.value === current)) {
    options.push({ value: current, label: notificationLabels[current] || `当前值：${current}` })
  }
  return options
}

function assetLabel(asset: Asset) {
  return `#${asset.id} ${asset.remark || asset.host} - ${asset.username}@${asset.host}:${asset.port} (${asset.asset_type}/${asset.protocol || asset.asset_type})`
}

function assetCategory(asset: Asset) {
  return String(asset.extra_args?.category || '').trim()
}

function uniqueOptions(values: string[]): SelectOption[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)))
    .sort((a, b) => a.localeCompare(b))
    .map((value) => ({ value, label: value }))
}

function scopeOptionsForAssets(assets: Asset[], scope: string): SelectOption[] {
  if (scope === 'tag') return uniqueOptions(assets.flatMap((asset) => asset.tags || []))
  if (scope === 'category') return uniqueOptions(assets.map(assetCategory))
  if (scope === 'protocol') return uniqueOptions(assets.map((asset) => asset.protocol || asset.asset_type || ''))
  if (scope === 'asset_type') return uniqueOptions(assets.map((asset) => asset.asset_type || ''))
  return []
}

function isCycleGeneratedMessage(message: string) {
  return inspectionCycleOptions.some((option) => option.message === message.trim())
}

export default function CronJobEditorModal({
  assets,
  form,
  notificationConfig,
  skills,
  templates,
  onClose,
  onFormChange,
  onSave,
  onSelectAsset,
  onToggleSkill,
}: CronJobEditorModalProps) {
  const selectedAsset = assets.find((asset) => String(asset.id) === form.asset_id)
  const notificationOptions = buildNotificationOptions(notificationConfig, form.notification_channel)
  const scopeOptions = scopeOptionsForAssets(assets, form.target_scope)
  const hasScopeValueSelect = !['asset', 'all'].includes(form.target_scope)
  const selectedCycle = inspectionCycleOptions.find((option) => option.value === form.inspection_cycle) || inspectionCycleOptions[0]
  const selectedDepth = inspectionDepthOptions.find((option) => option.value === form.inspection_depth) || inspectionDepthOptions[1]

  const selectTargetScope = (target_scope: string) => {
    if (target_scope === 'asset') {
      onFormChange({ ...form, target_scope, scope_value: form.asset_id || '' })
      return
    }
    if (target_scope === 'all') {
      onFormChange({ ...form, asset_id: '', host: '', username: '', target_scope, scope_value: '' })
      return
    }
    const nextOptions = scopeOptionsForAssets(assets, target_scope)
    const currentIsValid = nextOptions.some((option) => option.value === form.scope_value)
    onFormChange({
      ...form,
      asset_id: '',
      host: '',
      username: '',
      target_scope,
      scope_value: currentIsValid ? form.scope_value : nextOptions[0]?.value || '',
    })
  }

  const selectInspectionCycle = (inspection_cycle: string) => {
    const nextCycle = inspectionCycleOptions.find((option) => option.value === inspection_cycle) || inspectionCycleOptions[0]
    const shouldReplaceMessage = !form.message.trim() || isCycleGeneratedMessage(form.message)
    onFormChange({
      ...form,
      inspection_cycle: nextCycle.value,
      cron_expr: nextCycle.cronExpr,
      message: shouldReplaceMessage ? nextCycle.message : form.message,
    })
  }

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
              <option value="" disabled>{assets.length > 0 ? '请选择资产中心资产' : '暂无资产，请先在资产中心添加'}</option>
              {assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {assetLabel(asset)}
                </option>
              ))}
            </select>
            {selectedAsset && (
              <div className="ops-data-panel mt-2 grid gap-1.5 p-3 text-xs text-ops-subtext sm:grid-cols-2">
                <span>主机：{selectedAsset.host}:{selectedAsset.port}</span>
                <span>账号：{selectedAsset.username}</span>
                <span>类型：{selectedAsset.asset_type}</span>
                <span>协议：{selectedAsset.protocol || selectedAsset.asset_type}</span>
              </div>
            )}
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

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-xs text-ops-subtext">巡检周期</label>
              <select
                value={form.inspection_cycle}
                onChange={(e) => selectInspectionCycle(e.target.value)}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              >
                {inspectionCycleOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-ops-subtext">巡检深度</label>
              <select
                value={form.inspection_depth}
                onChange={(e) => onFormChange({ ...form, inspection_depth: e.target.value })}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              >
                {inspectionDepthOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2 rounded border border-ops-surface0 bg-ops-dark/25 px-3 py-2 text-[11px] leading-5 text-ops-subtext">
              <div>周期重点：{selectedCycle.focus}</div>
              <div>深度说明：{selectedDepth.description}</div>
            </div>
          </div>

          <div>
            <label className="text-xs text-ops-subtext">Cron 表达式</label>
            <input
              value={form.cron_expr}
              onChange={(e) => onFormChange({ ...form, cron_expr: e.target.value, inspection_cycle: 'custom' })}
              className="ops-control mt-1 w-full px-3 py-2 font-mono text-sm text-ops-text outline-none focus:border-ops-accent"
            />
            <div className="mt-1.5 flex flex-wrap gap-1">
              {cronPresets.map((preset) => (
                <button
                  key={`${preset.expr}-${preset.cycle}`}
                  onClick={() => {
                    const shouldReplaceMessage = !form.message.trim() || isCycleGeneratedMessage(form.message)
                    const cycle = inspectionCycleOptions.find((option) => option.value === preset.cycle)
                    onFormChange({
                      ...form,
                      cron_expr: preset.expr,
                      inspection_cycle: preset.cycle,
                      message: shouldReplaceMessage && cycle ? cycle.message : form.message,
                    })
                  }}
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
            <div>
              <label className="text-xs text-ops-subtext">目标范围</label>
              <select
                value={form.target_scope}
                onChange={(e) => selectTargetScope(e.target.value)}
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
            <div>
              <label className="text-xs text-ops-subtext">范围值</label>
              <select
                value={hasScopeValueSelect ? form.scope_value : ''}
                onChange={(e) => onFormChange({ ...form, scope_value: e.target.value })}
                disabled={!hasScopeValueSelect}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-60"
              >
                <option value="">
                  {form.target_scope === 'asset' ? '由绑定资产决定' : form.target_scope === 'all' ? '全部资产' : '请选择资产范围值'}
                </option>
                {scopeOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
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
            <div>
              <label className="text-xs text-ops-subtext">通知渠道</label>
              <select
                value={form.notification_channel || 'auto'}
                onChange={(e) => onFormChange({ ...form, notification_channel: e.target.value })}
                className="ops-control mt-1 w-full px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
              >
                {notificationOptions.map((option) => (
                  <option key={option.value} value={option.value} disabled={option.disabled}>{option.label}</option>
                ))}
              </select>
            </div>
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
