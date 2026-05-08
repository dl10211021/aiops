import type { Asset } from '@/types'
import type { AssetDisplayMeta } from './AssetVaultParts'

export function DeleteAssetDialog({
  asset,
  deleting,
  display,
  onCancel,
  onConfirm,
}: {
  asset: Asset
  deleting: boolean
  display: AssetDisplayMeta
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={() => !deleting && onCancel()}>
      <section className="ops-modal-surface w-full max-w-md" onClick={(event) => event.stopPropagation()}>
        <div className="ops-modal-header">
          <div className="text-xs font-semibold text-ops-alert">删除资产</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认从资产中心移除</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            删除后不会再作为会话、巡检和审批上下文使用，历史记录不会被自动删除。
          </p>
        </div>
        <div className="p-5">
          <div className="ops-data-panel px-3 py-2">
            <div className="truncate text-sm font-semibold text-ops-text">{asset.remark || asset.host}</div>
            <div className="mt-1 text-xs text-ops-overlay">
              {asset.username}@{asset.host}:{asset.port} · {display.typeLabel}
            </div>
          </div>
        </div>
        <div className="ops-modal-footer">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="ops-muted-action px-4 py-2 text-sm disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="ops-danger-action px-4 py-2 text-sm disabled:opacity-50"
          >
            {deleting ? '删除中...' : '确认删除'}
          </button>
        </div>
      </section>
    </div>
  )
}

export function NormalizeAssetsDialog({
  duplicatesToRemove,
  normalizing,
  rowsToUpdate,
  onCancel,
  onConfirm,
}: {
  duplicatesToRemove: number
  normalizing: boolean
  rowsToUpdate: number
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={() => !normalizing && onCancel()}>
      <section className="ops-modal-surface w-full max-w-lg" onClick={(event) => event.stopPropagation()}>
        <div className="ops-modal-header">
          <div className="text-xs font-semibold text-ops-accent">资产数据规范化</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认执行规范化</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            系统会在执行前生成备份，用于合并重复资产、补齐分类和连接字段，便于后续巡检与会话统一识别。
          </p>
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-2">
          <div className="ops-data-panel p-3">
            <div className="text-xs text-ops-overlay">待规范化资产</div>
            <div className="mt-1 font-mono text-2xl font-semibold text-ops-text">{rowsToUpdate}</div>
          </div>
          <div className="ops-data-panel p-3">
            <div className="text-xs text-ops-overlay">将删除重复资产</div>
            <div className="mt-1 font-mono text-2xl font-semibold text-ops-alert">{duplicatesToRemove}</div>
          </div>
        </div>
        <div className="ops-modal-footer">
          <button
            onClick={onCancel}
            disabled={normalizing}
            className="ops-muted-action px-4 py-2 text-sm disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={normalizing}
            className="ops-primary-action px-4 py-2 text-sm disabled:opacity-50"
          >
            {normalizing ? '处理中...' : '确认规范化'}
          </button>
        </div>
      </section>
    </div>
  )
}

export function BatchImportAssetsDialog({
  draft,
  importing,
  onCancel,
  onChange,
  onConfirm,
}: {
  draft: string
  importing: boolean
  onCancel: () => void
  onChange: (value: string) => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={() => !importing && onCancel()}>
      <section className="ops-modal-surface w-full max-w-3xl" onClick={(event) => event.stopPropagation()}>
        <div className="ops-modal-header">
          <div className="text-xs font-semibold text-ops-accent">批量导入资产</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">导入 JSON 资产数组</h2>
        </div>
        <div className="p-5">
          <textarea
            value={draft}
            onChange={(event) => onChange(event.target.value)}
            rows={12}
            spellCheck={false}
            className="ops-control w-full resize-y px-3 py-3 font-mono text-xs leading-5"
          />
        </div>
        <div className="ops-modal-footer">
          <button
            onClick={onCancel}
            disabled={importing}
            className="ops-muted-action px-4 py-2 text-sm disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={importing}
            className="ops-primary-action px-4 py-2 text-sm disabled:opacity-50"
          >
            {importing ? '导入中...' : '确认导入'}
          </button>
        </div>
      </section>
    </div>
  )
}
