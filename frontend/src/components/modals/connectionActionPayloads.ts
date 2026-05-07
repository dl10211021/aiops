import type { Asset } from '@/types'
import type { ConnectionFormState, resolveConnectionTarget } from './connectionModalState'

type ConnectionTarget = ReturnType<typeof resolveConnectionTarget>

type ConnectionActionPayloadArgs = {
  form: ConnectionFormState
  selectedSkills: string[]
  target: ConnectionTarget
}

export function buildTestConnectionPayload({ form, target }: ConnectionActionPayloadArgs) {
  return {
    host: target.host,
    port: form.port,
    username: target.username,
    password: form.password,
    asset_type: target.assetType,
    protocol: target.protocol,
    extra_args: form.extra_args,
    active_skills: [],
    target_scope: form.target_scope,
    scope_value: target.scopeValue,
  }
}

export function buildConnectSessionPayload({ form, selectedSkills, target }: ConnectionActionPayloadArgs) {
  return {
    ...form,
    host: target.host,
    username: target.username,
    asset_type: target.assetType,
    protocol: target.protocol,
    active_skills: selectedSkills,
    tags: [form.group_name],
    target_scope: form.target_scope,
    scope_value: target.scopeValue,
  }
}

export function buildSavedAssetPayload({ form, selectedSkills, target }: ConnectionActionPayloadArgs): Partial<Asset> {
  return {
    host: target.host,
    username: target.username,
    password: form.password,
    port: form.port,
    asset_type: target.assetType,
    protocol: target.protocol,
    remark: form.remark,
    agent_profile: form.agent_profile,
    extra_args: form.extra_args,
    skills: selectedSkills,
    tags: [form.group_name],
  }
}
