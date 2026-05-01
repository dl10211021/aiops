export default function ConnectionSnmpParams({
  extraArgs,
  onExtraArgChange,
}: {
  extraArgs: Record<string, unknown>
  onExtraArgChange: (field: string, value: unknown) => void
}) {
  const version = ((extraArgs.snmp_version as string) || 'v2c')
  return (
    <div className="space-y-3">
      <p className="rounded-lg bg-ops-surface0/55 px-3 py-2 text-[11px] leading-5 text-ops-subtext">
        v2c 只需要 Community；v3 需要认证用户、认证密码，可选加密密码。网络设备和 NAS/SAN 推荐生产使用 v3。
      </p>
      <div>
        <label className="text-xs text-ops-subtext">SNMP 版本</label>
        <select
          value={version}
          onChange={(event) => onExtraArgChange('snmp_version', event.target.value)}
          className="mt-1 w-full appearance-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          <option value="v2c">v2c</option>
          <option value="v3">v3</option>
        </select>
      </div>
      {version === 'v2c' ? (
        <div>
          <label className="text-xs text-ops-subtext">Community 字符串</label>
          <input
            type="password"
            value={(extraArgs.community_string as string) || ''}
            onChange={(event) => onExtraArgChange('community_string', event.target.value)}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
          <p className="mt-1 text-[11px] leading-4 text-ops-overlay">如果设备仍使用 public，建议后续在设备侧改为专用只读 Community。</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-ops-subtext">认证用户</label>
            <input
              value={(extraArgs.v3_auth_user as string) || ''}
              onChange={(event) => onExtraArgChange('v3_auth_user', event.target.value)}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            />
          </div>
          <div>
            <label className="text-xs text-ops-subtext">认证协议</label>
            <select
              value={(extraArgs.v3_auth_protocol as string) || 'MD5'}
              onChange={(event) => onExtraArgChange('v3_auth_protocol', event.target.value)}
              className="mt-1 w-full appearance-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="MD5">MD5</option>
              <option value="SHA">SHA</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-ops-subtext">认证密码</label>
            <input
              type="password"
              value={(extraArgs.v3_auth_pass as string) || ''}
              onChange={(event) => onExtraArgChange('v3_auth_pass', event.target.value)}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            />
          </div>
          <div className="col-span-1" />
          <div>
            <label className="text-xs text-ops-subtext">加密协议</label>
            <select
              value={(extraArgs.v3_priv_protocol as string) || 'DES'}
              onChange={(event) => onExtraArgChange('v3_priv_protocol', event.target.value)}
              className="mt-1 w-full appearance-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="DES">DES</option>
              <option value="AES">AES</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-ops-subtext">加密密码</label>
            <input
              type="password"
              value={(extraArgs.v3_priv_pass as string) || ''}
              onChange={(event) => onExtraArgChange('v3_priv_pass', event.target.value)}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            />
          </div>
        </div>
      )}
    </div>
  )
}
