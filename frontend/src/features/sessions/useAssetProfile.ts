import { useEffect, useState } from 'react'
import { generateSessionProfile, getSessionProfile } from '@/api/client'
import { useStore } from '@/store'
import type { AssetProfile } from '@/types'

export function useAssetProfile(currentSessionId: string | null, modelName: string) {
  const addToast = useStore((state) => state.addToast)
  const [profile, setProfile] = useState<AssetProfile | null>(null)
  const [busySessionId, setBusySessionId] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const busy = Boolean(currentSessionId && busySessionId === currentSessionId)

  useEffect(() => {
    let cancelled = false
    setProfile(null)
    setOpen(false)
    if (!currentSessionId) return
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') return
      getSessionProfile(currentSessionId)
        .then((res) => {
          if (!cancelled) setProfile(res.data.profile)
        })
        .catch(() => {
          if (!cancelled) setProfile(null)
        })
    }, 800)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [currentSessionId])

  const toggle = () => {
    setOpen((value) => !value)
  }

  const generate = async () => {
    const sessionId = currentSessionId
    if (!sessionId) return
    setBusySessionId(sessionId)
    try {
      const res = await generateSessionProfile(sessionId, modelName || undefined, true)
      if (useStore.getState().currentSessionId === sessionId) {
        setProfile(res.data.profile)
        setOpen(true)
      }
      addToast('资产画像已生成', 'success')
    } catch (err) {
      const message = err instanceof Error ? err.message : '资产画像生成失败'
      addToast(message, 'error')
    } finally {
      setBusySessionId((current) => current === sessionId ? null : current)
    }
  }

  return {
    busy,
    generate,
    open,
    profile,
    toggle,
  }
}
