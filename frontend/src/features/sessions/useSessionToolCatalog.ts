import { useEffect, useState } from 'react'
import { getSessionTools } from '@/api/client'
import { isAbortError } from '@/api/http'
import { useStore } from '@/store'
import type { SessionToolCatalog } from '@/types'

const SESSION_TOOL_CACHE_TTL_MS = 5 * 60 * 1000
const SESSION_TOOL_FETCH_DELAY_MS = 450
const sessionToolCatalogCache = new Map<string, { catalog: SessionToolCatalog; cachedAt: number }>()

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
    const cacheKey = sessionToolCatalogCacheKey(currentSessionId, assetType, protocol)
    const cached = sessionToolCatalogCache.get(cacheKey)
    if (cached && Date.now() - cached.cachedAt < SESSION_TOOL_CACHE_TTL_MS) {
      setToolCatalog(cached.catalog)
      return
    }
    let cancelled = false
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') return
      getSessionTools(currentSessionId, { signal: controller.signal })
        .then((response) => {
          sessionToolCatalogCache.set(cacheKey, { catalog: response.data, cachedAt: Date.now() })
          if (!cancelled) setToolCatalog(response.data)
        })
        .catch((error) => {
          if (isAbortError(error) || controller.signal.aborted) return
          if (!cancelled) setToolCatalog(null)
        })
    }, SESSION_TOOL_FETCH_DELAY_MS)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [currentSessionId, assetType, protocol])

  return toolCatalog
}

function sessionToolCatalogCacheKey(sessionId: string, assetType?: string, protocol?: string) {
  return [sessionId, assetType || '', protocol || ''].join('|')
}
