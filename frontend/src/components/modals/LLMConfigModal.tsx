import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getProviders, updateProviders, getAvailableModels } from '@/api/client'
import type { ModelGroup, ProviderConfig } from '@/api/client'

export default function LLMConfigModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [providers, setProviders] = useState<ProviderConfig[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [modelsCount, setModelsCount] = useState<number | null>(null)
  const [fetchedModelsInfo, setFetchedModelsInfo] = useState<ModelGroup[]>([])

  useEffect(() => {
    getProviders().then((r) => {
      setProviders(r.data.providers || [])
      if (r.data.providers && r.data.providers.length > 0) {
        setSelectedId(r.data.providers[0].id)
      }
    }).catch(() => addToast('加载配置失败', 'error'))
  }, [])

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

  const handleDelete = async (id: string) => {
    const next = providers.filter(p => p.id !== id)
    setProviders(next)
    if (selectedId === id) {
      setSelectedId(next.length > 0 ? next[0].id : '')
    }
    try {
      await updateProviders(next)
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
          count += g.models.length;
          nextProviders = nextProviders.map(p => {
            if (p.id === g.provider_id) {
              const modelNames = g.models.filter(m => m.name !== '未获取到模型或配置错误').map(m => m.name).join(',');
              return { ...p, models: modelNames };
            }
            return p;
          });
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
                  <p className="text-[11px] text-ops-subtext mt-1">可手动填写，也可点击下方按钮从当前供应商的 /models 接口强制刷新。</p>
                </div>

                
                <div className="pt-4 border-t border-ops-surface0">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xs font-medium text-ops-subtext">已拉取到的模型列表</h3>
                  </div>
                  
                  {fetchedModelsInfo.length > 0 ? (
                    <div className="bg-black/30 rounded border border-ops-surface1 p-2 max-h-40 overflow-y-auto">
                      {fetchedModelsInfo.map(group => (
                        <div key={group.provider_id} className="mb-2 last:mb-0">
                          <div className="text-[11px] text-ops-accent mb-1 sticky top-0 bg-black/80 py-0.5">{group.provider_name}</div>
                          <div className="flex flex-wrap gap-1.5 pl-1">
                            {group.models.map(m => (
                              <span key={m.id} className="text-[10px] font-mono bg-ops-surface0 text-ops-text px-1.5 py-0.5 rounded border border-ops-surface1">
                                {m.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[11px] text-ops-subtext italic bg-ops-surface0/50 p-2 rounded text-center border border-ops-surface0/50">
                      点击右下角的"测试当前供应商 & 动态获取模型"查看结果
                    </div>
                  )}
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
              <button onClick={handleTestModels} disabled={testing || saving} className="text-xs bg-ops-surface1 hover:bg-ops-surface2 text-ops-text px-3 py-1.5 rounded transition-colors disabled:opacity-50">
                {testing ? '⏳ 正在与当前模型供应商通信...' : '🔍 测试当前供应商 & 动态获取模型'}
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
