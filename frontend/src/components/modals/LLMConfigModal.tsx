import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { getAvailableModels } from '@/api/client'

export default function LLMConfigModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)

  const [models, setModels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    handleLoadModels()
  }, [])

  const handleLoadModels = async () => {
    setLoading(true)
    try {
      const res = await getAvailableModels()
      setModels(res.data.models || [])
    } catch {
      addToast('获取模型列表失败', 'error')
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[500px] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">🖥️ 系统已加载模型</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>

        <div className="space-y-4">
          <div className="text-sm text-ops-subtext">
            系统底层已切换为多协议支持的动态客户端工厂。所有的 API Keys 和基础 URL 目前由后端统一配置管理。
            这里是系统已成功拉取的所有可用模型：
          </div>

          <div className="bg-ops-dark rounded-lg p-3">
            <div className="flex justify-between items-center mb-2 border-b border-ops-surface1 pb-2">
              <span className="text-xs text-ops-subtext">可用模型 ({models.length})</span>
              <button 
                onClick={handleLoadModels} 
                disabled={loading}
                className="text-xs text-ops-accent hover:text-ops-accent/80 transition-colors disabled:opacity-50"
              >
                {loading ? '刷新中...' : '🔄 刷新'}
              </button>
            </div>
            
            <div className="max-h-64 overflow-y-auto space-y-1 mt-2">
              {models.length > 0 ? models.map((m) => (
                <div key={m} className="text-sm text-ops-text font-mono bg-ops-surface0 px-2 py-1.5 rounded">{m}</div>
              )) : (
                <div className="text-xs text-ops-subtext text-center py-4">暂无可用模型，请检查后端配置</div>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end mt-6">
          <button onClick={closeModal} className="px-4 py-2 text-sm bg-ops-surface0 text-ops-text rounded-lg hover:bg-ops-surface1 transition-colors">
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}
