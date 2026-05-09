import type {
  ObservabilityOverview,
  ObservabilityProfile,
  ObservabilityProfilePack,
  ObservabilitySource,
  ObservabilitySystemSummary,
} from '@/types'
import { request } from './http'

export async function getObservabilityOverview() {
  return request<{ overview: ObservabilityOverview }>('/observability/overview')
}

export async function getObservabilitySystems() {
  return request<{ systems: ObservabilitySystemSummary[] }>('/observability/systems')
}

export async function getObservabilityProfile(systemId: string) {
  return request<{ profile: ObservabilityProfile }>(`/observability/systems/${encodeURIComponent(systemId)}`)
}

export async function getObservableSources() {
  return request<{ sources: ObservabilitySource[] }>('/observability/sources')
}

export async function getObservabilityProfilePacks() {
  return request<{ profile_packs: ObservabilityProfilePack[] }>('/observability/profile-packs')
}
