import { useCallback, useEffect, useState } from 'react'
import {
  getDashboardAlertTrend,
  getDashboardInspectionRunTrend,
  getDashboardOverview,
  getDashboardRiskRanking,
  getDashboardToolsets,
} from '@/api/client'
import type { AlertTrendPoint, DashboardOverview, InspectionTrendPoint, RiskRankingItem, SessionToolCatalog } from '@/types'

export function useDashboardData() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [trend, setTrend] = useState<AlertTrendPoint[]>([])
  const [inspectionTrend, setInspectionTrend] = useState<InspectionTrendPoint[]>([])
  const [ranking, setRanking] = useState<RiskRankingItem[]>([])
  const [toolsets, setToolsets] = useState<SessionToolCatalog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [overviewRes, trendRes, inspectionTrendRes, rankingRes, toolsetRes] = await Promise.all([
        getDashboardOverview(),
        getDashboardAlertTrend(),
        getDashboardInspectionRunTrend(),
        getDashboardRiskRanking(),
        getDashboardToolsets(),
      ])
      setOverview(overviewRes.data)
      setTrend(trendRes.data.points || [])
      setInspectionTrend(inspectionTrendRes.data.points || [])
      setRanking(rankingRes.data.ranking || [])
      setToolsets(toolsetRes.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载总览失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return {
    error,
    inspectionTrend,
    load,
    loading,
    overview,
    ranking,
    toolsets,
    trend,
  }
}
