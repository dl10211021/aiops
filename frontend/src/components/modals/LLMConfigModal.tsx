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
      <div
        className="ops-modal-surface flex h-[min(820px,94vh)] w-full max-w-6xl flex-col"
        onClick={(e) => e.stopPropagation()}
      >
          <div className="ops-modal-header h-16">
            <div>
              <h2 className="ops-modal-title">模型配置 · 全局主模型 / 辅助模型</h2>
              <p className="ops-modal-description">上方维护全局模型角色和执行保护；下方维护模型供应商、连接参数和模型列表。</p>
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
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
                  <LLMAssistantModelPanel
                    config={assistantConfig}
                    modelOptions={modelOptions}
                    saving={assistantSaving}
                    onChange={updateAssistantDraft}
                    onTaskChange={updateAssistantTask}
                    onSave={handleSaveAssistantConfig}
                  />
                  <LLMRuntimeConfigPanel
                    runtimeConfig={runtimeConfig}
                    runtimeDraft={runtimeDraft}
                    runtimeSaving={runtimeSaving}
                    onDraftChange={updateRuntimeDraft}
                    onSave={handleSaveRuntime}
                  />
                </div>

                <section className="ops-data-panel p-4">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-ops-text">模型供应商与模型列表</div>
                      <p className="mt-1 text-[11px] leading-5 text-ops-subtext">
                        这里统一管理供应商连接、API Key 和可用模型；全局主模型与辅助模型只从这些模型列表中选择。
                      </p>
                    </div>
                    <button onClick={handleAddProvider} className="ops-primary-action px-3 py-1.5 text-xs">
                      + 添加模型供应商
                    </button>
                  </div>

                  {providers.length > 0 ? (
                    <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(220px,280px)_1fr]">
                      <label className="block text-xs text-ops-subtext">
                        当前编辑供应商
                        <select
                          value={selectedId}
                          onChange={(e) => setSelectedId(e.target.value)}
                          className="ops-control mt-1 w-full px-3 py-2 text-sm"
                        >
                          {providers.map((provider) => (
                            <option key={provider.id} value={provider.id}>
                              {provider.name || provider.id}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {providers.map((provider) => (
                          <button
                            key={provider.id}
                            type="button"
                            onClick={() => setSelectedId(provider.id)}
                            className={`rounded-lg border px-3 py-2 text-left transition-colors ${
                              selectedId === provider.id
                                ? 'border-ops-accent/55 bg-ops-accent/12 text-ops-accent'
                                : 'border-ops-surface0 bg-ops-dark/24 text-ops-subtext hover:border-ops-surface1 hover:text-ops-text'
                            }`}
                          >
                            <div className="truncate text-xs font-semibold">{provider.name || provider.id}</div>
                            <div className="mt-1 truncate font-mono text-[10px] text-ops-overlay">
                              {provider.base_url || '官方默认端点'}
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-ops-surface0 bg-ops-dark/25 p-6 text-sm text-ops-subtext">
                      还没有模型供应商。先在下方添加模型供应商，再填写连接参数和模型列表。
                    </div>
                  )}

                  {selectedProvider ? (
                    <div className="space-y-4">
                      <div className="grid gap-4 lg:grid-cols-2">
                        <label className="block text-xs text-ops-subtext">
                          供应商/渠道名称
                          <input
                            value={selectedProvider.name}
                            onChange={(e) => updateProvider({ name: e.target.value })}
                            className="ops-control mt-1 w-full px-3 py-2 text-sm"
                          />
                        </label>

                        <label className="block text-xs text-ops-subtext">
                          内部标识
                          <input
                            value={selectedProvider.id}
                            disabled
                            className="ops-control mt-1 w-full cursor-not-allowed px-3 py-2 text-sm opacity-70"
                          />
                        </label>

                        <label className="block text-xs text-ops-subtext">
                          通信协议
                          <select
                            value={selectedProvider.protocol}
                            onChange={(e) => updateProvider({ protocol: e.target.value })}
                            className="ops-control mt-1 w-full px-3 py-2 text-sm"
                          >
                            <option value="openai">OpenAI 兼容协议</option>
                            <option value="anthropic">Anthropic (Claude) 原生</option>
                          </select>
                        </label>

                        <label className="block text-xs text-ops-subtext">
                          Base URL (兼容网关地址)
                          <input
                            value={selectedProvider.base_url}
                            onChange={(e) => updateProvider({ base_url: e.target.value })}
                            placeholder="https://api.openai.com/v1"
                            className="ops-control mt-1 w-full px-3 py-2 font-mono text-sm"
                          />
                          <span className="mt-1 block text-[11px] text-ops-overlay">
                            本地模型请填入具体地址（如 http://localhost:11434/v1），官方端点可按供应商实际情况留空。
                          </span>
                        </label>

                        <label className="block text-xs text-ops-subtext">
                          API Key
                          <input
                            type="password"
                            value={selectedProvider.api_key}
                            onChange={(e) => updateProvider({ api_key: e.target.value })}
                            placeholder="sk-..."
                            className="ops-control mt-1 w-full px-3 py-2 font-mono text-sm"
                          />
                        </label>

                        <label className="block text-xs text-ops-subtext lg:row-span-2">
                          手动定义模型列表 (逗号分隔)
                          <textarea
                            value={selectedProvider.models}
                            onChange={(e) => updateProvider({ models: e.target.value })}
                            rows={5}
                            placeholder="gpt-4o, gpt-4-turbo"
                            className="ops-control mt-1 w-full resize-none px-3 py-2 font-mono text-sm"
                          />
                          <span className="mt-1 block text-[11px] text-ops-overlay">
                            可手动填写，也可点击底部按钮从当前供应商的 /models 接口强制刷新。
                          </span>
                        </label>
                      </div>

                      <div className="flex justify-end border-t border-ops-surface0 pt-3">
                        <button onClick={() => setDeleteTarget(selectedProvider)} className="ops-danger-action px-3 py-1.5 text-xs">
                          删除该供应商
                        </button>
                      </div>
                    </div>
                  ) : null}
                </section>

                <div className="pt-1">
                  <LLMFetchedModelsList fetchedModelsInfo={fetchedModelsInfo} />
                </div>
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
