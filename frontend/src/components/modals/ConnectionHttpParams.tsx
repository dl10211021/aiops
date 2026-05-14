export default function ConnectionHttpParams({
  extraArgs,
  port,
  onExtraArgChange,
}: {
  extraArgs: Record<string, unknown>
  port: number
  onExtraArgChange: (field: string, value: unknown) => void
}) {
  const authType = (extraArgs.auth_type as string) || 'auto'

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
        <label className="text-xs text-ops-subtext">认证模式</label>
        <select
          value={authType}
          onChange={(event) => onExtraArgChange('auth_type', event.target.value)}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          <option value="auto">自动识别</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Token</option>
          <option value="api_key">API Key Header</option>
          <option value="raw">原样写入</option>
        </select>
      </div>
      <div>
        <label className="text-xs text-ops-subtext">认证请求头</label>
        <input
          value={(extraArgs.auth_header as string) || 'Authorization'}
          onChange={(event) => onExtraArgChange('auth_header', event.target.value)}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
      <div>
        <label className="text-xs text-ops-subtext">API Token / Header 值</label>
        <input
          type="password"
          value={(extraArgs.api_token as string) || ''}
          onChange={(event) => onExtraArgChange('api_token', event.target.value)}
          placeholder={authType === 'basic' ? 'base64(user:pass) 或完整 Basic ...' : ''}
          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
      <div className="col-span-2">
        <label className="text-xs text-ops-subtext">自定义 Headers</label>
        <textarea
          value={(extraArgs.custom_headers as string) || ''}
          onChange={(event) => onExtraArgChange('custom_headers', event.target.value)}
          placeholder={'kbn-xsrf: true\nX-Requested-By: OpsCore'}
          className="mt-1 min-h-20 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-xs text-ops-text outline-none focus:border-ops-accent"
        />
      </div>
    </div>
  )
}
