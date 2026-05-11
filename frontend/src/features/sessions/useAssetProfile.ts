import { useCallback, useEffect, useState } from 'react'
import { generateSessionProfile, getSessionProfile } from '@/api/client'
import { isAbortError } from '@/api/http'
import { useStore } from '@/store'
import type { AssetProfile } from '@/types'

const SESSION_PROFILE_CACHE_TTL_MS = 5 * 60 * 1000
const SESSION_PROFILE_FETCH_DELAY_MS = 450
const sessionProfileCache = new Map<string, { profile: AssetProfile | null; cachedAt: number }>()

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

    const cached = sessionProfileCache.get(currentSessionId)
    if (cached && Date.now() - cached.cachedAt < SESSION_PROFILE_CACHE_TTL_MS) {
      setProfile(cached.profile)
      return
    }

    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') return
      getSessionProfile(currentSessionId, { signal: controller.signal })
        .then((res) => {
          sessionProfileCache.set(currentSessionId, { profile: res.data.profile, cachedAt: Date.now() })
          if (!cancelled) setProfile(res.data.profile)
        })
        .catch((error) => {
          if (isAbortError(error) || controller.signal.aborted) return
          if (!cancelled) setProfile(null)
        })
    }, SESSION_PROFILE_FETCH_DELAY_MS)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [currentSessionId])

  const toggle = useCallback(() => {
    setOpen((value) => !value)
  }, [])

  const generate = useCallback(async () => {
    const sessionId = currentSessionId
    if (!sessionId) return
    setBusySessionId(sessionId)
    try {
      const res = await generateSessionProfile(sessionId, modelName || undefined, true)
      sessionProfileCache.set(sessionId, { profile: res.data.profile, cachedAt: Date.now() })
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
  }, [addToast, currentSessionId, modelName])

  return {
    busy,
    generate,
    open,
    profile,
    toggle,
  }
}
