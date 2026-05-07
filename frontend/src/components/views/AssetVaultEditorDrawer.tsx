import { useMemo, useState, type ReactNode } from 'react'
import type { Asset, AssetTypeDefinition } from '@/types'
import {
  DEFAULT_SESSION_GROUP,
  normalizeSessionGroupName,
  uniqueSessionGroups,
  withPrimaryGroup,
} from '@/features/sessions/sessionGroups'
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
  const initialExtraArgs = asset.extra_args || {}
  const initialDatabaseKey = Object.prototype.hasOwnProperty.call(initialExtraArgs, 'db_name') ? 'db_name' : 'database'
  const [remark, setRemark] = useState(asset.remark || '')
  const [host, setHost] = useState(asset.host || '')
  const [port, setPort] = useState(String(asset.port || ''))
  const [username, setUsername] = useState(asset.username || '')
  const [assetType, setAssetType] = useState(asset.asset_type || '')
  const [protocol, setProtocol] = useState(asset.protocol || asset.asset_type || '')
  const [agentProfile, setAgentProfile] = useState(asset.agent_profile || 'default')
  const [groupName, setGroupName] = useState(normalizeSessionGroupName(asset.tags?.[0]) || DEFAULT_SESSION_GROUP)
  const [tagsText, setTagsText] = useState((asset.tags || []).slice(1).join(', '))
  const [databaseName, setDatabaseName] = useState(String(initialExtraArgs[initialDatabaseKey] || ''))
  const [oracleServiceName, setOracleServiceName] = useState(String(initialExtraArgs.service_name || ''))
  const [oracleSid, setOracleSid] = useState(String(initialExtraArgs.SID || initialExtraArgs.sid || ''))
  const [extraArgsText, setExtraArgsText] = useState(JSON.stringify(initialExtraArgs, null, 2))
  const [error, setError] = useState<string | null>(null)
  const selectedType = useMemo(
    () => catalogTypes.find((item) => item.id === assetType),
    [assetType, catalogTypes]
  )
  const accessProtocols = selectedType?.access_protocols?.length
    ? selectedType.access_protocols
    : protocol
      ? [{ protocol, label: display.protocolLabel || protocol }]
      : []
  const groupOptions = useMemo(
    () => uniqueSessionGroups([...sessionGroups, ...(asset.tags || []), DEFAULT_SESSION_GROUP]),
    [asset.tags, sessionGroups]
  )

  const applyTypeDefault = () => {
    if (!selectedType) return
    setProtocol(selectedType.protocol || protocol)
    setPort(String(selectedType.default_port || port || ''))
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
    let extraArgs: Record<string, unknown>
    try {
      extraArgs = JSON.parse(extraArgsText || '{}') as Record<string, unknown>
      if (!extraArgs || Array.isArray(extraArgs) || typeof extraArgs !== 'object') {
        setError('高级参数必须是 JSON 对象')
        return
      }
    } catch {
      setError('高级参数 JSON 格式不正确')
      return
    }
    setOptionalField(extraArgs, initialDatabaseKey, databaseName)
    setOptionalField(extraArgs, 'service_name', oracleServiceName)
    setOptionalField(extraArgs, 'SID', oracleSid)
    delete extraArgs.sid
    const patch: Partial<Asset> = {
      remark: remark.trim() || normalizedHost,
      host: normalizedHost,
      port: normalizedPort,
      username: username.trim(),
      asset_type: assetType.trim() || asset.asset_type,
      protocol: protocol.trim() || asset.protocol || asset.asset_type,
      agent_profile: agentProfile.trim() || 'default',
      extra_args: extraArgs,
      tags: withPrimaryGroup(parseTags(tagsText), normalizedGroup),
      skills: asset.skills || [],
    }
    setError(null)
    onSave(asset, patch)
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55">
      <aside className="flex h-full w-full max-w-[760px] flex-col border-l border-ops-surface1 bg-ops-panel shadow-2xl">
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
                修改资产台账信息；凭据由平台托管，密码不会在这里明文展示。
              </p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg border border-ops-surface1 bg-ops-panel px-3 py-1.5 text-sm font-semibold text-ops-subtext hover:border-ops-accent/50 hover:text-ops-text"
            >
              关闭
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <section className="mb-4 grid gap-3 rounded-xl border border-ops-surface1 bg-ops-dark/25 p-4 md:grid-cols-3">
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
                <Field label="账号">
                  <input value={username} onChange={(event) => setUsername(event.target.value)} className={inputClass} placeholder="登录账号" />
                </Field>
                <Field label="主机 / 地址">
                  <input value={host} onChange={(event) => setHost(event.target.value)} className={inputClass} placeholder="IP、域名或 API 地址" />
                </Field>
                <Field label="端口">
                  <input value={port} onChange={(event) => setPort(event.target.value)} className={inputClass} inputMode="numeric" placeholder="1-65535" />
                </Field>
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
                  <select value={protocol} onChange={(event) => setProtocol(event.target.value)} className={inputClass}>
                    {accessProtocols.map((item) => (
                      <option key={item.protocol} value={item.protocol}>
                        {item.label || item.protocol}
                      </option>
                    ))}
                    {!accessProtocols.some((item) => item.protocol === protocol) && protocol && (
                      <option value={protocol}>{protocol}</option>
                    )}
                  </select>
                </Field>
                <div className="flex items-end">
                  <button
                    onClick={applyTypeDefault}
                    disabled={!selectedType}
                    className="h-10 rounded-lg border border-ops-accent/35 bg-ops-accent/10 px-3 text-xs font-semibold text-ops-accent hover:bg-ops-accent/18 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    应用默认
                  </button>
                </div>
              </div>
              <p className="mt-2 text-[11px] text-ops-overlay">
                默认建议：Linux 使用 SSH，Windows 使用 WinRM，数据库使用原生数据库协议，ESXi 可按实际接入选择 SSH/API。
              </p>
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

            <EditorBlock title="数据库 / Oracle 参数" hint="只填写当前资产真正需要的字段，避免 MySQL 出 SID 这类错位配置。">
              <div className="grid gap-3 md:grid-cols-3">
                <Field label="数据库名 / 实例">
                  <input value={databaseName} onChange={(event) => setDatabaseName(event.target.value)} className={inputClass} placeholder="MySQL/PostgreSQL 等" />
                </Field>
                <Field label="Oracle Service Name">
                  <input value={oracleServiceName} onChange={(event) => setOracleServiceName(event.target.value)} className={inputClass} placeholder="Oracle 可选" />
                </Field>
                <Field label="Oracle SID">
                  <input value={oracleSid} onChange={(event) => setOracleSid(event.target.value)} className={inputClass} placeholder="Oracle 可选" />
                </Field>
              </div>
            </EditorBlock>

            <EditorBlock title="高级参数 JSON" hint="保留少数特殊资产需要的扩展配置；保存前会校验 JSON 对象。">
              <textarea
                value={extraArgsText}
                onChange={(event) => setExtraArgsText(event.target.value)}
                className="min-h-40 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-xs text-ops-text outline-none focus:border-ops-accent"
                spellCheck={false}
              />
            </EditorBlock>
          </section>
        </div>

        <footer className="border-t border-ops-surface1 bg-ops-surface0/70 px-5 py-4">
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
                className="rounded-lg border border-ops-success/35 bg-ops-success/10 px-3 py-2 text-sm font-semibold text-ops-success hover:bg-ops-success/18"
              >
                验证
              </button>
              <button
                onClick={() => onConnect(asset)}
                className="rounded-lg border border-ops-accent/35 bg-ops-accent/10 px-3 py-2 text-sm font-semibold text-ops-accent hover:bg-ops-accent/18"
              >
                进入会话
              </button>
              <button
                onClick={submit}
                disabled={saving}
                className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-bold text-ops-dark hover:bg-ops-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
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
    <section className="rounded-xl border border-ops-surface1 bg-ops-panel/70 p-4">
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

function setOptionalField(target: Record<string, unknown>, field: string, value: string) {
  const normalized = value.trim()
  if (normalized) {
    target[field] = normalized
  } else {
    delete target[field]
  }
}

const inputClass = 'h-10 rounded-lg border border-ops-surface1 bg-ops-dark px-3 text-sm text-ops-text outline-none focus:border-ops-accent'
