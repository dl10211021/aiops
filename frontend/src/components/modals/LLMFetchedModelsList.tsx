import type { ModelGroup } from '@/api/client'

interface LLMFetchedModelsListProps {
  fetchedModelsInfo: ModelGroup[]
}

export default function LLMFetchedModelsList({ fetchedModelsInfo }: LLMFetchedModelsListProps) {
  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-xs font-medium text-ops-subtext">已拉取到的模型列表</h3>
      </div>

      {fetchedModelsInfo.length > 0 ? (
        <div className="ops-data-panel max-h-40 overflow-y-auto p-2">
          {fetchedModelsInfo.map((group) => (
            <div key={group.provider_id} className="mb-2 last:mb-0">
              <div className="sticky top-0 mb-1 bg-ops-panel/95 py-0.5 text-[11px] text-ops-accent">{group.provider_name}</div>
              <div className="flex flex-wrap gap-1.5 pl-1">
                {group.models.map((model) => (
                  <span
                    key={model.id}
                    className="ops-control px-1.5 py-0.5 font-mono text-[10px] text-ops-text"
                  >
                    {model.name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="ops-data-panel p-3 text-center text-[11px] italic text-ops-subtext">
          点击右下角的"测试当前供应商 & 动态获取模型"查看结果
        </div>
      )}
    </>
  )
}
