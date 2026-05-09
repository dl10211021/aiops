import type {
  ObservabilityOverview,
  ObservabilityDiscoveryCandidate,
  ObservabilityInvestigation,
  ObservabilityComponent,
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

export async function bindObservabilityAsset(systemId: string, asset: Record<string, unknown>) {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/assets`,
    {
      method: 'POST',
      body: JSON.stringify({ asset }),
    },
  )
}

export async function bindObservabilitySession(systemId: string, session: Record<string, unknown>, role = 'investigation_channel') {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/sessions`,
    {
      method: 'POST',
      body: JSON.stringify({ session, role }),
    },
  )
}

export async function unbindObservabilityComponent(systemId: string, componentId: string) {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/components/${encodeURIComponent(componentId)}`,
    { method: 'DELETE' },
  )
}

export async function updateObservabilityComponent(systemId: string, componentId: string, payload: Partial<ObservabilityComponent>) {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/components/${encodeURIComponent(componentId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  )
}

export async function getObservableSources() {
  return request<{ sources: ObservabilitySource[] }>('/observability/sources')
}

export async function getObservabilityDiscoveryCandidates(systemId?: string) {
  const query = systemId ? `?system_id=${encodeURIComponent(systemId)}` : ''
  return request<{ candidates: ObservabilityDiscoveryCandidate[] }>(`/observability/discovery-candidates${query}`)
}

export async function getObservabilityInvestigations(systemId?: string) {
  const query = systemId ? `?system_id=${encodeURIComponent(systemId)}` : ''
  return request<{ investigations: ObservabilityInvestigation[] }>(`/observability/investigations${query}`)
}

export async function createObservabilityInvestigation(payload: {
  system_id: string
  title: string
  symptom: string
  time_window?: string
  severity?: 'unknown' | 'info' | 'warning' | 'critical' | string
}) {
  return request<{ investigation: ObservabilityInvestigation }>('/observability/investigations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function appendObservabilityEvidence(investigationId: string, payload: {
  title: string
  summary?: string
  evidence_type?: string
  confidence?: string
}) {
  return request<{ investigation: ObservabilityInvestigation }>(
    `/observability/investigations/${encodeURIComponent(investigationId)}/evidence`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export async function getObservabilityProfilePacks() {
  return request<{ profile_packs: ObservabilityProfilePack[] }>('/observability/profile-packs')
}
