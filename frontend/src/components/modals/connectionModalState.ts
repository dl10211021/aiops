export interface ConnectionFormState {
  host: string
  port: number
  username: string
  password: string
  remark: string
  asset_type: string
  protocol: string
  agent_profile: string
  group_name: string
  allow_modifications: boolean
  target_scope: string
  category: string
  sub_type: string
  extra_args: Record<string, unknown>
}

export const DEFAULT_CONNECTION_FORM: ConnectionFormState = {
  host: '',
  port: 22,
  username: 'root',
  password: '',
  remark: '',
  asset_type: 'linux',
  protocol: 'ssh',
  agent_profile: 'default',
  group_name: '未分组',
  allow_modifications: false,
  target_scope: 'asset',
  category: 'os',
  sub_type: 'linux',
  extra_args: {},
}

export function resolveConnectionTarget(
  form: ConnectionFormState,
  host: string,
  protocol: string,
) {
  const isGlobal = form.target_scope === 'global'
  return {
    assetType: isGlobal ? 'virtual' : form.sub_type,
    host,
    isGlobal,
    protocol: isGlobal ? 'virtual' : protocol,
    scopeValue: form.target_scope === 'group' ? form.group_name : host,
    username: isGlobal ? 'admin' : form.username,
  }
}
