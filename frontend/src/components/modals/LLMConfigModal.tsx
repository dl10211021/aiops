import LLMDeleteProviderDialog from './LLMDeleteProviderDialog'
import LLMFetchedModelsList from './LLMFetchedModelsList'
import LLMRuntimeConfigPanel from './LLMRuntimeConfigPanel'
import LLMAssistantModelPanel from './LLMAssistantModelPanel'
import { useLLMConfigData } from './useLLMConfigData'

export default function LLMConfigModal() {
  const {
    assistantConfig,
    assistantSaving,
    closeModal,
    deleteTarget,
    error,
    fetchedModelsInfo,
    handleAddProvider,
    handleDelete,
    handleSave,
    handleSaveAssistantConfig,
    handleSaveRuntime,
    handleTestModels,
    loading,
    modelsCount,
    modelOptions,
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
    updateAssistantDraft,
    updateAssistantTask,
    updateProvider,
    updateRuntimeDraft,
  } = useLLMConfigData()

  return (
    <div className="ops-modal-backdrop" onClick={closeModal}>
      <div className="ops-modal-surface flex h-[min(740px,94vh)] w-full max-w-6xl" onClick={(e) => e.stopPropagation()}>
        
        {/* 左侧：供应商列表 */}
        <div className="flex w-64 flex-col border-r border-ops-surface0 bg-ops-dark/72">
          <div className="flex items-center justify-between border-b border-ops-surface0 p-4">
            <h2 className="text-sm font-bold text-ops-text">模型配置</h2>
            <button onClick={handleAddProvider} className="ops-control rounded-lg px-2 py-1 text-xs font-semibold">+ 添加</button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loading && <div className="mt-4 text-center text-xs text-ops-subtext">正在加载配置...</div>}
            {!loading && providers.map(p => (
              <div 
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={`cursor-pointer rounded-lg px-3 py-2 text-sm transition-colors ${selectedId === p.id ? 'bg-ops-accent/14 text-ops-accent font-semibold ring-1 ring-ops-accent/30' : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'}`}
              >
                {p.name}
              </div>
            ))}
            {!loading && providers.length === 0 && <div className="text-xs text-ops-subtext text-center mt-4">暂无配置</div>}
          </div>
        </div>

        {/* 右侧：详情配置面板 */}
        <div className="flex-1 flex flex-col bg-ops-panel">
          <div className="ops-modal-header h-16">
            <div>
              <h2 className="ops-modal-title">模型配置 · 主模型 / 辅助模型</h2>
              <p className="ops-modal-description">维护模型供应商、主模型、辅助模型和运行参数。</p>
            </div>
            <button onClick={closeModal} className="ops-icon-button" title="关闭">&times;</button>
          </div>

          <div className="ops-modal-body p-6">
            {error && (
              <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
                {error}
              </div>
            )}
            {loading ? (
              <div className="flex h-full items-center justify-center text-sm text-ops-subtext">
                正在读取模型供应商配置...
              </div>
            ) : (
              <div className="space-y-5">
                <LLMAssistantModelPanel
                  config={assistantConfig}
                  modelOptions={modelOptions}
                  saving={assistantSaving}
                  onChange={updateAssistantDraft}
                  onTaskChange={updateAssistantTask}
                  onSave={handleSaveAssistantConfig}
                />

                {selectedProvider ? (
                <>
                <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-ops-text">供应商连接参数</div>
                      <p className="mt-1 text-[11px] text-ops-subtext">这里维护模型网关、API Key 和模型列表；上方负责选择主模型与辅助模型。</p>
                    </div>
                    <span className="rounded bg-ops-surface0 px-2 py-1 text-[10px] text-ops-overlay">{selectedProvider.name}</span>
                  </div>
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
                </div>

                
                <div className="pt-4 border-t border-ops-surface0">
                  <LLMRuntimeConfigPanel
                    runtimeConfig={runtimeConfig}
                    runtimeDraft={runtimeDraft}
                    runtimeSaving={runtimeSaving}
                    onDraftChange={updateRuntimeDraft}
                    onSave={handleSaveRuntime}
                  />

                  <LLMFetchedModelsList fetchedModelsInfo={fetchedModelsInfo} />
                </div>
                
                <div className="pt-2 border-t border-ops-surface0">
                  <button onClick={() => setDeleteTarget(selectedProvider)} className="text-red-400 hover:text-red-300 text-xs px-2 py-1 rounded hover:bg-red-400/10 transition-colors">
                    删除该供应商
                  </button>
                </div>
                </>
                ) : (
                  <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 p-6 text-sm text-ops-subtext">
                    左侧还没有模型供应商。可以先添加供应商和模型列表；主模型/辅助模型配置会在模型列表可用后自动出现选项。
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 右下侧：保存与获取按钮 */}
          <div className="ops-modal-footer justify-between">
            <div className="flex items-center gap-3">
              <button onClick={handleTestModels} disabled={testing || saving || loading} className="ops-control rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50">
                {testing ? '正在与当前模型供应商通信...' : '测试当前供应商并获取模型'}
              </button>
              {modelsCount !== null && <span className="text-xs text-green-400">已成功获取 {modelsCount} 个模型</span>}
            </div>
            <div className="flex gap-2">
              <button onClick={closeModal} className="ops-control rounded-lg px-4 py-2 text-sm font-semibold">取消</button>
              <button onClick={handleSave} disabled={saving || loading} className="ops-primary-action px-4 py-2 text-sm disabled:opacity-50">
                {saving ? '保存中...' : '保存所有更改'}
              </button>
            </div>
          </div>
        </div>
      </div>
      {deleteTarget && (
        <LLMDeleteProviderDialog
          target={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete()}
        />
      )}
    </div>
  )
}
