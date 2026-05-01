import { useEffect, useState } from 'react'
import {
  getAgentRuntimeConfig,
  getAvailableModels,
  getProviders,
  updateAgentRuntimeConfig,
  updateProviders,
} from '@/api/config'
import type { AgentRuntimeConfig, ModelGroup, ProviderConfig } from '@/api/config'
import { useStore } from '@/store'

export interface RuntimeDraft {
  chat_max_steps: number
  headless_max_steps: number
}

export function useLLMConfigData() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [providers, setProviders] = useState<ProviderConfig[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [modelsCount, setModelsCount] = useState<number | null>(null)
  const [fetchedModelsInfo, setFetchedModelsInfo] = useState<ModelGroup[]>([])
  const [deleteTarget, setDeleteTarget] = useState<ProviderConfig | null>(null)
  const [runtimeConfig, setRuntimeConfig] = useState<AgentRuntimeConfig | null>(null)
  const [runtimeDraft, setRuntimeDraft] = useState<RuntimeDraft>({ chat_max_steps: 80, headless_max_steps: 60 })
  const [runtimeSaving, setRuntimeSaving] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError('')
    getProviders().then((r) => {
      setProviders(r.data.providers || [])
      if (r.data.providers && r.data.providers.length > 0) {
        setSelectedId(r.data.providers[0].id)
      }
    }).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : '加载模型配置失败')
      addToast('加载配置失败', 'error')
    }).finally(() => setLoading(false))
    getAgentRuntimeConfig().then((r) => {
      const config = r.data.config
      setRuntimeConfig(config)
      setRuntimeDraft({
        chat_max_steps: config.chat_max_steps,
        headless_max_steps: config.headless_max_steps,
      })
    }).catch(() => {
      addToast('加载执行保护配置失败', 'error')
    })
  }, [])

  const selectedProvider = providers.find(p => p.id === selectedId)

  const handleAddProvider = () => {
    const id = 'custom_' + Math.random().toString(36).substring(2, 9) + Date.now().toString().slice(-4)
    setProviders(prev => {
      const newProvider: ProviderConfig = {
        id,
        name: '自定义供应商 ' + (prev.length + 1),
        protocol: 'openai',
        base_url: '',
        api_key: '',
        models: ''
      }
      return [...prev, newProvider]
    })
    setSelectedId(id)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    const next = providers.filter(p => p.id !== deleteTarget.id)
    setProviders(next)
    if (selectedId === deleteTarget.id) {
      setSelectedId(next.length > 0 ? next[0].id : '')
    }
    try {
      await updateProviders(next)
      setDeleteTarget(null)
      addToast('已删除供应商并保存', 'success')
    } catch {
      addToast('删除保存失败', 'error')
    }
  }

  const updateProvider = (updates: Partial<ProviderConfig>) => {
    setProviders(prev => prev.map(p => p.id === selectedId ? { ...p, ...updates } : p))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateProviders(providers)
      addToast('配置已保存', 'success')
      closeModal()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存失败', 'error')
    }
    setSaving(false)
  }

  const handleTestModels = async () => {
    setTesting(true)
    try {
      if (!selectedId) throw new Error('请先选择一个模型供应商')
      await updateProviders(providers)
      const res = await getAvailableModels(selectedId, true)
      let count = 0
      let nextProviders = providers

      // Auto-fill models string only for the selected provider.
      if (res.data.models) {
        res.data.models.forEach(g => {
          count += g.models.length
          nextProviders = nextProviders.map(p => {
            if (p.id === g.provider_id) {
              const modelNames = g.models.filter(m => m.name !== '未获取到模型或配置错误').map(m => m.name).join(',')
              return { ...p, models: modelNames }
            }
            return p
          })
        })
        setProviders(nextProviders)
        await updateProviders(nextProviders)
      }

      setModelsCount(count)
      setFetchedModelsInfo(res.data.models)
      addToast(`已从当前供应商拉取 ${count} 个可用模型`, 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '获取模型失败，请检查 Base URL 和 API Key', 'error')
    }
    setTesting(false)
  }

  const clampRuntimeSteps = (value: number) => {
    const min = runtimeConfig?.min_steps ?? 10
    const max = runtimeConfig?.max_steps ?? 200
    if (!Number.isFinite(value)) return min
    return Math.max(min, Math.min(Math.round(value), max))
  }

  const handleSaveRuntime = async () => {
    setRuntimeSaving(true)
    try {
      const payload = {
        chat_max_steps: clampRuntimeSteps(runtimeDraft.chat_max_steps),
        headless_max_steps: clampRuntimeSteps(runtimeDraft.headless_max_steps),
      }
      const res = await updateAgentRuntimeConfig(payload)
      setRuntimeConfig(res.data.config)
      setRuntimeDraft({
        chat_max_steps: res.data.config.chat_max_steps,
        headless_max_steps: res.data.config.headless_max_steps,
      })
      addToast('执行保护配置已保存', 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存执行保护配置失败', 'error')
    }
    setRuntimeSaving(false)
  }

  const updateRuntimeDraft = (patch: Partial<RuntimeDraft>) => {
    setRuntimeDraft((current) => ({ ...current, ...patch }))
  }

  return {
    closeModal,
    deleteTarget,
    error,
    fetchedModelsInfo,
    handleAddProvider,
    handleDelete,
    handleSave,
    handleSaveRuntime,
    handleTestModels,
    loading,
    modelsCount,
    providers,
    runtimeConfig,
    runtimeDraft,
    runtimeSaving,
    saving,
    selectedId,
    selectedProvider,
    setDeleteTarget,
    setSelectedId,
    testing,
    updateProvider,
    updateRuntimeDraft,
  }
}
