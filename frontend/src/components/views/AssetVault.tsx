import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { getSavedAssets, deleteAsset } from '@/api/client'
import type { Asset } from '@/types'

export default function AssetVault() {
  const assets = useStore((s) => s.assets)
  const setAssets = useStore((s) => s.setAssets)
  const openModal = useStore((s) => s.openModal)
  const addToast = useStore((s) => s.addToast)
  const [search, setSearch] = useState('')

  const loadAssets = useCallback(async () => {
    try {
      const res = await getSavedAssets()
      setAssets(res.data.assets || [])
    } catch {
      addToast('加载资产列表失败', 'error')
    }
  }, [setAssets, addToast])

  useEffect(() => { loadAssets() }, [loadAssets])

  const handleDelete = async (id: number) => {
    if (!confirm('确定要从金库中移除此资产？')) return
    try {
      await deleteAsset(id)
      setAssets(assets.filter((a) => a.id !== id))
      addToast('资产已移除', 'success')
    } catch {
      addToast('删除失败', 'error')
    }
  }

  const handleConnect = (asset: Asset) => {
    sessionStorage.setItem('prefill_asset', JSON.stringify(asset))
    openModal('connect')
  }

  const filtered = assets.filter((a) => {
    const q = search.toLowerCase()
    return !q || a.host.toLowerCase().includes(q) || (a.remark || '').toLowerCase().includes(q)
  })

  const grouped: Record<string, Asset[]> = {}
  filtered.forEach((a) => {
    const g = (a.tags && a.tags[0]) || '未分组'
    if (!grouped[g]) grouped[g] = []
    grouped[g].push(a)
  })

  const protocolBadge = (p: string) => {
    const colors: Record<string, string> = {
      ssh: 'bg-blue-500/20 text-blue-400',
      database: 'bg-purple-500/20 text-purple-400',
      api: 'bg-green-500/20 text-green-400',
      winrm: 'bg-orange-500/20 text-orange-400',
    }
    return colors[p] || 'bg-ops-surface1 text-ops-subtext'
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-ops-text">🏦 资产金库</h1>
            <p className="text-sm text-ops-subtext mt-1">管理所有已保存的远程资产连接凭据</p>
          </div>
          <div className="flex gap-2">
            <input type="text" placeholder="搜索资产..." value={search} onChange={(e) => setSearch(e.target.value)}
              className="bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-1.5 text-sm text-ops-text outline-none focus:border-ops-accent" />
            <button onClick={() => openModal('connect')}
              className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors">+ 新建连接</button>
            <button onClick={loadAssets}
              className="bg-ops-surface0 text-ops-subtext text-sm px-3 py-1.5 rounded-lg hover:text-ops-text transition-colors">🔄</button>
          </div>
        </div>

        {Object.entries(grouped).map(([group, items]) => (
          <div key={group} className="mb-6">
            <h2 className="text-sm font-semibold text-ops-subtext mb-3">{group} ({items.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {items.map((asset) => (
                <div key={asset.id} className="bg-ops-panel border border-ops-surface0 rounded-xl p-4 hover:border-ops-accent/40 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div className="min-w-0">
                      <div className="font-medium text-ops-text text-sm truncate">{asset.remark || asset.host}</div>
                      <div className="text-xs text-ops-overlay mt-0.5">{asset.username}@{asset.host}:{asset.port}</div>
                    </div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${protocolBadge(asset.asset_type)}`}>{asset.asset_type.toUpperCase()}</span>
                  </div>
                  {asset.skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {asset.skills.slice(0, 3).map((sk) => (
                        <span key={sk} className="text-[10px] bg-ops-surface0 text-ops-subtext px-1.5 py-0.5 rounded">{sk}</span>
                      ))}
                      {asset.skills.length > 3 && <span className="text-[10px] text-ops-overlay">+{asset.skills.length - 3}</span>}
                    </div>
                  )}
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handleConnect(asset)} className="flex-1 bg-ops-accent/15 text-ops-accent text-xs py-1.5 rounded-lg hover:bg-ops-accent/25 transition-colors">✏️ 编辑 / 连接</button>
                    <button onClick={() => handleDelete(asset.id)} className="text-ops-overlay text-xs px-2 py-1.5 rounded-lg hover:text-ops-alert hover:bg-ops-alert/10 transition-colors">🗑️</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="text-center text-ops-subtext py-20">
            <div className="text-4xl mb-3">🏦</div>
            <p>金库中暂无资产</p>
            <p className="text-xs mt-1">连接过的资产会自动保存在这里</p>
          </div>
        )}
      </div>
    </div>
  )
}
