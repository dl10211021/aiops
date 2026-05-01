export default function ConnectionKubernetesParams({
  extraArgs,
  onExtraArgChange,
}: {
  extraArgs: Record<string, unknown>
  onExtraArgChange: (field: string, value: unknown) => void
}) {
  return (
    <div className="space-y-3">
      <p className="rounded-lg bg-ops-surface0/55 px-3 py-2 text-[11px] leading-5 text-ops-subtext">
        选择 Token 时适合 ServiceAccount；选择 Kubeconfig 时可以粘贴完整配置。生产环境建议使用只读或最小权限凭据。
      </p>
      <div className="flex gap-4">
        <label className="flex cursor-pointer items-center gap-1.5 text-sm text-ops-subtext">
          <input
            type="radio"
            name="k8s_auth"
            value="token"
            checked={extraArgs.k8s_auth_type !== 'kubeconfig'}
            onChange={() => onExtraArgChange('k8s_auth_type', 'token')}
            className="accent-ops-accent"
          /> Token
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-sm text-ops-subtext">
          <input
            type="radio"
            name="k8s_auth"
            value="kubeconfig"
            checked={extraArgs.k8s_auth_type === 'kubeconfig'}
            onChange={() => onExtraArgChange('k8s_auth_type', 'kubeconfig')}
            className="accent-ops-accent"
          /> Kubeconfig
        </label>
      </div>
      {extraArgs.k8s_auth_type === 'kubeconfig' ? (
        <div>
          <label className="text-xs text-ops-subtext">Kubeconfig</label>
          <textarea
            value={(extraArgs.kubeconfig as string) || ''}
            onChange={(event) => onExtraArgChange('kubeconfig', event.target.value)}
            className="mt-1 h-24 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-xs text-ops-text outline-none focus:border-ops-accent"
          />
          <p className="mt-1 text-[11px] leading-4 text-ops-overlay">可包含 clusters、users、contexts；系统会按敏感字段保存。</p>
        </div>
      ) : (
        <div>
          <label className="text-xs text-ops-subtext">Bearer Token</label>
          <input
            type="password"
            value={(extraArgs.bearer_token as string) || ''}
            onChange={(event) => onExtraArgChange('bearer_token', event.target.value)}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
          <p className="mt-1 text-[11px] leading-4 text-ops-overlay">建议使用专用 ServiceAccount Token，不要复用管理员 Token。</p>
        </div>
      )}
    </div>
  )
}
