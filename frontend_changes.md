# 前端重构：多供应商模型配置中心

为了支持无限扩展各种模型厂家（自定义地址和API Key等），我们提供了一份全新设计的前端重构代码。

请直接使用这段代码替换您的 `frontend/src/components/modals/LLMConfigModal.tsx` 文件内容：

```tsx
import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getProviders, updateProviders, getAvailableModels } from '@/api/client'
import type { ProviderConfig } from '@/api/client'

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
      name: '自定义供应商 ' + (providers.length + 1),
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
      addToast('配置已保存', 'success')
      closeModal()
    } catch {
      addToast('保存失败', 'error')
    }
    setSaving(false)
  }

  const handleTestModels = async () => {
    try {
      await updateProviders(providers) // 必须先保存
      const res = await getAvailableModels()
      let count = 0
      res.data.models.forEach(g => { count += g.models.length })
      setModelsCount(count)
      addToast(`成功拉取到 ${count} 个可用模型`, 'success')
    } catch {
      addToast('获取模型列表失败，请检查网络和 API Key', 'error')
    }
  }

  const selectedProvider = providers.find(p => p.id === selectedId)

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-0 w-[800px] h-[600px] flex overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        
        {/* 左侧：供应商列表 */}
        <div className="w-64 bg-ops-dark border-r border-ops-surface0 flex flex-col">
          <div className="p-4 border-b border-ops-surface0 flex justify-between items-center">
            <h2 className="text-ops-text font-bold">🧠 模型配置</h2>
            <button onClick={handleAddProvider} className="text-ops-accent hover:bg-ops-accent/20 px-2 py-1 rounded text-xs transition-colors">+ 添加</button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {providers.map(p => (
              <div 
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={`px-3 py-2 text-sm rounded cursor-pointer transition-colors ${selectedId === p.id ? 'bg-ops-surface1 text-ops-text font-medium' : 'text-ops-subtext hover:bg-ops-surface0'}`}
              >
                {p.name}
              </div>
            ))}
            {providers.length === 0 && <div className="text-xs text-ops-subtext text-center mt-4">暂无配置</div>}
          </div>
        </div>

        {/* 右侧：详情配置面板 */}
        <div className="flex-1 flex flex-col bg-ops-panel">
          <div className="p-4 border-b border-ops-surface0 flex justify-between items-center h-14">
            <h2 className="text-ops-text font-medium">{selectedProvider ? '编辑配置' : '请选择一项配置'}</h2>
            <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-xl">&times;</button>
          </div>

          <div className="flex-1 p-6 overflow-y-auto">
            {selectedProvider ? (
              <div className="space-y-5">
                <div>
                  <label className="text-xs text-ops-subtext block mb-1">供应商/渠道名称</label>
                  <input value={selectedProvider.name} onChange={(e) => updateProvider({ name: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-text focus:border-ops-accent outline-none" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-ops-subtext block mb-1">通信协议</label>
                    <select value={selectedProvider.protocol} onChange={(e) => updateProvider({ protocol: e.target.value })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-text focus:border-ops-accent outline-none">
                      <option value="openai">OpenAI 兼容协议</option>
                      <option value="anthropic">Anthropic (Claude) 原生</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-ops-subtext block mb-1">内部标识</label>
                    <input value={selectedProvider.id} disabled
                      className="w-full bg-ops-surface0 border border-ops-surface1 rounded px-3 py-2 text-sm text-ops-subtext cursor-not-allowed" />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-ops-subtext block mb-1">Base URL (兼容网关地址)</label>
                  <input value={selectedProvider.base_url} onChange={(e) => updateProvider({ base_url: e.target.value })}
                    placeholder="https://api.openai.com/v1"
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm font-mono text-ops-text focus:border-ops-accent outline-none" />
                  <p className="text-[11px] text-ops-subtext mt-1">本地模型请填入具体地址（如 http://localhost:11434/v1），如果是官方端点可留空。</p>
                </div>

                <div>
                  <label className="text-xs text-ops-subtext block mb-1">API Key</label>
                  <input type="password" value={selectedProvider.api_key} onChange={(e) => updateProvider({ api_key: e.target.value })}
                    placeholder="sk-..."
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm font-mono text-ops-text focus:border-ops-accent outline-none" />
                </div>

                <div>
                  <label className="text-xs text-ops-subtext block mb-1">手动定义模型列表 (逗号分隔)</label>
                  <textarea value={selectedProvider.models} onChange={(e) => updateProvider({ models: e.target.value })}
                    rows={3}
                    placeholder="gpt-4o, gpt-4-turbo"
                    className="w-full bg-ops-dark border border-ops-surface1 rounded px-3 py-2 text-sm font-mono text-ops-text focus:border-ops-accent outline-none resize-none" />
                  <p className="text-[11px] text-ops-subtext mt-1">如果您知道可用的模型名，请在此填写。如果不填，系统将尝试从API动态拉取全量列表。</p>
                </div>

                <div className="pt-2 border-t border-ops-surface0">
                  <button onClick={() => handleDelete(selectedProvider.id)} className="text-red-400 hover:text-red-300 text-xs px-2 py-1 rounded hover:bg-red-400/10 transition-colors">
                    🗑️ 删除该供应商
                  </button>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-ops-subtext text-sm">
                请在左侧选择或者添加一个新的配置
              </div>
            )}
          </div>

          {/* 右下侧：保存与获取按钮 */}
          <div className="p-4 border-t border-ops-surface0 flex justify-betw
een items-center bg-ops-dark">
            <div className="flex items-center gap-3">
              <button onClick={handleTestModels} className="text-xs bg-ops-surface1 hover:bg-ops-surface2 text-ops-text px-3 py-1.5 rounded transition-colors">
                🔍 测试全局连接 & 动态获取模型
              </button>
              {modelsCount !== null && <span className="text-xs text-green-400">已成功获取 {modelsCount} 个模型</span>}
            </div>
            <div className="flex gap-2">
              <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text transition-colors">取消</button>
              <button onClick={handleSave} disabled={saving} className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 transition-colors disabled:opacity-50">
                {saving ? '保存中...' : '💾 保存所有更改'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

同时请确保您的 `frontend/src/api/client.ts` 已经更新了这四个新接口类型：

```ts
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

export async function getProviders() {
  return request<{ providers: ProviderConfig[] }>('/config/providers')
}

export async function updateProviders(providers: ProviderConfig[]) {
  return request('/config/providers', {
    method: 'POST', body: JSON.stringify(providers),
  })
}

// getAvailableModels 接口现在的返回类型应该是：
export async function getAvailableModels() {
  return request<{ models: ModelGroup[] }>('/models')
}
```

这些前端更新配合我们刚才写好的后端，就可以完美实现类似 LobeChat 那种左侧选择供应商、右侧无限添加各个厂家的大模型面板功能了！
