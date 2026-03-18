const fs = require('fs');
const clientPath = 'frontend/src/api/client.ts';
let clientContent = fs.readFileSync(clientPath, 'utf8');

const newInterfaces = `
export interface ProviderConfig {
  id: string;
  name: string;
  protocol: string;
  base_url: string;
  api_key: string;
  models: string;
}

export interface ModelGroup {
  provider_id: string;
  provider_name: string;
  models: { id: string; name: string }[];
}
`;

if (!clientContent.includes('ProviderConfig')) {
  clientContent = clientContent.replace(/export async function getAvailableModels\(\) \{/, newInterfaces + '\nexport async function getAvailableModels() {');
}

clientContent = clientContent.replace(
  /return request<\{ models: string\[\] \}>\('\/models'\)/,
  `return request<{ models: ModelGroup[] }>('/models')`
);

clientContent = clientContent.replace(
  /export async function getLLMConfig\(\) \{[\s\S]*?export async function updateLLMConfig\(baseUrl: string, apiKey: string\) \{[\s\S]*?\}\n/,
  `export async function getProviders() {
  return request<{ providers: ProviderConfig[] }>('/config/providers')
}

export async function updateProviders(providers: ProviderConfig[]) {
  return request('/config/providers', {
    method: 'POST', body: JSON.stringify(providers),
  })
}\n`
);

fs.writeFileSync(clientPath, clientContent);

// -- Now for LLMConfigModal.tsx --
const modalPath = 'frontend/src/components/modals/LLMConfigModal.tsx';
const modalCode = `import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getProviders, updateProviders, getAvailableModels, type ProviderConfig } from '@/api/client'

export default function LLMConfigModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [providers, setProviders] = useState<ProviderConfig[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [modelsCount, setModelsCount] = useState<number | null>(null)

  useEffect(() => {
    getProviders().then((r) => {
      setProviders(r.data.providers || [])
      if (r.data.providers && r.data.providers.length > 0) {
        setSelectedId(r.data.providers[0].id)
      }
    }).catch(() => addToast('加载配置失败', 'error'))
  }, [])

  const handleAddProvider = () => {
    const id = 'custom_' + Date.now().toString().slice(-6)
    const newProvider: ProviderConfig = {
      id,
      name: '自定义供应商 ' + providers.length,
      protocol: 'openai',
      base_url: '',
      api_key: '',
      models: ''
    }
    setProviders([...providers, newProvider])
    setSelectedId(id)
  }

  const handleDelete = (id: string) => {
    const next = providers.filter(p => p.id !== id)
    setProviders(next)
    if (selectedId === id && next.length > 0) {
      setSelectedId(next[0].id)
    }
  }

  const updateProvider = (updates: Partial<ProviderConfig>) => {
    setProviders(providers.map(p => p.id === selectedId ? { ...p, ...updates } : p))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateProviders(providers)
      addToast('供应商配置已保存', 'success')
      closeModal()
    } catch {
      addToast('保存失败', 'error')
    }
    setSaving(false)
  }

  const handleTestModels = async () => {
    try {
      await updateProviders(providers) // Save first to test real config
      const res = await getAvailableModels()
      let count = 0
      res.data.models.forEach(g => { count += g.models.length })
      setModelsCount(count)
      addToast(\`成功拉取到 \${count} 个可用模型\`, 'success')
    } catch {
      addToast('获取模型列表失败，请检查配置', 'error')
    }
  }

  const selectedProvider = providers.find(p => p.id === selectedId)

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-0 w-[800px] h-[600px] flex overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        
        {/* Left Sidebar */}
        <div className="w-64 bg-ops-dark border-r border-ops-surface0 flex flex-col">
          <div className="p-4 border-b border-ops-surface0 flex justify-between items-center">
            <h2 className="text-ops-text font-bold">🧠 供应商列表</h2>
            <button onClick={handleAddProvider} className="text-ops-accent hover:bg-ops-accent/20 px-2 py-1 rounded text-xs transition-colors">+ 添加</button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {providers.map(p => (
              <div 
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={\`px-3 py-2 text-sm rounded cursor-pointer transition-colors \${selectedId === p.id ? 'bg-ops-surface1 text-ops-text font-medium' : 'text-ops-subtext hover:bg-ops-surface0'}\`}
              >
                {p.name}
              </div>
            ))}
            {providers.length === 0 && <div className="text-xs text-ops-subtext text-center mt-4">暂无供应商</div>}
          </div>
        </div>

        {/* Right Content */}
        <div className="flex-1 flex flex-col bg-ops-panel">
          <div className="p-4 border-b border-ops-surface0 flex justify-between items-center h-14">
            <h2 className="text-ops-text font-medium">{selectedProvider ? '编辑配置' : '请选择供应商'}</h2>
            <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-xl">&times;</button>
          </div>

          <div className="flex-1 p-6 overflow-y-auto">
            {selectedProvider ? (
              <div className="space-y-5">
                <div>
                  <label className="text-xs text-ops-subtext block mb-1">供应商名称 (UI显示用)</label>
                  <input value={selectedProvider.name} onChange={(e) => updateProvider({ name: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-text focus:border-ops-accent outline-none" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-ops-subtext block mb-1">通信协议 (Protocol)</label>
                    <select value={selectedProvider.protocol} onChange={(e) => updateProvider({ protocol: e.target.value })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-text focus:border-ops-accent outline-none">
                      <option value="openai">OpenAI 兼容协议</option>
                      <option value="anthropic">Anthropic (Claude) 原生</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-ops-subtext block mb-1">标识 ID (唯一)</label>
                    <input value={selectedProvider.id} disabled
                      className="w-full bg-ops-surface0 border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-subtext cursor-not-allowed" />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-ops-subtext block mb-1">Base URL (兼容网关地址)</label>
                  <input value={selectedProvider.base_url} onChange={(e) => updateProvider({ base_url: e.target.value })}
                    placeholder="https://api.openai.com/v1"
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm font-mono text-ops-text focus:border-ops-accent outline-none" />
                  <p className="text-[11px] text-ops-subtext mt-1">留空则使用官方默认地址，本地模型请填入具体本地地址如 http://localhost:11434/v1</p>
                </div>

                <div>
                  <label className="text-xs text-ops-subtext block mb-1">API Key</label>
                  <input type="password" value={selectedProvider.api_key} onChange={(e) => updateProvider({ api_key: e.target.value })}
                    placeholder="sk-..."
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm font-mono text-ops-text focus:border-ops-accent outline-none" />
                
