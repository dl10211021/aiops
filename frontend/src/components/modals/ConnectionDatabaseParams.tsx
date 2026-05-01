import type { OracleClientConfig } from './connectionModalHelpers'

export default function ConnectionDatabaseParams({
  extraArgs,
  oracleClientConfig,
  subType,
  onExtraArgChange,
  onExtraArgsChange,
  oracleThickDefaults,
}: {
  extraArgs: Record<string, unknown>
  oracleClientConfig: OracleClientConfig | null
  subType: string
  onExtraArgChange: (field: string, value: unknown) => void
  onExtraArgsChange: (patch: Record<string, unknown>) => void
  oracleThickDefaults: () => Record<string, unknown>
}) {
  const oracleConnectType = ((extraArgs.oracle_connect_type as string) || 'sid')
  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label className="text-xs text-ops-subtext">
          {subType === 'oracle'
            ? oracleConnectType === 'tns_alias'
              ? 'TNS Alias'
              : 'SID / 服务名'
            : '数据库名 / SID'}
        </label>
        <input
          value={(extraArgs.db_name as string) || (extraArgs.database as string) || ''}
          onChange={(event) => onExtraArgChange('db_name', event.target.value)}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
      <div className="mt-6 flex items-center">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ops-subtext hover:text-ops-text">
          <input
            type="checkbox"
            checked={!!extraArgs.use_ssl}
            onChange={(event) => onExtraArgChange('use_ssl', event.target.checked)}
            className="accent-ops-accent"
          />
          使用 SSL
        </label>
      </div>
      {subType === 'oracle' && (
        <>
          <div>
            <label className="text-xs text-ops-subtext">Oracle 连接类型</label>
            <select
              value={(extraArgs.oracle_connect_type as string) || (extraArgs.connect_type as string) || 'sid'}
              onChange={(event) => onExtraArgChange('oracle_connect_type', event.target.value)}
              className="mt-1 w-full appearance-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="sid">SID</option>
              <option value="service_name">服务名</option>
              <option value="tns_alias">TNS Alias</option>
            </select>
          </div>
          <div className="mt-6 flex items-center">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-ops-subtext hover:text-ops-text">
              <input
                type="checkbox"
                checked={!!extraArgs.use_thick_mode}
                onChange={(event) => onExtraArgsChange({
                  use_thick_mode: event.target.checked,
                  ...(event.target.checked && !extraArgs.oracle_client_lib_dir ? oracleThickDefaults() : {}),
                })}
                className="accent-ops-accent"
              />
              Oracle Thick 模式
            </label>
          </div>
          {!!extraArgs.use_thick_mode && (
            <div className="col-span-2">
              <label className="text-xs text-ops-subtext">Oracle Instant Client 目录</label>
              <input
                value={(extraArgs.oracle_client_lib_dir as string) || ''}
                onChange={(event) => onExtraArgChange('oracle_client_lib_dir', event.target.value)}
                className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                placeholder="${OPSCORE_ORACLE_CLIENT_LIB_DIR}"
              />
              <div className="mt-1 text-[11px] text-ops-subtext">
                {oracleClientConfig?.detected
                  ? `后端已识别本机目录：${oracleClientConfig.lib_dir}。留空时会使用后端变量或自动探测结果，不会把本机路径写入资产。`
                  : '建议留空并在部署环境配置 OPSCORE_ORACLE_CLIENT_LIB_DIR；也可手动填写目录或变量名。'}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
