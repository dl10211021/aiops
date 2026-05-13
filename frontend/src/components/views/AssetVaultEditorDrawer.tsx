import { useMemo, useState, type ReactNode } from 'react'
import type { Asset, AssetParamDefinition, AssetTypeDefinition, ToolDisplayDetail } from '@/types'
import { toolLabel } from '@/utils/assetDisplay'
import {
  DEFAULT_SESSION_GROUP,
  normalizeSessionGroupName,
  uniqueSessionGroups,
  withPrimaryGroup,
} from '@/features/sessions/sessionGroups'
import ConnectionAdvancedParamsSection from '@/components/modals/ConnectionAdvancedParamsSection'
import ConnectionDedicatedParamsSection from '@/components/modals/ConnectionDedicatedParamsSection'
import { authModeFor } from '@/components/modals/connectionAuthRules'
import {
  CORE_ASSET_PARAM_FIELDS,
  DATABASE_DEDICATED_PARAM_FIELDS,
  DEDICATED_HTTP_CONNECTORS,
  HTTP_BACKED_PROTOCOLS,
  HTTP_DEDICATED_PARAM_FIELDS,
  K8S_DEDICATED_PARAM_FIELDS,
  SNMP_DEDICATED_PARAM_FIELDS,
  groupParamDefinitions,
} from '@/components/modals/connectionParamDefinitions'
import type { AssetDisplayMeta } from './AssetVaultParts'

type AssetVaultEditorDrawerProps = {
  asset: Asset
  catalogTypes: AssetTypeDefinition[]
  display: AssetDisplayMeta
  saving: boolean
  sessionGroups: string[]
  onClose: () => void
  onConnect: (asset: Asset) => void
  onOpenVerification: (asset: Asset) => void
  onSave: (asset: Asset, patch: Partial<Asset>) => void
}

export function AssetVaultEditorDrawer({
  asset,
  catalogTypes,
  display,
  saving,
  sessionGroups,
  onClose,
  onConnect,
  onOpenVerification,
  onSave,
}: AssetVaultEditorDrawerProps) {
  const initialExtraArgs = normalizeExtraArgs(asset.extra_args)
  const [remark, setRemark] = useState(asset.remark || '')
  const [host, setHost] = useState(asset.host || '')
  const [port, setPort] = useState(String(asset.port || ''))
  const [username, setUsername] = useState(asset.username || '')
  const [password, setPassword] = useState('')
  const [assetType, setAssetType] = useState(asset.asset_type || '')
  const [protocol, setProtocol] = useState(asset.protocol || asset.asset_type || '')
  const [agentProfile, setAgentProfile] = useState(asset.agent_profile || 'default')
  const [groupName, setGroupName] = useState(normalizeSessionGroupName(asset.tags?.[0]) || DEFAULT_SESSION_GROUP)
  const [tagsText, setTagsText] = useState((asset.tags || []).slice(1).join(', '))
  const [extraArgs, setExtraArgs] = useState<Record<string, unknown>>(initialExtraArgs)
  const [extraArgsText, setExtraArgsText] = useState(JSON.stringify(initialExtraArgs, null, 2))
  const [error, setError] = useState<string | null>(null)
  const selectedType = useMemo(
    () => catalogTypes.find((item) => item.id === assetType),
    [assetType, catalogTypes]
  )
  const currentProtocol = protocol.trim() || selectedType?.protocol || asset.protocol || asset.asset_type
  const accessProtocols = selectedType?.access_protocols?.length
    ? selectedType.access_protocols
    : currentProtocol
      ? [{ protocol: currentProtocol, label: display.protocolLabel || currentProtocol }]
      : []
  const currentAccessProtocol = accessProtocols.find((item) => item.protocol === currentProtocol)
  const selectedTools = selectedType?.capability?.tools || selectedType?.capability?.connector_group?.tools || []
  const selectedToolDetails: ToolDisplayDetail[] = selectedType?.capability?.tool_details?.length
    ? selectedType.capability.tool_details
    : selectedTools.map((name) => ({ name }))
  const selectedCategory = selectedType?.category || String(extraArgs.category || '')
  const selectedSubType = selectedType?.id || String(extraArgs.sub_type || assetType || '')
  const selectedConnector = selectedType?.capability?.connector || ''
  const authVisibility = authVisibilityFor(assetType, currentProtocol, selectedType)
  const isKubernetesAsset = ['k8s', 'kubernetes'].includes(selectedSubType) || currentProtocol === 'k8s'
  const shouldShowGenericHttpParams =
    (['http_api', 'redfish'].includes(currentProtocol) || HTTP_BACKED_PROTOCOLS.has(currentProtocol))
    && !DEDICATED_HTTP_CONNECTORS.has(selectedConnector)
  const selectedConnectorLabel =
    currentAccessProtocol?.label
    || selectedType?.capability?.connector_group?.label
    || selectedType?.capability?.connector
    || currentProtocol
  const extensionParamGroups = useMemo(() => {
    const params = selectedType?.params || selectedType?.capability?.parameter_template || []
    return groupParamDefinitions(params.filter((param) => {
      if (CORE_ASSET_PARAM_FIELDS.has(param.field)) return false
      if (selectedCategory === 'db' && DATABASE_DEDICATED_PARAM_FIELDS.has(param.field)) return false
      if (isKubernetesAsset && K8S_DEDICATED_PARAM_FIELDS.has(param.field)) return false
      if (currentProtocol === 'snmp' && SNMP_DEDICATED_PARAM_FIELDS.has(param.field)) return false
      if (shouldShowGenericHttpParams && HTTP_DEDICATED_PARAM_FIELDS.has(param.field)) return false
      return shouldShowParam(param, extraArgs)
    }))
  }, [currentProtocol, extraArgs, isKubernetesAsset, selectedCategory, selectedType, shouldShowGenericHttpParams])
  const groupOptions = useMemo(
    () => uniqueSessionGroups([...sessionGroups, ...(asset.tags || []), DEFAULT_SESSION_GROUP]),
    [asset.tags, sessionGroups]
  )

  const syncExtraArgs = (next: Record<string, unknown>) => {
    setExtraArgs(next)
    setExtraArgsText(JSON.stringify(next, null, 2))
    setError(null)
  }

  const handleExtraArgChange = (field: string, value: unknown) => {
    syncExtraArgs({ ...extraArgs, [field]: value })
  }

  const handleExtraArgsPatch = (patch: Record<string, unknown>) => {
    syncExtraArgs({ ...extraArgs, ...patch })
  }

  const handleExtraArgsBlur = () => {
    const parsed = parseExtraArgsText(extraArgsText)
    if (!parsed) {
      setError('高级参数 JSON 格式不正确')
      return
    }
    setExtraArgs(parsed)
    setError(null)
  }

  const applyTypeDefault = () => {
    if (!selectedType) return
    setProtocol(selectedType.protocol || protocol)
    setPort(String(selectedType.default_port || port || ''))
    handleExtraArgsPatch({
      category: selectedType.category,
      sub_type: selectedType.id,
      ...(selectedType.category === 'db' ? { db_type: selectedType.id } : {}),
    })
  }

  const submit = () => {
    const normalizedHost = host.trim()
    const normalizedPort = Number(port)
    const normalizedGroup = normalizeSessionGroupName(groupName) || DEFAULT_SESSION_GROUP
    if (!normalizedHost) {
      setError('请输入主机、IP 或访问地址')
      return
    }
    if (!Number.isInteger(normalizedPort) || normalizedPort <= 0 || normalizedPort > 65535) {
      setError('端口必须是 1-65535 之间的数字')
      return
    }
    const parsedExtraArgs = parseExtraArgsText(extraArgsText)
    if (!parsedExtraArgs) {
      setError('高级参数 JSON 格式不正确')
      return
    }
    if (selectedType) {
      parsedExtraArgs.category = selectedType.category
      parsedExtraArgs.sub_type = selectedType.id
      if (selectedType.category === 'db') parsedExtraArgs.db_type = selectedType.id
    }
    if (currentProtocol) {
      parsedExtraArgs.login_protocol = currentProtocol
      parsedExtraArgs.protocol = currentProtocol
    }
    const patch: Partial<Asset> = {
      remark: remark.trim() || normalizedHost,
      host: normalizedHost,
      port: normalizedPort,
      username: username.trim(),
      asset_type: assetType.trim() || asset.asset_type,
      protocol: currentProtocol,
      agent_profile: agentProfile.trim() || 'default',
      extra_args: parsedExtraArgs,
      tags: withPrimaryGroup(parseTags(tagsText), normalizedGroup),
      skills: asset.skills || [],
    }
    if (authVisibility.showPass) {
      patch.password = password || (asset.password ? MANAGED_SECRET_MASK : undefined)
    }
    setError(null)
    onSave(asset, patch)
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55">
      <aside className="ops-modal-surface flex h-full w-full max-w-[760px] flex-col rounded-none border-l border-ops-surface1">
        <header className="border-b border-ops-surface1 bg-[linear-gradient(135deg,rgba(38,207,175,0.12),rgba(10,18,32,0.96)_55%,rgba(44,88,148,0.14))] px-5 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-ops-accent/35 bg-ops-accent/10 px-2.5 py-1 text-[11px] font-semibold text-ops-accent">
                  资产详情 / 编辑
                </span>
                <span className="rounded-full border border-ops-surface1 bg-ops-dark/45 px-2.5 py-1 text-[11px] text-ops-subtext">
                  {display.typeLabel} · {display.protocolLabel}
                </span>
              </div>
              <h2 className="truncate text-lg font-bold text-ops-text" title={asset.remark || asset.host}>
                {asset.remark || asset.host}
              </h2>
              <p className="mt-1 text-xs text-ops-overlay">
                修改资产台账信息；密码留空时保留平台托管的原凭据。
              </p>
            </div>
            <button
              onClick={onClose}
              className="ops-muted-action px-3 py-1.5 text-sm"
            >
              关闭
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <section className="ops-data-panel mb-4 grid gap-3 p-4 md:grid-cols-3">
            <InfoItem label="资产 ID" value={String(asset.id)} />
            <InfoItem label="当前地址" value={`${asset.host}:${asset.port}`} />
            <InfoItem label="资产组" value={normalizeSessionGroupName(asset.tags?.[0]) || DEFAULT_SESSION_GROUP} />
          </section>

          <section className="grid gap-4">
            <EditorBlock title="基础信息" hint="用于列表、会话标题和资产检索。">
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="显示名称">
                  <input value={remark} onChange={(event) => setRemark(event.target.value)} className={inputClass} placeholder="例如：生产数据库、核心交换机" />
                </Field>
                <Field label="主机 / 地址">
                  <input value={host} onChange={(event) => setHost(event.target.value)} className={inputClass} placeholder="IP、域名或 API 地址" />
                </Field>
                <Field label="端口">
                  <input value={port} onChange={(event) => setPort(event.target.value)} className={inputClass} inputMode="numeric" placeholder="1-65535" />
                </Field>
                {authVisibility.showUser && (
                  <Field label="账号">
                    <input value={username} onChange={(event) => setUsername(event.target.value)} className={inputClass} placeholder="登录账号" />
                  </Field>
                )}
                {authVisibility.showPass && (
                  <Field label={asset.password ? '密码（留空保持原密码）' : '密码'}>
                    <input
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className={inputClass}
                      type="password"
                      autoComplete="new-password"
                      placeholder={asset.password ? '留空保持平台托管密码' : '请输入登录密码'}
                    />
                  </Field>
                )}
              </div>
            </EditorBlock>

            <EditorBlock title="资产类型与主接入" hint="类型决定默认协议、巡检方式和可暴露给 AI 的工具。">
              <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                <Field label="资产类型">
                  <select
                    value={assetType}
                    onChange={(event) => setAssetType(event.target.value)}
                    className={inputClass}
                  >
                    {catalogTypes.map((item) => (
                      <option key={item.id} value={item.id}>{item.label || item.id}</option>
                    ))}
                    {!catalogTypes.some((item) => item.id === assetType) && (
                      <option value={assetType}>{assetType || '未标记类型'}</option>
                    )}
                  </select>
                </Field>
                <Field label="主接入协议">
                  <select
                    value={currentProtocol}
                    onChange={(event) => {
                      const nextProtocol = event.target.value
                      setProtocol(nextProtocol)
                      handleExtraArgsPatch({ login_protocol: nextProtocol, protocol: nextProtocol })
                    }}
                    className={inputClass}
                  >
                    {accessProtocols.map((item) => (
                      <option key={item.protocol} value={item.protocol}>
                        {item.label || item.protocol}
                      </option>
                    ))}
                    {!accessProtocols.some((item) => item.protocol === currentProtocol) && currentProtocol && (
                      <option value={currentProtocol}>{currentProtocol}</option>
                    )}
                  </select>
                </Field>
                <div className="flex items-end">
                  <button
                    onClick={applyTypeDefault}
                    disabled={!selectedType}
                    className="ops-muted-action h-10 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    应用默认
                  </button>
                </div>
              </div>
              <p className="mt-2 text-[11px] text-ops-overlay">
                默认建议：Linux 使用 SSH，Windows 使用 WinRM，数据库使用原生数据库协议，ESXi 可按实际接入选择 SSH/API。
              </p>
              {selectedToolDetails.length > 0 && (
                <details className="ops-data-panel mt-3 px-3 py-2">
                  <summary className="cursor-pointer text-[11px] font-semibold text-ops-subtext">
                    AI 工具目录 {selectedToolDetails.length} 个
                  </summary>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selectedToolDetails.map((tool) => (
                      <span
                        key={tool.name}
                        title={[tool.name, tool.description].filter(Boolean).join(' · ')}
                        className="ops-control px-2 py-0.5 text-[10px] text-ops-subtext"
                      >
                        {tool.label || toolLabel(tool.name)}
                      </span>
                    ))}
                  </div>
                </details>
              )}
            </EditorBlock>

            <EditorBlock title="连接参数" hint="与新建资产使用同一套资产类型参数，包含 Oracle、SNMP、K8S、HTTP API 等专用配置。">
              <div className="space-y-3">
                <ConnectionDedicatedParamsSection
                  category={selectedCategory}
                  currentProtocol={currentProtocol}
                  extraArgs={extraArgs}
                  isKubernetesAsset={isKubernetesAsset}
                  oracleClientConfig={null}
                  port={Number(port) || selectedType?.default_port || asset.port || 0}
                  selectedConnectorLabel={selectedConnectorLabel}
                  shouldShowGenericHttpParams={shouldShowGenericHttpParams}
                  subType={selectedSubType}
                  onExtraArgChange={handleExtraArgChange}
                  onExtraArgsChange={handleExtraArgsPatch}
                  oracleThickDefaults={() => ({ use_thick_mode: true })}
                />
                <ConnectionAdvancedParamsSection
                  connectorLabel={selectedConnectorLabel}
                  extraArgs={extraArgs}
                  maturity={selectedType?.capability?.maturity}
                  paramGroups={extensionParamGroups}
                  onParamChange={handleExtraArgChange}
                />
                {selectedCategory !== 'db'
                  && currentProtocol !== 'snmp'
                  && !isKubernetesAsset
                  && !shouldShowGenericHttpParams
                  && extensionParamGroups.length === 0
                  && (
                    <p className="rounded-lg bg-ops-surface0/55 px-3 py-2 text-[11px] leading-5 text-ops-subtext">
                      当前资产类型没有额外连接参数。
                    </p>
                  )}
              </div>
            </EditorBlock>

            <EditorBlock title="分组与标签" hint="资产组会同步用于资产列表和批量会话；其它标签用于检索。">
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="资产组">
                  <input
                    value={groupName}
                    onChange={(event) => setGroupName(event.target.value)}
                    className={inputClass}
                    list="asset-editor-groups"
                    placeholder="例如：数据库、网络设备、生产区"
                  />
                  <datalist id="asset-editor-groups">
                    {groupOptions.map((item) => <option key={item} value={item} />)}
                  </datalist>
                </Field>
                <Field label="其它标签">
                  <input value={tagsText} onChange={(event) => setTagsText(event.target.value)} className={inputClass} placeholder="英文逗号或中文顿号分隔" />
                </Field>
              </div>
            </EditorBlock>

            <EditorBlock title="高级参数 JSON" hint="保留少数特殊资产需要的扩展配置；保存前会校验 JSON 对象。">
              <textarea
                value={extraArgsText}
                onChange={(event) => setExtraArgsText(event.target.value)}
                onBlur={handleExtraArgsBlur}
                className="ops-control min-h-40 w-full px-3 py-2 font-mono text-xs"
                spellCheck={false}
              />
            </EditorBlock>
          </section>
        </div>

        <footer className="ops-modal-footer">
          {error && (
            <div className="mb-3 rounded-lg border border-rose-400/35 bg-rose-400/10 px-3 py-2 text-xs text-rose-100">
              {error}
            </div>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-ops-overlay">
              保存后可继续在当前资产上执行验证或进入会话。
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => onOpenVerification(asset)}
                className="ops-muted-action px-3 py-2 text-sm text-ops-success"
              >
                验证
              </button>
              <button
                onClick={() => onConnect(asset)}
                className="ops-muted-action px-3 py-2 text-sm text-ops-accent"
              >
                进入会话
              </button>
              <button
                onClick={submit}
                disabled={saving}
                className="ops-primary-action px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? '保存中...' : '保存资产'}
              </button>
            </div>
          </div>
        </footer>
      </aside>
    </div>
  )
}

function EditorBlock({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section className="ops-data-panel p-4">
      <div className="mb-3">
        <h3 className="text-sm font-bold text-ops-text">{title}</h3>
        <p className="mt-1 text-[11px] text-ops-overlay">{hint}</p>
      </div>
      {children}
    </section>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-xs font-semibold text-ops-subtext">
      {label}
      {children}
    </label>
  )
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate font-mono text-sm font-semibold text-ops-text" title={value}>{value || '-'}</div>
    </div>
  )
}

function parseTags(value: string) {
  return value
    .split(/[,\u3001]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function normalizeExtraArgs(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  return { ...(value as Record<string, unknown>) }
}

function parseExtraArgsText(value: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(value || '{}') as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
    return parsed as Record<string, unknown>
  } catch {
    return null
  }
}

function shouldShowParam(param: AssetParamDefinition, extraArgs: Record<string, unknown>) {
  if (!param.depend) return true
  return Object.entries(param.depend).every(([field, allowed]) => {
    const current = extraArgs[field]
    return allowed.map(String).includes(String(current))
  })
}

function authVisibilityFor(assetType: string, protocol: string, selectedType?: AssetTypeDefinition) {
  const authMode = authModeFor(selectedType?.id || assetType, protocol || selectedType?.protocol, selectedType?.capability)
  if (authMode === 'password_only') return { showUser: false, showPass: true }
  if (authMode === 'custom_snmp' || authMode === 'none') return { showUser: false, showPass: false }
  return { showUser: true, showPass: true }
}

const MANAGED_SECRET_MASK = '*'.repeat(8)

const inputClass = 'ops-control h-10 px-3 text-sm'
