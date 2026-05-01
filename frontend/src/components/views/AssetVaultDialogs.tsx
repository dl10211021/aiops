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
      <section className="w-full max-w-md rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className="text-xs font-semibold text-ops-alert">删除资产</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认从资产中心移除</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            删除后不会再作为会话、巡检和审批上下文使用，历史记录不会被自动删除。
          </p>
        </div>
        <div className="p-5">
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
            <div className="truncate text-sm font-semibold text-ops-text">{asset.remark || asset.host}</div>
            <div className="mt-1 text-xs text-ops-overlay">
              {asset.username}@{asset.host}:{asset.port} · {display.typeLabel}
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="rounded-lg bg-ops-alert px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
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
      <section className="w-full max-w-lg rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className="text-xs font-semibold text-ops-accent">资产数据规范化</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认执行规范化</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            系统会在执行前生成备份，用于合并重复资产、补齐分类和连接字段，便于后续巡检与会话统一识别。
          </p>
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-2">
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
            <div className="text-xs text-ops-overlay">待规范化资产</div>
            <div className="mt-1 font-mono text-2xl font-semibold text-ops-text">{rowsToUpdate}</div>
          </div>
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
            <div className="text-xs text-ops-overlay">将删除重复资产</div>
            <div className="mt-1 font-mono text-2xl font-semibold text-ops-alert">{duplicatesToRemove}</div>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button
            onClick={onCancel}
            disabled={normalizing}
            className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={normalizing}
            className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark disabled:opacity-50"
          >
            {normalizing ? '处理中...' : '确认规范化'}
          </button>
        </div>
      </section>
    </div>
  )
}
