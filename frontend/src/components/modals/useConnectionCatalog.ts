import { useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { getAssetTypes, getDatabaseDriverCapabilities, getSkillRegistry } from '@/api/client'
import type { SkillInfo } from '@/types'
import { ASSET_CATEGORIES, ASSET_SUB_TYPES, CATEGORY_LABELS } from './connectionAssetCatalog'
import type {
  AssetCategoryOption,
  AssetSubType,
  DatabaseDriverCapability,
  OracleClientConfig,
} from './connectionModalHelpers'
import {
  authModeFor,
  autoSelectSkills,
} from './connectionModalHelpers'
import type { ConnectionFormState } from './connectionModalState'

const oracleThickDefaultsFromConfig = (config: OracleClientConfig | null) =>
  config?.detected || config?.thick_mode_env_enabled
    ? { use_thick_mode: true }
    : {}

export function useConnectionCatalog({
  form,
  setForm,
  setSelectedSkills,
}: {
  form: ConnectionFormState
  setForm: Dispatch<SetStateAction<ConnectionFormState>>
  setSelectedSkills: Dispatch<SetStateAction<Set<string>>>
}) {
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [assetCategories, setAssetCategories] = useState<AssetCategoryOption[]>(ASSET_CATEGORIES)
  const [assetSubTypes, setAssetSubTypes] = useState<Record<string, AssetSubType[]>>(ASSET_SUB_TYPES)
  const [oracleClientConfig, setOracleClientConfig] = useState<OracleClientConfig | null>(null)
  const [databaseDrivers, setDatabaseDrivers] = useState<Record<string, DatabaseDriverCapability>>({})

  useEffect(() => {
    Promise.all([
      getAssetTypes().catch(() => null),
      getSkillRegistry().catch(() => null),
      getDatabaseDriverCapabilities().catch(() => null),
    ]).then(([assetResponse, skillResponse, driverResponse]) => {
      const drivers = driverResponse?.data.drivers || {}
      setDatabaseDrivers(drivers)
      const detectedOracleClient = driverResponse?.data.oracle_client || drivers.oracle?.oracle_client || null
      setOracleClientConfig(detectedOracleClient)
      let effectiveSubTypes = ASSET_SUB_TYPES
      const grouped: Record<string, AssetSubType[]> = {}
      ;(assetResponse?.data.types || []).forEach((item) => {
        if (!grouped[item.category]) grouped[item.category] = []
        grouped[item.category].push({
          id: item.id,
          label: item.label,
          asset_type: item.protocol,
          defaultPort: item.default_port,
          authMode: authModeFor(item.id, item.protocol, item.capability),
          source: item.source,
          hertzbeat_protocols: item.hertzbeat_protocols,
          params: item.params || [],
          capability: item.capability,
        })
      })
      if (Object.keys(grouped).length > 0) {
        effectiveSubTypes = grouped
        setAssetSubTypes(grouped)
        const backendCategories = assetResponse?.data.categories || []
        setAssetCategories(
          backendCategories.length > 0
            ? backendCategories.filter((category) => grouped[category.id]).map((category) => ({
                id: category.id,
                label: category.label,
                group: category.group,
                description: category.description,
              }))
            : Object.keys(grouped).map((id) => ({
                id,
                label: CATEGORY_LABELS[id] || id.toUpperCase(),
                group: '其它',
              }))
        )
      }

      const protocolFor = (category: string, subType: string) =>
        effectiveSubTypes[category]?.find((item) => item.id === subType)?.asset_type || subType

      const loadedSkills = skillResponse?.data.registry?.filter((skill) => !skill.is_market) || []
      setSkills(loadedSkills)

      const prefill = sessionStorage.getItem('prefill_asset')
      if (prefill) {
        try {
          const asset = JSON.parse(prefill)
          const extraArgs = asset.extra_args || {}
          let category = extraArgs.category || asset.category
          let subType = extraArgs.sub_type || asset.sub_type

          if (!category || !subType) {
            const assetType = asset.asset_type || 'ssh'
            const protocol = asset.protocol || extraArgs.login_protocol || extraArgs.protocol
            for (const [catalogCategory, subs] of Object.entries(effectiveSubTypes)) {
              const match = subs.find((item) => item.id === assetType || item.asset_type === assetType || (item.asset_type === protocol && item.id === assetType))
              if (match) {
                category = catalogCategory
                subType = match.id
                break
              }
            }
            if (!category || !subType) {
              category = 'os'
              subType = 'linux'
            }
          }

          setForm((prev) => ({
            ...prev,
            host: asset.host || '',
            port: asset.port || 22,
            username: asset.username || 'root',
            password: asset.password || '',
            remark: asset.remark || '',
            asset_type: asset.asset_type || subType || 'linux',
            protocol: asset.protocol || protocolFor(category, subType),
            agent_profile: asset.agent_profile || 'default',
            group_name: (asset.tags && asset.tags[0]) || '未分组',
            allow_modifications: false,
            target_scope: 'asset',
            extra_args: {
              ...extraArgs,
              ...(subType === 'oracle' && extraArgs.use_thick_mode ? oracleThickDefaultsFromConfig(detectedOracleClient) : {}),
            },
            category,
            sub_type: subType,
          }))

          if (asset.skills && asset.skills.length > 0) {
            setSelectedSkills(new Set(asset.skills))
          } else {
            setSelectedSkills(autoSelectSkills(subType, loadedSkills))
          }
        } catch {
          // Ignore stale prefill data and keep the default form.
        }
        sessionStorage.removeItem('prefill_asset')
      } else {
        sessionStorage.removeItem('asset_editing_id')
        setSelectedSkills(autoSelectSkills(form.sub_type, loadedSkills))
      }
    })
    // Keep the startup catalog load behavior identical to the previous mount-only effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    assetCategories,
    assetSubTypes,
    databaseDrivers,
    oracleClientConfig,
    oracleThickDefaults: (config: OracleClientConfig | null = oracleClientConfig) => oracleThickDefaultsFromConfig(config),
    skills,
  }
}
