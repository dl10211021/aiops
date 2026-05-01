import { useEffect, useState } from 'react'
import { getAvailableModels, getSafetyPolicy } from '@/api/client'
import type { ModelGroup } from '@/api/client'

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
  const [availableModels, setAvailableModels] = useState<ModelGroup[]>([])
  const [readWriteWarningEnabled, setReadWriteWarningEnabled] = useState(true)

  useEffect(() => {
    getAvailableModels().then((response) => {
      const groups = response.data.models || []
      setAvailableModels(groups)
      const validIds = groups.flatMap((group) => group.models.map((model) => model.id))
      const firstValid = validIds.find((id) => !id.endsWith('|none')) || validIds[0] || ''
      setModelName((current) => {
        if (current && validIds.includes(current)) return current
        return firstValid || current
      })
    }).catch(() => {})
    getSafetyPolicy()
      .then((response) => setReadWriteWarningEnabled(response.data.policy.readwrite_chat_warning_enabled))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (modelName) localStorage.setItem('ops_model', modelName)
  }, [modelName])

  useEffect(() => {
    localStorage.setItem('ops_thinking', thinkingMode)
  }, [thinkingMode])

  return {
    availableModels,
    modelName,
    readWriteWarningEnabled,
    setModelName,
    setThinkingMode,
    thinkingMode,
  }
}
