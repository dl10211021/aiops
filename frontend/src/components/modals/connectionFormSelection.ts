import type { SkillInfo } from '@/types'
import { buildConnectionExtraArgs } from './connectionModalModel'
import type { AssetSubType } from './connectionModalTypes'
import type { ConnectionFormState } from './connectionModalState'
import { autoSelectSkills, usernameForSelection } from './connectionModalHelpers'

export function formForCategorySelection({
  assetSubTypes,
  form,
  newCategory,
  oracleThickDefaults,
}: {
  assetSubTypes: Record<string, AssetSubType[]>
  form: ConnectionFormState
  newCategory: string
  oracleThickDefaults: () => Record<string, unknown>
}) {
  const firstSubType = assetSubTypes[newCategory]?.[0]
  if (!firstSubType) return null
  return {
    ...form,
    category: newCategory,
    sub_type: firstSubType.id,
    asset_type: firstSubType.id,
    protocol: firstSubType.asset_type,
    port: firstSubType.defaultPort,
    username: usernameForSelection(form.username, newCategory, firstSubType),
    extra_args: buildConnectionExtraArgs(newCategory, firstSubType, oracleThickDefaults),
  }
}

export function formForSubTypeSelection({
  assetSubTypes,
  form,
  newSubTypeId,
  oracleThickDefaults,
}: {
  assetSubTypes: Record<string, AssetSubType[]>
  form: ConnectionFormState
  newSubTypeId: string
  oracleThickDefaults: () => Record<string, unknown>
}) {
  const subInfo = assetSubTypes[form.category].find((item) => item.id === newSubTypeId)
  if (!subInfo) return null
  return {
    ...form,
    sub_type: newSubTypeId,
    asset_type: newSubTypeId,
    protocol: subInfo.asset_type,
    port: subInfo.defaultPort,
    username: usernameForSelection(form.username, form.category, subInfo),
    extra_args: buildConnectionExtraArgs(form.category, subInfo, oracleThickDefaults),
  }
}

export function formForProtocolSelection({
  form,
  protocol,
  selectedSubInfo,
}: {
  form: ConnectionFormState
  protocol: string
  selectedSubInfo?: AssetSubType
}) {
  const selectedAccess = (selectedSubInfo?.access_protocols || []).find((item) => item.protocol === protocol)
  return {
    ...form,
    protocol,
    port: selectedAccess?.default_port || (selectedSubInfo && protocol === selectedSubInfo.asset_type ? selectedSubInfo.defaultPort : form.port),
    extra_args: {
      ...form.extra_args,
      login_protocol: protocol,
      protocol,
    },
  }
}

export function setConnectionExtraArg(
  form: ConnectionFormState,
  field: string,
  value: unknown,
) {
  return {
    ...form,
    extra_args: { ...form.extra_args, [field]: value },
  }
}

export function patchConnectionExtraArgs(
  form: ConnectionFormState,
  patch: Record<string, unknown>,
) {
  return {
    ...form,
    extra_args: { ...form.extra_args, ...patch },
  }
}

export function toggleConnectionSkillSelection(selectedSkills: Set<string>, id: string) {
  const next = new Set(selectedSkills)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  return next
}

export function skillsForSelectedSubType(subTypeId: string, skills: SkillInfo[]) {
  return autoSelectSkills(subTypeId, skills)
}
