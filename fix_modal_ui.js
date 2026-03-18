const fs = require('fs');

const modalPath = 'frontend/src/components/modals/LLMConfigModal.tsx';
let modalCode = fs.readFileSync(modalPath, 'utf8');

// We need to add state to store the fetched models so we can display them
if (!modalCode.includes('fetchedModelsInfo')) {
  modalCode = modalCode.replace(
    /const \[modelsCount, setModelsCount\] = useState<number \| null>\(null\)/,
    `const [modelsCount, setModelsCount] = useState<number | null>(null)\n  const [fetchedModelsInfo, setFetchedModelsInfo] = useState<import('@/api/client').ModelGroup[]>([])`
  );

  modalCode = modalCode.replace(
    /const res = await getAvailableModels\(\)\n\s*let count = 0\n\s*res\.data\.models\.forEach\(g => \{ count \+= g\.models\.length \}\)\n\s*setModelsCount\(count\)/,
    `const res = await getAvailableModels()\n      let count = 0\n      res.data.models.forEach(g => { count += g.models.length })\n      setModelsCount(count)\n      setFetchedModelsInfo(res.data.models)`
  );

  // We need to add a section below the forms to show the fetched models
  const displayModelsHtml = `
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
                      点击右下角的"测试全局连接 & 动态获取模型"查看结果
                    </div>
                  )}
                </div>
                
                <div className="pt-2 border-t border-ops-surface0">`;

  modalCode = modalCode.replace(
    /<div className="pt-2 border-t border-ops-surface0">/,
    displayModelsHtml
  );

  fs.writeFileSync(modalPath, modalCode);
  console.log("Updated modal UI successfully");
}
