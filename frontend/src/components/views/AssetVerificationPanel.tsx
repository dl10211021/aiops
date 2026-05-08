import type { Asset, AssetVerificationMatrix, AssetVerificationRun, InspectionRun } from '@/types'
import { statusLabel } from '@/utils/assetDisplay'
import { AssetMetaLine, type AssetDisplayMeta } from './AssetVaultParts'
import { InspectionRunsSection, VerificationHistorySection, VerificationMatrixSection } from './AssetVerificationSections'

export function VerificationStatusStrip({ matrix }: { matrix: AssetVerificationMatrix }) {
  const ready = matrix.status === 'ready'
  return (
    <div className="ops-data-panel mb-3 flex items-center justify-between px-2.5 py-2">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${ready ? 'bg-ops-success' : 'bg-ops-alert'}`} />
        <span className="text-[11px] text-ops-subtext">{ready ? '主接入就绪' : '主接入需复核'}</span>
      </div>
      <span className="font-mono text-[11px] text-ops-overlay">
        {matrix.coverage.supported}/{matrix.coverage.total}
      </span>
    </div>
  )
}

export function VerificationPanel({
  panel,
  onClose,
  onRun,
  onOpenInspectionReport,
}: {
  panel: {
    asset: Asset
    display: AssetDisplayMeta
    matrix: AssetVerificationMatrix | null
    runs: AssetVerificationRun[]
    inspectionRuns: InspectionRun[]
    loading: boolean
    running: boolean
  }
  onClose: () => void
  onRun: () => void
  onOpenInspectionReport: (runId: string) => void
}) {
  const latest = panel.runs[0]
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/45 backdrop-blur-sm" onClick={onClose}>
      <aside
        className="ops-modal-surface h-full w-full max-w-2xl overflow-y-auto rounded-none border-l border-ops-surface1 p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-ops-accent">资产接入详情</p>
            <h2 className="mt-1 text-xl font-black text-ops-text">{panel.asset.remark || panel.asset.host}</h2>
            <p className="mt-1 text-sm text-ops-subtext">{panel.asset.username}@{panel.asset.host}:{panel.asset.port}</p>
            <div className="mt-3 grid gap-2 text-[11px] text-ops-subtext sm:grid-cols-4">
              <AssetMetaLine label="类型" value={panel.display.typeLabel} />
              <AssetMetaLine label="分类" value={panel.display.categoryLabel} />
              <AssetMetaLine label="工具" value={panel.display.connectorLabel} />
              <AssetMetaLine label="主接入" value={panel.display.protocolLabel} />
            </div>
          </div>
          <button onClick={onClose} className="ops-muted-action px-3 py-1.5 text-sm">关闭</button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button
            onClick={onRun}
            disabled={panel.running || panel.loading}
            className="ops-primary-action px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            {panel.running ? '验证中...' : '验证主接入'}
          </button>
          {latest && (
            <span className={`rounded-full px-3 py-1 text-xs ${latest.status === 'success' ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
              最近结果：{statusLabel(latest.status)}
            </span>
          )}
        </div>

        {panel.loading ? (
          <div className="ops-data-panel p-6 text-sm text-ops-subtext">正在加载资产接入详情...</div>
        ) : (
          <>
            {panel.matrix && <VerificationMatrixSection matrix={panel.matrix} />}
            <VerificationHistorySection runs={panel.runs} />
            <InspectionRunsSection
              runs={panel.inspectionRuns}
              onOpenInspectionReport={onOpenInspectionReport}
            />
          </>
        )}
      </aside>
    </div>
  )
}
