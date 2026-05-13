import { useState } from 'react'
import { useStore } from '@/store'
import {
  DEFAULT_CONNECTION_FORM,
  type ConnectionFormState,
} from './connectionModalState'
import { buildConnectionModalModel } from './connectionModalModel'
import {
  formForCategorySelection,
  formForProtocolSelection,
  formForSubTypeSelection,
  patchConnectionExtraArgs,
  setConnectionExtraArg,
  skillsForSelectedSubType,
  toggleConnectionSkillSelection,
} from './connectionFormSelection'
import { useConnectionActions } from './useConnectionActions'
import { useConnectionCatalog } from './useConnectionCatalog'

export function useConnectionModalController() {
  const closeModal = useStore((state) => state.closeModal)
  const [form, setForm] = useState<ConnectionFormState>(DEFAULT_CONNECTION_FORM)
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set())
  const [assetTypeSearch, setAssetTypeSearch] = useState('')
  const [assetCatalogMode, setAssetCatalogMode] = useState<'common' | 'all'>('common')
  const [skillSearch, setSkillSearch] = useState('')

  const {
    assetCategories,
    assetSubTypes,
    catalogStatus,
    databaseDrivers,
    oracleClientConfig,
    oracleThickDefaults,
    skills,
  } = useConnectionCatalog({
    form,
    setForm,
    setSelectedSkills,
  })

  const model = buildConnectionModalModel({
    assetCatalogMode,
    assetCategories,
    assetSubTypes,
    assetTypeSearch,
    databaseDrivers,
    form,
  })

  const setExtraArg = (field: string, value: unknown) => {
    setForm(setConnectionExtraArg(form, field, value))
  }

  const setExtraArgs = (patch: Record<string, unknown>) => {
    setForm(patchConnectionExtraArgs(form, patch))
  }

  const handleCategoryChange = (newCategory: string) => {
    const nextForm = formForCategorySelection({
      assetSubTypes,
      form,
      newCategory,
      oracleThickDefaults,
    })
    if (!nextForm) return
    setAssetTypeSearch('')
    setForm(nextForm)
    setSelectedSkills(skillsForSelectedSubType(nextForm.sub_type, skills))
  }

  const handleSubTypeChange = (newSubTypeId: string) => {
    const nextForm = formForSubTypeSelection({
      assetSubTypes,
      form,
      newSubTypeId,
      oracleThickDefaults,
    })
    if (!nextForm) return
    setAssetTypeSearch('')
    setForm(nextForm)
    setSelectedSkills(skillsForSelectedSubType(newSubTypeId, skills))
  }

  const handleProtocolChange = (protocol: string) => {
    setForm(formForProtocolSelection({
      form,
      protocol,
      selectedSubInfo: model.selectedSubInfo,
    }))
  }

  const toggleSkill = (id: string) => {
    setSelectedSkills(toggleConnectionSkillSelection(selectedSkills, id))
  }

  const isGlobal = form.target_scope === 'global'
  const canSubmitAsset = isGlobal || !!model.resolveAssetHost(false)
  const connectionActions = useConnectionActions({
    currentProtocol: model.currentProtocol,
    form,
    missingHostMessage: model.missingHostMessage,
    resolveAssetHost: model.resolveAssetHost,
    selectedSkills,
  })

  return {
    ...model,
    ...connectionActions,
    assetCategories,
    assetCatalogMode,
    assetTypeSearch,
    catalogStatus,
    canSubmitAsset,
    closeModal,
    form,
    oracleClientConfig,
    oracleThickDefaults,
    selectedSkills,
    setAssetCatalogMode,
    setAssetTypeSearch,
    setExtraArg,
    setExtraArgs,
    setForm,
    setSkillSearch,
    skillSearch,
    skills,
    toggleSkill,
    handleCategoryChange,
    handleProtocolChange,
    handleSubTypeChange,
  }
}
