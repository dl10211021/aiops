interface ConnectionCredentialSectionProps {
  host: string
  inferredHostFromEndpoint: string
  isEndpointBackedAsset: boolean
  password: string
  port: number
  showPass: boolean
  showUser: boolean
  targetScope: string
  username: string
  onHostChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onPortChange: (value: number) => void
  onUsernameChange: (value: string) => void
}

export default function ConnectionCredentialSection({
  host,
  inferredHostFromEndpoint,
  isEndpointBackedAsset,
  password,
  port,
  showPass,
  showUser,
  targetScope,
  username,
  onHostChange,
  onPasswordChange,
  onPortChange,
  onUsernameChange,
}: ConnectionCredentialSectionProps) {
  return (
    <section className="ops-data-panel p-3">
      <div className="mb-3 text-xs font-semibold text-ops-text">连接地址与凭据</div>
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <label className="text-xs text-ops-subtext">
            {isEndpointBackedAsset ? '资产地址' : '主机地址'} {targetScope === 'group' && '(代表主机)'}
          </label>
          <input
            value={host}
            onChange={(event) => onHostChange(event.target.value)}
            className="ops-control mt-1 w-full px-3 py-2 text-sm"
            placeholder={isEndpointBackedAsset ? (inferredHostFromEndpoint || '可从 Endpoint/Base URL 自动识别') : '192.168.1.100'}
          />
          {isEndpointBackedAsset && (
            <p className="mt-1 text-[11px] leading-4 text-ops-overlay">
              {inferredHostFromEndpoint
                ? `将从 Endpoint/Base URL 识别为 ${inferredHostFromEndpoint}。`
                : '如果填写 Endpoint URL 或 Base URL，这里可以暂时留空。'}
            </p>
          )}
        </div>
        <div>
          <label className="text-xs text-ops-subtext">端口</label>
          <input
            type="number"
            value={port}
            onChange={(event) => onPortChange(parseInt(event.target.value) || 22)}
            className="ops-control mt-1 w-full px-3 py-2 text-sm"
          />
        </div>
      </div>

      {(showUser || showPass) && (
        <div className="grid grid-cols-2 gap-3">
          {showUser && (
            <div>
              <label className="text-xs text-ops-subtext">用户名</label>
              <input
                value={username}
                onChange={(event) => onUsernameChange(event.target.value)}
                className="ops-control mt-1 w-full px-3 py-2 text-sm"
              />
            </div>
          )}
          {showPass && (
            <div className={!showUser ? 'col-span-2' : ''}>
              <label className="text-xs text-ops-subtext">密码</label>
              <input
                type="password"
                value={password}
                onChange={(event) => onPasswordChange(event.target.value)}
                className="ops-control mt-1 w-full px-3 py-2 text-sm"
              />
            </div>
          )}
        </div>
      )}
    </section>
  )
}
