import { useEffect, useMemo, useState } from 'react'
import {
  getAssistantModelConfig,
  getAvailableModels,
  getProviders,
  updateAssistantModelConfig,
  updateProviders,
  type AssistantModelConfig,
  type ModelGroup,
  type ProviderConfig,
} from '@/api/config'
import { useStore } from '@/store'

const EMPTY_PROVIDER: ProviderConfig = {
  id: '',
  name: '',
  protocol: 'openai',
  base_url: '',
  api_key: '',
  models: '',
}

const DEFAULT_ASSISTANT_CONFIG: AssistantModelConfig = {
  main_model_id: '',
  enabled: false,
  model_id: '',
  thinking_mode: 'high',
  tasks: {
    memory_compression: true,
    trace_review: true,
    risk_advice: true,
    asset_profile_prompt: true,
    completion_check: true,
  },
}

const TASK_LABELS: Array<{ id: keyof AssistantModelConfig['tasks']; label: string }> = [
  { id: 'memory_compression', label: '记忆压缩' },
  { id: 'trace_review', label: '执行链路复核' },
  { id: 'risk_advice', label: '风险建议' },
  { id: 'asset_profile_prompt', label: '资产画像提示词' },
  { id: 'completion_check', label: '完成度检查' },
]

export default function ModelSettingsModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)
  const [providers, setProviders] = useState<ProviderConfig[]>([])
  const [assistantConfig, setAssistantConfig] = useState<AssistantModelConfig>(DEFAULT_ASSISTANT_CONFIG)
  const [modelGroups, setModelGroups] = useState<ModelGroup[]>([])
  const [activeProviderId, setActiveProviderId] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [fetchingModels, setFetchingModels] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [providerResponse, assistantResponse, modelsResponse] = await Promise.all([
          getProviders(),
          getAssistantModelConfig(),
          getAvailableModels(undefined, false),
        ])
        if (cancelled) return
        const incomingProviders = providerResponse.data.providers || []
        setProviders(incomingProviders)
        setAssistantConfig({ ...DEFAULT_ASSISTANT_CONFIG, ...assistantResponse.data.config })
        setModelGroups(modelsResponse.data.models || [])
        setActiveProviderId(incomingProviders[0]?.id || '')
      } catch (err: unknown) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : '加载模型配置失败'
          setError(message)
          addToast(message, 'error')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [addToast])

  const modelOptions = useMemo(() => {
    const fromGroups = modelGroups.flatMap((group) =>
      group.models.map((model) => ({
        id: model.id,
        label: `${group.provider_name || group.provider_id} / ${model.name}`,
      }))
    )
    const fromProviders = providers.flatMap((provider) =>
      provider.models
        .split(',')
        .map((model) => model.trim())
        .filter(Boolean)
        .map((model) => ({
          id: `${provider.id}|${model}`,
          label: `${provider.name || provider.id} / ${model}`,
        }))
    )
    const byId = new Map<string, { id: string; label: string }>()
    for (const item of [...fromGroups, ...fromProviders]) {
      if (item.id && !byId.has(item.id)) byId.set(item.id, item)
    }
    return Array.from(byId.values())
  }, [modelGroups, providers])

  const activeProvider = providers.find((provider) => provider.id === activeProviderId) || providers[0]

  const updateProvider = (providerId: string, patch: Partial<ProviderConfig>) => {
    setProviders((current) =>
      current.map((provider) => provider.id === providerId ? { ...provider, ...patch } : provider)
    )
    if (patch.id && activeProviderId === providerId) setActiveProviderId(patch.id)
  }

  const addProvider = () => {
    const nextId = uniqueProviderId(providers)
    setProviders((current) => [
      ...current,
      {
        ...EMPTY_PROVIDER,
        id: nextId,
        name: '自定义模型',
      },
    ])
    setActiveProviderId(nextId)
  }

  const removeProvider = (providerId: string) => {
    const next = providers.filter((provider) => provider.id !== providerId)
    setProviders(next)
    if (activeProviderId === providerId) setActiveProviderId(next[0]?.id || '')
  }

  const fetchModels = async (providerId?: string) => {
    setFetchingModels(true)
    try {
      const response = await getAvailableModels(providerId, true)
      setModelGroups((current) => mergeModelGroups(current, response.data.models || [], providerId))
      addToast('模型列表已刷新', 'success')
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '拉取模型列表失败', 'error')
    } finally {
      setFetchingModels(false)
    }
  }

  const save = async () => {
    const validation = validateProviders(providers)
    if (validation) {
      addToast(validation, 'error')
      return
    }
    setSaving(true)
    try {
      await updateProviders(providers)
      const assistantResponse = await updateAssistantModelConfig(assistantConfig)
      setAssistantConfig({ ...DEFAULT_ASSISTANT_CONFIG, ...assistantResponse.data.config })
      addToast('模型配置已保存', 'success')
      closeModal()
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '保存模型配置失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="ops-modal-backdrop" onClick={closeModal}>
      <div
        className="ops-modal-surface flex h-[min(760px,94vh)] w-full max-w-6xl flex-col"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="ops-modal-header">
          <div>
            <h2 className="ops-modal-title">模型配置</h2>
            <p className="ops-modal-description">
              管理模型供应商、拉取模型列表，并设置主会话模型和辅助思维模型。
            </p>
          </div>
          <button onClick={closeModal} className="ops-icon-button" title="关闭">&times;</button>
        </div>

        <div className="ops-modal-body p-5">
          {error && (
            <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex h-full items-center justify-center text-sm text-ops-subtext">
              正在加载模型配置...
            </div>
          ) : (
            <div className="grid min-h-0 gap-4 lg:grid-cols-[280px_1fr]">
              <aside className="ops-data-panel flex min-h-0 flex-col overflow-hidden">
                <div className="flex items-center justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
                  <div>
                    <div className="text-sm font-semibold text-ops-text">供应商</div>
                    <div className="mt-1 text-xs text-ops-overlay">{providers.length} 个配置</div>
                  </div>
                  <button className="ops-primary-action px-3 py-1.5 text-xs" onClick={addProvider}>
                    新增
                  </button>
                </div>
                <div className="min-h-0 flex-1 space-y-2 overflow-auto p-3">
                  {providers.length === 0 && (
                    <div className="rounded border border-ops-surface0 bg-ops-dark/30 p-4 text-xs leading-5 text-ops-subtext">
                      还没有模型供应商，点击新增后填写 OpenAI 兼容地址。
                    </div>
                  )}
                  {providers.map((provider) => (
                    <button
                      key={provider.id}
                      type="button"
                      onClick={() => setActiveProviderId(provider.id)}
                      className={`block w-full rounded-lg border px-3 py-2 text-left transition ${
                        activeProvider?.id === provider.id
                          ? 'border-ops-accent bg-ops-accent/10'
                          : 'border-ops-surface0 bg-ops-dark/28 hover:border-ops-accent/45'
                      }`}
                    >
                      <div className="truncate text-sm font-semibold text-ops-text">{provider.name || provider.id}</div>
                      <div className="mt-1 truncate font-mono text-[11px] text-ops-overlay">{provider.base_url || '-'}</div>
                      <div className="mt-1 text-[11px] text-ops-subtext">{modelCount(provider.models)} 个模型</div>
                    </button>
                  ))}
                </div>
              </aside>

              <div className="min-h-0 space-y-4 overflow-auto pr-1">
                {activeProvider ? (
                  <ProviderEditor
                    fetchingModels={fetchingModels}
                    provider={activeProvider}
                    onFetchModels={() => void fetchModels(activeProvider.id)}
                    onRemove={() => removeProvider(activeProvider.id)}
                    onUpdate={(patch) => updateProvider(activeProvider.id, patch)}
                  />
                ) : (
                  <section className="ops-data-panel p-5 text-sm text-ops-subtext">
                    请选择或新增一个模型供应商。
                  </section>
                )}

                <AssistantModelPanel
                  config={assistantConfig}
                  modelOptions={modelOptions}
                  onRefreshModels={() => void fetchModels()}
                  refreshing={fetchingModels}
                  onUpdate={(patch) => setAssistantConfig((current) => ({ ...current, ...patch }))}
                />
              </div>
            </div>
          )}
        </div>

        <div className="ops-modal-footer">
          <button onClick={closeModal} className="ops-control rounded-lg px-4 py-2 text-sm font-semibold">
            取消
          </button>
          <button onClick={save} disabled={saving || loading} className="ops-primary-action px-4 py-2 text-sm disabled:opacity-40">
            {saving ? '保存中...' : '保存配置'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ProviderEditor({
  fetchingModels,
  provider,
  onFetchModels,
  onRemove,
  onUpdate,
}: {
  fetchingModels: boolean
  provider: ProviderConfig
  onFetchModels: () => void
  onRemove: () => void
  onUpdate: (patch: Partial<ProviderConfig>) => void
}) {
  return (
    <section className="ops-data-panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">供应商详情</div>
          <div className="mt-1 text-xs text-ops-subtext">OpenAI 兼容接口可直接填写 Base URL 和模型名。</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="ops-muted-action px-3 py-1.5 text-xs" disabled={fetchingModels} onClick={onFetchModels}>
            {fetchingModels ? '拉取中...' : '拉取模型'}
          </button>
          <button className="ops-danger-action px-3 py-1.5 text-xs" onClick={onRemove}>
            删除供应商
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <ModelField label="供应商 ID" value={provider.id} onChange={(id) => onUpdate({ id: sanitizeProviderId(id) })} />
        <ModelField label="显示名称" value={provider.name} onChange={(name) => onUpdate({ name })} />
        <ModelField label="协议" value={provider.protocol} onChange={(protocol) => onUpdate({ protocol })} />
        <ModelField label="Base URL" value={provider.base_url} onChange={(base_url) => onUpdate({ base_url })} />
        <ModelField
          label="API Key"
          type="password"
          value={provider.api_key}
          onChange={(api_key) => onUpdate({ api_key })}
          placeholder="留空或保留掩码表示沿用原密钥"
        />
        <ModelField
          label="模型列表"
          value={provider.models}
          onChange={(models) => onUpdate({ models })}
          placeholder="model-a,model-b"
        />
      </div>
    </section>
  )
}

function AssistantModelPanel({
  config,
  modelOptions,
  onRefreshModels,
  onUpdate,
  refreshing,
}: {
  config: AssistantModelConfig
  modelOptions: Array<{ id: string; label: string }>
  onRefreshModels: () => void
  onUpdate: (patch: Partial<AssistantModelConfig>) => void
  refreshing: boolean
}) {
  const updateTasks = (id: keyof AssistantModelConfig['tasks'], enabled: boolean) => {
    onUpdate({ tasks: { ...config.tasks, [id]: enabled } })
  }

  return (
    <section className="ops-data-panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">运行模型选择</div>
          <div className="mt-1 text-xs text-ops-subtext">主模型负责会话执行，辅助思维模型负责记忆、画像、链路复核等后台任务。</div>
        </div>
        <button className="ops-muted-action px-3 py-1.5 text-xs" disabled={refreshing} onClick={onRefreshModels}>
          {refreshing ? '刷新中...' : '刷新模型列表'}
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <ModelSelect
          label="主会话模型"
          value={config.main_model_id}
          options={modelOptions}
          onChange={(main_model_id) => onUpdate({ main_model_id })}
        />
        <ModelSelect
          label="辅助思维模型"
          value={config.model_id}
          options={modelOptions}
          onChange={(model_id) => onUpdate({ model_id })}
        />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_220px]">
        <label className="flex items-center justify-between gap-4 rounded-lg border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
          <span>
            <span className="block text-sm font-semibold text-ops-text">启用辅助思维模型</span>
            <span className="mt-1 block text-xs text-ops-subtext">关闭后后台任务会回退到主模型。</span>
          </span>
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(event) => onUpdate({ enabled: event.target.checked })}
            className="h-5 w-5 accent-ops-accent"
          />
        </label>
        <ModelSelect
          label="思考强度"
          value={config.thinking_mode}
          options={[
            { id: 'low', label: 'low' },
            { id: 'medium', label: 'medium' },
            { id: 'high', label: 'high' },
          ]}
          onChange={(thinking_mode) => onUpdate({ thinking_mode })}
        />
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-5">
        {TASK_LABELS.map((task) => (
          <label key={task.id} className="rounded-lg border border-ops-surface0 bg-ops-dark/30 px-3 py-2 text-xs text-ops-subtext">
            <div className="flex items-center justify-between gap-2">
              <span>{task.label}</span>
              <input
                type="checkbox"
                checked={config.tasks?.[task.id] !== false}
                onChange={(event) => updateTasks(task.id, event.target.checked)}
                className="h-4 w-4 accent-ops-accent"
              />
            </div>
          </label>
        ))}
      </div>
    </section>
  )
}

function ModelField({
  label,
  onChange,
  placeholder,
  type = 'text',
  value,
}: {
  label: string
  onChange: (value: string) => void
  placeholder?: string
  type?: string
  value: string
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-ops-subtext">{label}</span>
      <input
        className="ops-input mt-1 w-full px-3 py-2 text-sm"
        type={type}
        value={value || ''}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

function ModelSelect({
  label,
  onChange,
  options,
  value,
}: {
  label: string
  onChange: (value: string) => void
  options: Array<{ id: string; label: string }>
  value: string
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-ops-subtext">{label}</span>
      <select
        className="ops-input mt-1 w-full px-3 py-2 text-sm"
        value={value || ''}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">未选择</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>{option.label}</option>
        ))}
      </select>
    </label>
  )
}

function modelCount(models: string) {
  return models.split(',').map((item) => item.trim()).filter(Boolean).length
}

function sanitizeProviderId(value: string) {
  return value.trim().replace(/[^a-zA-Z0-9_-]/g, '_')
}

function uniqueProviderId(providers: ProviderConfig[]) {
  const used = new Set(providers.map((provider) => provider.id))
  let index = providers.length + 1
  let id = `custom_${index}`
  while (used.has(id)) {
    index += 1
    id = `custom_${index}`
  }
  return id
}

function validateProviders(providers: ProviderConfig[]) {
  const ids = new Set<string>()
  for (const provider of providers) {
    if (!provider.id.trim()) return '供应商 ID 不能为空'
    if (ids.has(provider.id)) return `供应商 ID 重复：${provider.id}`
    ids.add(provider.id)
  }
  return ''
}

function mergeModelGroups(current: ModelGroup[], incoming: ModelGroup[], providerId?: string) {
  if (!providerId) return incoming
  const withoutProvider = current.filter((group) => group.provider_id !== providerId)
  return [...withoutProvider, ...incoming]
}
