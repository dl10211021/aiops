import { useState } from 'react'
import { batchImportAssets, updateAsset, connectSession, getSavedAssets, inspectConnection, testConnection } from '@/api/client'
import { useStore } from '@/store'
import {
  buildConnectSessionPayload,
  buildInspectConnectionPayload,
  buildSavedAssetPayload,
  buildTestConnectionPayload,
} from './connectionActionPayloads'
import { connectionFeedbackFromError, type ConnectionFeedback } from './connectionModalHelpers'
import { resolveConnectionTarget, type ConnectionFormState } from './connectionModalState'
import type { ConnectionInspectionResult } from './ConnectionFeedbackPanels'

interface UseConnectionActionsArgs {
  currentProtocol: string
  form: ConnectionFormState
  missingHostMessage: string
  resolveAssetHost: (isGlobal?: boolean) => string
  selectedSkills: Set<string>
}

export function useConnectionActions({
  currentProtocol,
  form,
  missingHostMessage,
  resolveAssetHost,
  selectedSkills,
}: UseConnectionActionsArgs) {
  const addSession = useStore((state) => state.addSession)
  const addToast = useStore((state) => state.addToast)
  const closeModal = useStore((state) => state.closeModal)
  const setAssets = useStore((state) => state.setAssets)
  const setView = useStore((state) => state.setView)
  const [testing, setTesting] = useState(false)
  const [inspecting, setInspecting] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionFeedback | null>(null)
  const [inspectionResult, setInspectionResult] = useState<ConnectionInspectionResult | null>(null)

  const resolveRequestTarget = () => {
    const isGlobal = form.target_scope === 'global'
    const host = resolveAssetHost(isGlobal)
    return {
      host,
      target: resolveConnectionTarget(form, host, currentProtocol),
    }
  }
  const payloadArgsFor = (target: ReturnType<typeof resolveConnectionTarget>) => ({
    form,
    selectedSkills: Array.from(selectedSkills),
    target,
  })

  const refreshSavedAssets = async () => {
    try {
      const assetsRes = await getSavedAssets()
      setAssets(assetsRes.data.assets || [])
    } catch {
      addToast('资产已提交，但资产列表刷新失败，请稍后手动刷新页面。', 'info')
    }
  }

  const handleTest = async () => {
    const { host, target } = resolveRequestTarget()

    if (!host) {
      setTestResult({ ok: false, title: '缺少连接地址', msg: missingHostMessage })
      return
    }
    setTesting(true)
    setTestResult(null)
    setInspectionResult(null)
    try {
      const res = await testConnection(buildTestConnectionPayload(payloadArgsFor(target)))
      setTestResult({
        ok: res.status === 'success',
        title: res.status === 'success' ? '连接正常' : '连接失败',
        msg: res.message,
      })
    } catch (error: unknown) {
      setTestResult(connectionFeedbackFromError(error, '测试失败'))
    } finally {
      setTesting(false)
    }
  }

  const handleInspect = async () => {
    const { host, target } = resolveRequestTarget()

    if (!host) {
      addToast(missingHostMessage, 'error')
      return
    }
    setInspecting(true)
    setTestResult(null)
    setInspectionResult(null)
    try {
      const res = await inspectConnection(buildInspectConnectionPayload(payloadArgsFor(target)))
      const inspection = res.data.inspection
      setInspectionResult({
        ok: res.status === 'success' && inspection.status !== 'error',
        summary: inspection.summary || inspection.message || res.message,
        checks: inspection.checks || [],
      })
    } catch (error: unknown) {
      const feedback = connectionFeedbackFromError(error, '巡检失败')
      setInspectionResult({
        ok: false,
        summary: `${feedback.title}：${feedback.msg}`,
        checks: [],
      })
    } finally {
      setInspecting(false)
    }
  }

  const handleConnect = async () => {
    const { host, target } = resolveRequestTarget()

    if (!host) {
      addToast(missingHostMessage, 'error')
      return
    }
    setConnecting(true)
    setTestResult(null)
    try {
      const selectedSkillIds = Array.from(selectedSkills)
      const res = await connectSession(buildConnectSessionPayload({ form, selectedSkills: selectedSkillIds, target }))
      const sid = res.data.session_id
      addSession({
        id: sid,
        host: target.host,
        remark: form.remark,
        isReadWriteMode: form.allow_modifications,
        skills: selectedSkillIds,
        agentProfile: form.agent_profile,
        user: target.isGlobal ? 'opscore_agent' : target.username,
        asset_type: target.assetType,
        protocol: target.protocol,
        extra_args: form.extra_args,
        heartbeatEnabled: false,
        tags: [form.group_name],
        messages: [],
        isStreaming: false,
      })
      await refreshSavedAssets()
      addToast(`已连接到 ${form.remark || target.host}`, 'success')
      closeModal()
      setView('chat')
    } catch (error: unknown) {
      const feedback = connectionFeedbackFromError(error)
      setTestResult(feedback)
      addToast(`${feedback.title}：${feedback.msg}`, 'error')
    } finally {
      setConnecting(false)
    }
  }

  const handleSaveOnly = async () => {
    const { host, target } = resolveRequestTarget()

    if (!host) {
      addToast(missingHostMessage, 'error')
      return
    }
    setConnecting(true)
    try {
      const savedAssetPayload = buildSavedAssetPayload(payloadArgsFor(target))
      const editingAssetId = Number(sessionStorage.getItem('asset_editing_id') || '')
      const isEditingAsset = Number.isFinite(editingAssetId) && editingAssetId > 0

      if (isEditingAsset) {
        if (!String(savedAssetPayload.password || '').trim()) {
          savedAssetPayload['password'] = '********'
        }
        await updateAsset(editingAssetId, savedAssetPayload)
        sessionStorage.removeItem('asset_editing_id')
      } else {
        await batchImportAssets([savedAssetPayload])
      }
      await refreshSavedAssets()
      addToast(`${isEditingAsset ? '已更新资产' : '已保存资产'} ${form.remark || target.host}`, 'success')
      closeModal()
      if (useStore.getState().currentView !== 'assets') {
        setView('assets')
      }
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '保存失败', 'error')
    } finally {
      setConnecting(false)
    }
  }

  return {
    connecting,
    handleConnect,
    handleInspect,
    handleSaveOnly,
    handleTest,
    inspecting,
    inspectionResult,
    testing,
    testResult,
  }
}
