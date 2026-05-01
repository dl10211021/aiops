import { useEffect, useState } from 'react'
import { getSessionTools } from '@/api/client'
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
    getSessionTools(currentSessionId)
      .then((response) => {
        if (!cancelled) setToolCatalog(response.data)
      })
      .catch(() => {
        if (!cancelled) setToolCatalog(null)
      })
    return () => {
      cancelled = true
    }
  }, [currentSessionId, assetType, protocol])

  return toolCatalog
}
