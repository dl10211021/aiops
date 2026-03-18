import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getLLMConfig, updateLLMConfig, getAvailableModels } from '@/api/client'

const LLM_PRESETS: Record<string, { base_url: string; hint: string }> = {
  'Google Gemini': { base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/', hint: 'AIza...' },
  'OpenAI': { base_url: 'https://api.openai.com/v1/', hint: 'sk-...' },
  'Anthropic': { base_url: 'https://api.anthropic.com/v1/', hint: 'sk-ant-...' },
  'DeepSeek': { base_url: 'https://api.deepseek.com/v1/', hint: 'sk-...' },
  'Ollama (本地)': { base_url: 'http://localhost:11434/v1/', hint: 'ollama' },
  'vLLM (本地)': { base_url: 'http://localhost:8000/v1/', hint: 'EMPTY' },
}

export default function LLMConfigModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [models, setModels] = useState<string[]>([])
  
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getLLMConfig().then((r) => {
      setBaseUrl(r.data.base_url || '')
      setApiKey(r.data.api_key || '')
    }).catch(() => {})
    
  }, [])

  const handleTestModels = async () => {
    try {
      const res = await getAvailableModels()
      setModels(res.data.models || [])
      addToast(`发现 ${res.data.models?.length || 0} 个可用模型`, 'success')
    } catch {
      addToast('获取模型列表失败', 'error')
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateLLMConfig(baseUrl, apiKey)
      
      addToast('配置已保存', 'success')
      closeModal()
    } catch {
      addToast('保存失败', 'error')
    }
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[500px] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">⚙️ AI 大脑配置</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>

        <div className="space-y-4">
          {/* Presets */}
          <div>
            <label className="text-xs text-ops-subtext mb-1.5 block">快捷预设</label>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(LLM_PRESETS).map(([name, preset]) => (
                <button key={name} onClick={() => setBaseUrl(preset.base_url)}
                  className={`text-[11px] px-2 py-1 rounded transition-colors ${baseUrl === preset.base_url ? 'bg-ops-accent/20 text-ops-accent' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}>
                  {name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-ops-subtext">Base URL</label>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
              className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent font-mono"
              placeholder="https://api.example.com/v1/" />
          </div>

          <div>
            <label className="text-xs text-ops-subtext">API Key</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent font-mono" />
          </div>

          <button onClick={handleTestModels}
            className="w-full bg-ops-surface0 text-ops-subtext text-sm py-2 rounded-lg hover:text-ops-text transition-colors">
            🔍 测试连接 & 获取模型列表
          </button>

          {models.length > 0 && (
            <div className="bg-ops-dark rounded-lg p-3">
              <div className="text-xs text-ops-subtext mb-1">可用模型 ({models.length})</div>
              <div className="max-h-32 overflow-y-auto space-y-0.5">
                {models.map((m) => (
                  <div key={m} className="text-xs text-ops-text font-mono">{m}</div>
                ))}
              </div>
            </div>
          )}

          
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors">
            {saving ? '保存中...' : '💾 保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
