import { useEffect, useState } from 'react'
import { getSessionTools } from '@/api/client'
import { useStore } from '@/store'
import type { SessionToolCatalog } from '@/types'

export function useSessionToolCatalog(
  currentSessionId: string | null,
  assetType?: string,
  protocol?: string,
) {
  const [toolCatalog, setToolCatalog] = useState<SessionToolCatalog | null>(null)

  useEffect(() => {
    if (!currentSessionId) {
      setToolCatalog(null)
      return
    }
    let cancelled = false
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') return
      getSessionTools(currentSessionId)
        .then((response) => {
          if (!cancelled) setToolCatalog(response.data)
        })
        .catch(() => {
          if (!cancelled) setToolCatalog(null)
        })
    }, 800)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [currentSessionId, assetType, protocol])

  return toolCatalog
}
