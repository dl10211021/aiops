export default function ConnectionHttpParams({
  extraArgs,
  port,
  onExtraArgChange,
}: {
  extraArgs: Record<string, unknown>
  port: number
  onExtraArgChange: (field: string, value: unknown) => void
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label className="text-xs text-ops-subtext">访问协议</label>
        <select
          value={(extraArgs.scheme as string) || (port === 443 ? 'https' : 'http')}
          onChange={(event) => onExtraArgChange('scheme', event.target.value)}
          className="mt-1 w-full appearance-none rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          <option value="https">HTTPS</option>
          <option value="http">HTTP</option>
        </select>
      </div>
      <div>
        <label className="text-xs text-ops-subtext">基础路径</label>
        <input
          value={(extraArgs.base_path as string) || ''}
          onChange={(event) => onExtraArgChange('base_path', event.target.value)}
          placeholder="/api 或留空"
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
      <div>
        <label className="text-xs text-ops-subtext">API Token</label>
        <input
          type="password"
          value={(extraArgs.api_token as string) || ''}
          onChange={(event) => onExtraArgChange('api_token', event.target.value)}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
      <div>
        <label className="text-xs text-ops-subtext">Token 请求头</label>
        <input
          value={(extraArgs.auth_header as string) || 'Authorization'}
          onChange={(event) => onExtraArgChange('auth_header', event.target.value)}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
    </div>
  )
}
