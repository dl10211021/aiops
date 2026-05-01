import type { AlertTrendPoint, DashboardOverview, RiskRankingItem, SessionToolCatalog } from '@/types'
import { request } from './http'

export async function getDashboardOverview() {
  return request<DashboardOverview>('/dashboard/overview')
}

export async function getDashboardAlertTrend() {
  return request<{ points: AlertTrendPoint[] }>('/dashboard/alerts/trend')
}

export async function getDashboardRiskRanking() {
  return request<{ ranking: RiskRankingItem[] }>('/dashboard/risk-ranking')
}

export async function getDashboardToolsets() {
  return request<SessionToolCatalog>('/dashboard/toolsets')
}
