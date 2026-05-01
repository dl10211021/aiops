import { statusLabel } from '@/utils/assetDisplay'
import type { DatabaseDriverCapability } from './connectionModalHelpers'

interface ConnectionDatabaseDriverStatusProps {
  driver: DatabaseDriverCapability
  isOracle: boolean
  selectedConnectorLabel: string
}

export default function ConnectionDatabaseDriverStatus({
  driver,
  isOracle,
  selectedConnectorLabel,
}: ConnectionDatabaseDriverStatusProps) {
  return (
    <div className="rounded-lg border border-ops-surface1 bg-ops-dark/30 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-ops-text">数据库驱动状态</div>
          <div className="mt-0.5 text-[11px] text-ops-subtext">
            {driver.label} · {selectedConnectorLabel}
          </div>
        </div>
        <span
          className={`rounded px-2 py-0.5 text-[10px] ${
            driver.status === 'ready'
              ? 'bg-ops-success/15 text-ops-success'
              : 'bg-ops-alert/15 text-ops-alert'
          }`}
        >
          {driver.status === 'ready' ? '可用' : statusLabel(driver.status)}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-[11px] leading-5 text-ops-subtext">
        <div>
          Python 驱动：{driver.python_package}
          {driver.python_package_installed ? ' 已安装' : ' 未安装'}
        </div>
        {driver.external_client_name && (
          <div>
            外部客户端：{driver.external_client_name}
            {driver.external_client_required
              ? (driver.external_client_detected ? ' 已检测到' : ' 未检测到')
              : (driver.external_client_detected ? ' 已检测到，可增强兼容性' : ' 非必需')}
          </div>
        )}
        <div>{driver.install_hint}</div>
        {driver.operation_profile && (
          <>
            <div>
              连接标识：{driver.operation_profile.identity_label}
              {' · '}
              验证语句：{driver.operation_profile.test_statement}
            </div>
            <div>只读示例：{driver.operation_profile.readonly_examples.slice(0, 2).join('；')}</div>
            <div>{driver.operation_profile.operator_note}</div>
          </>
        )}
        {isOracle && (
          <div className="rounded border border-ops-surface1/70 bg-ops-panel/60 p-2 font-mono text-[10px] text-ops-text">
            Windows: {driver.recommended_path_windows}
            <br />
            Linux: {driver.recommended_path_linux}
            <br />
            OPSCORE_ORACLE_CLIENT_LIB_DIR=${'{'}ORACLE_INSTANT_CLIENT_DIR{'}'}
          </div>
        )}
      </div>
    </div>
  )
}
