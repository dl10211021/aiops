import { useEffect, useState } from 'react'
import { getAssistantModelConfig, getAvailableModels, getSafetyPolicy } from '@/api/client'
import type { ModelGroup } from '@/api/client'

const CHAT_MODEL_CACHE_TTL_MS = 5 * 60 * 1000
const CHAT_SAFETY_POLICY_CACHE_TTL_MS = 30 * 1000
const ASSISTANT_MODEL_CONFIG_CHANGED_EVENT = 'opscore:assistant-model-config-changed'

let availableModelsCache: { value: ModelGroup[]; cachedAt: number } | null = null
let availableModelsRequest: Promise<ModelGroup[]> | null = null
let readWriteWarningCache: { value: boolean; cachedAt: number } | null = null
let readWriteWarningRequest: Promise<boolean> | null = null
let configuredMainModelCache: { value: string; cachedAt: number } | null = null
let configuredMainModelRequest: Promise<string> | null = null

function isFresh(cachedAt: number, ttlMs: number) {
  return Date.now() - cachedAt < ttlMs
}

function loadAvailableModelsCached() {
  if (availableModelsCache && isFresh(availableModelsCache.cachedAt, CHAT_MODEL_CACHE_TTL_MS)) {
    return Promise.resolve(availableModelsCache.value)
  }
  if (availableModelsRequest) return availableModelsRequest

  availableModelsRequest = getAvailableModels()
    .then((response) => {
      const groups = response.data.models || []
      availableModelsCache = { value: groups, cachedAt: Date.now() }
      return groups
    })
    .finally(() => {
      availableModelsRequest = null
    })

  return availableModelsRequest
}

function loadReadWriteWarningCached() {
  if (
    readWriteWarningCache &&
    isFresh(readWriteWarningCache.cachedAt, CHAT_SAFETY_POLICY_CACHE_TTL_MS)
  ) {
    return Promise.resolve(readWriteWarningCache.value)
  }
  if (readWriteWarningRequest) return readWriteWarningRequest

  readWriteWarningRequest = getSafetyPolicy()
    .then((response) => {
      const enabled = response.data.policy.readwrite_chat_warning_enabled
      readWriteWarningCache = { value: enabled, cachedAt: Date.now() }
      return enabled
    })
    .finally(() => {
      readWriteWarningRequest = null
    })

  return readWriteWarningRequest
}

function loadConfiguredMainModelCached() {
  if (configuredMainModelCache && isFresh(configuredMainModelCache.cachedAt, CHAT_MODEL_CACHE_TTL_MS)) {
    return Promise.resolve(configuredMainModelCache.value)
  }
  if (configuredMainModelRequest) return configuredMainModelRequest

  configuredMainModelRequest = getAssistantModelConfig()
    .then((response) => {
      const modelId = String(response.data.config?.main_model_id || '').trim()
      configuredMainModelCache = { value: modelId, cachedAt: Date.now() }
      return modelId
    })
    .finally(() => {
      configuredMainModelRequest = null
    })

  return configuredMainModelRequest
}

function getValidModelIds(groups: ModelGroup[]) {
  return groups.flatMap((group) => group.models.map((model) => model.id))
}

export function useChatRuntimePreferences() {
  const [modelName, setModelName] = useState(() => {
    const stored = localStorage.getItem('ops_model')
    if (stored) {
      if (!stored.includes('|') && stored.includes('gemini')) return `google|${stored}`
      if (!stored.includes('|') && stored.includes('claude')) return `anthropic|${stored}`
      if (!stored.includes('|') && stored.includes('deepseek')) return `deepseek|${stored}`
      return stored
    }
    return ''
  })
  const [thinkingMode, setThinkingMode] = useState(() =>
    localStorage.getItem('ops_thinking') || 'off'
  )
  const [availableModels, setAvailableModels] = useState<ModelGroup[]>(
    () => availableModelsCache?.value || []
  )
  const [configuredMainModel, setConfiguredMainModel] = useState(
    () => configuredMainModelCache?.value || ''
  )
  const [readWriteWarningEnabled, setReadWriteWarningEnabled] = useState(
    () => readWriteWarningCache?.value ?? true
  )

  useEffect(() => {
    let cancelled = false
    const timer = window.setTimeout(() => {
      loadAvailableModelsCached().then((groups) => {
        if (cancelled) return
        setAvailableModels(groups)
        const validIds = getValidModelIds(groups)
        const firstValid = validIds.find((id) => !id.endsWith('|none')) || validIds[0] || ''
        loadConfiguredMainModelCached().catch(() => '').then((configuredMainModel) => {
          if (cancelled) return
          setConfiguredMainModel(configuredMainModel)
          setModelName((current) => {
            if (configuredMainModel && validIds.includes(configuredMainModel)) {
              return configuredMainModel
            }
            if (current && validIds.includes(current)) return current
            return firstValid || current
          })
        })
      }).catch(() => {})
      loadReadWriteWarningCached()
        .then((enabled) => {
          if (!cancelled) setReadWriteWarningEnabled(enabled)
        })
        .catch(() => {})
    }, 1000)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    const handleAssistantConfigChanged = (event: Event) => {
      const nextMainModel = String((event as CustomEvent<{ main_model_id?: string }>).detail?.main_model_id || '').trim()
      configuredMainModelCache = { value: nextMainModel, cachedAt: Date.now() }
      availableModelsCache = null
      availableModelsRequest = null
      setConfiguredMainModel(nextMainModel)

      loadAvailableModelsCached().then((groups) => {
        setAvailableModels(groups)
        const validIds = getValidModelIds(groups)
        setModelName((current) => {
          if (nextMainModel && (validIds.length === 0 || validIds.includes(nextMainModel))) {
            return nextMainModel
          }
          if (current && validIds.includes(current)) return current
          return validIds.find((id) => !id.endsWith('|none')) || validIds[0] || current
        })
      }).catch(() => {
        if (nextMainModel) setModelName(nextMainModel)
      })
    }

    window.addEventListener(ASSISTANT_MODEL_CONFIG_CHANGED_EVENT, handleAssistantConfigChanged)
    return () => window.removeEventListener(ASSISTANT_MODEL_CONFIG_CHANGED_EVENT, handleAssistantConfigChanged)
  }, [])

  useEffect(() => {
    if (modelName) localStorage.setItem('ops_model', modelName)
  }, [modelName])

  useEffect(() => {
    localStorage.setItem('ops_thinking', thinkingMode)
  }, [thinkingMode])

  return {
    availableModels,
    configuredMainModel,
    modelName,
    readWriteWarningEnabled,
    setModelName,
    setThinkingMode,
    thinkingMode,
  }
}
